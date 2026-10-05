"""Shop database access and the tools the agent is allowed to call.

Everything that reads campus_customs.db lives here, so the REST routes in main.py and
the agent's tools return the same data through the same code path.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from models import ProductCard, ProductDetail, ProductFacts, SizeStock, StockAnswer, UserPublic

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
AUDIT_PATH = PROJECT_ROOT / "output" / "audit_trail.json"

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

# How many products a single search may hand back. Caps the tokens spent on one turn
# and keeps the card grid readable.
MAX_SEARCH_RESULTS = 6

# The catalogue stores 22 spellings of garment_type for about six real categories.
# First matching fragment wins, so order matters.
CATEGORY_RULES: list[tuple[str, str]] = [
    ("quarter-zip", "Quarter-Zips"),
    ("hood", "Hoodies"),
    ("jacket", "Jackets"),
    ("t-shirt", "T-Shirts"),
    ("performance shirt", "Performance"),
    ("crewneck", "Crewnecks"),
    ("mockneck", "Crewnecks"),
    ("sweatshirt", "Crewnecks"),
]

CATEGORY_ORDER = [
    "Hoodies",
    "Crewnecks",
    "T-Shirts",
    "Quarter-Zips",
    "Jackets",
    "Performance",
]


def categorize(garment_type: str) -> str:
    lowered = garment_type.lower()
    for fragment, category in CATEGORY_RULES:
        if fragment in lowered:
            return category
    return "Other"


def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise RuntimeError(
            f"Database not found at {DB_PATH}. Unzip the course data pack so that "
            f"data/campus_customs.db sits next to the backend/ folder."
        )
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def _blurb(description: str) -> str:
    head = description.split(". ")[0].strip()
    return head if head.endswith(".") else head + "."


def to_card(row: sqlite3.Row) -> ProductCard:
    return ProductCard(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        category=categorize(row["garment_type"]),
        price=row["price"],
        image_url=f"/static/{row['image_file_path']}",
        colors=json.loads(row["colors"]),
        blurb=_blurb(row["description"]),
    )


def sizes_for(con: sqlite3.Connection, product_id: str) -> list[SizeStock]:
    rows = con.execute(
        "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
    ).fetchall()
    by_size = {r["size"]: r["quantity"] for r in rows}
    # Explicit order: ORDER BY size would give L, M, S, XL, XS, XXL.
    return [SizeStock(size=s, quantity=by_size.get(s, 0)) for s in SIZE_ORDER]


def attach_stock(cards: list[ProductCard]) -> list[ProductCard]:
    """Fill in which sizes are still available, for every card, in one query.

    Done in bulk rather than per card so showing availability on a 102-item grid costs
    one trip to the database instead of 102.
    """
    if not cards:
        return cards
    with connect() as con:
        rows = con.execute(
            "SELECT product_id, size FROM inventory WHERE quantity > 0"
        ).fetchall()
    available: dict[str, set[str]] = {}
    for row in rows:
        available.setdefault(row["product_id"], set()).add(row["size"])
    for card in cards:
        got = available.get(card.product_id, set())
        card.in_stock_sizes = [s for s in SIZE_ORDER if s in got]
    return cards


def cards_for_ids(ids: list[str]) -> list[ProductCard]:
    """Rebuild cards straight from the database for the given ids, in order.

    The agent never writes card data; it only ever causes ids to be recorded. This is
    what makes it impossible for a hallucinated price to reach the shopper's screen.
    """
    if not ids:
        return []
    with connect() as con:
        placeholders = ",".join("?" * len(ids))
        rows = con.execute(
            f"SELECT * FROM catalogue WHERE product_id IN ({placeholders})", ids
        ).fetchall()
    by_id = {r["product_id"]: to_card(r) for r in rows}
    return attach_stock([by_id[i] for i in ids if i in by_id])


def product_detail(product_id: str) -> ProductDetail | None:
    with connect() as con:
        row = con.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            return None
        sizes = sizes_for(con, product_id)
    card = to_card(row)
    return ProductDetail(
        **card.model_dump(),
        description=row["description"],
        search_tags=json.loads(row["search_tags"]),
        sizes=sizes,
    )


def resolve_product(reference: str) -> sqlite3.Row | None:
    """Find a product by id, or failing that by a loose name match.

    The model sometimes passes a name ("Basic Hoodie Big Yale") where an id was
    expected, so a plain id lookup alone would make the tool look broken.
    """
    needle = reference.strip().lower()
    with connect() as con:
        row = con.execute(
            "SELECT * FROM catalogue WHERE lower(product_id) = ?", (needle,)
        ).fetchone()
        if row:
            return row
        row = con.execute(
            "SELECT * FROM catalogue WHERE lower(name) = ?", (needle,)
        ).fetchone()
        if row:
            return row
        return con.execute(
            "SELECT * FROM catalogue WHERE lower(name) LIKE ? OR lower(product_id) LIKE ?",
            (f"%{needle}%", f"%{needle}%"),
        ).fetchone()


# ------------------------------------------------------------------ chat history

# How many stored messages are replayed to the model on each turn. Enough for
# follow-ups like "what about in gray?" to resolve, while keeping the tokens spent on
# any single reply bounded.
HISTORY_TURNS = 10


def ensure_schema() -> None:
    """Create the chat history table if it is not there yet.

    A dedicated table rather than the seeded `chat_messages` because this one also
    records the page the customer was on, which is part of what Problem 8 asks the
    agent to use and which `chat_messages` has nowhere to put.
    """
    with connect() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL REFERENCES users(id),
                role            TEXT    NOT NULL CHECK (role IN ('user', 'assistant')),
                content         TEXT    NOT NULL,
                products_json   TEXT,
                page_path       TEXT,
                product_context TEXT,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_history_user "
            "ON chat_history (user_id, id)"
        )
        con.commit()


def save_turn(
    user_id: int,
    role: str,
    content: str,
    products: list[ProductCard] | None = None,
    page_path: str | None = None,
    product_context: str | None = None,
) -> None:
    with connect() as con:
        con.execute(
            """INSERT INTO chat_history
               (user_id, role, content, products_json, page_path, product_context)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                role,
                content,
                json.dumps([p.model_dump() for p in products]) if products else None,
                page_path,
                product_context,
            ),
        )
        con.commit()


def load_history(user_id: int, limit: int = HISTORY_TURNS) -> list[dict[str, Any]]:
    """Most recent `limit` messages for a customer, oldest first."""
    with connect() as con:
        rows = con.execute(
            """SELECT role, content, products_json, created_at
               FROM chat_history WHERE user_id = ?
               ORDER BY id DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    out: list[dict[str, Any]] = []
    for r in reversed(rows):
        # Only the product ids are trusted from storage; the card itself is rebuilt
        # from the catalogue. A snapshot saved last week would show last week's
        # stock, and an older row may predate fields the card has since gained.
        products: list[ProductCard] = []
        if r["products_json"]:
            stored = json.loads(r["products_json"])
            ids = [p["product_id"] for p in stored if isinstance(p, dict) and "product_id" in p]
            products = cards_for_ids(ids)
        out.append(
            {
                "role": r["role"],
                "content": r["content"],
                "products": [p.model_dump() for p in products],
                "created_at": r["created_at"],
            }
        )
    return out


# ------------------------------------------------------------------ audit trail


def audit(tool: str, args: dict[str, Any], result: str, stop_reason: str = "ok") -> None:
    """Append one line to output/audit_trail.json. Never truncates the file."""
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tool": tool,
        "args": {k: str(v)[:120] for k, v in args.items()},
        "result": result[:200],
        "stop_reason": stop_reason,
    }
    try:
        existing = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        if not isinstance(existing, list):
            existing = []
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []
    existing.append(entry)
    AUDIT_PATH.write_text(json.dumps(existing, indent=2), encoding="utf-8")


# ------------------------------------------------------------------ agent deps


@dataclass
class ShopDeps:
    """Everything the agent knows about who it is talking to and where they are."""

    user: UserPublic | None = None
    current_product_id: str | None = None
    page_path: str | None = None

    # Product ids the tools returned this turn, in the order they were first seen.
    # main.py turns these into cards after the run.
    matched: list[str] = field(default_factory=list)

    def remember(self, product_ids: list[str]) -> None:
        for pid in product_ids:
            if pid not in self.matched:
                self.matched.append(pid)


# ------------------------------------------------------------------ tool bodies
#
# These are plain functions so they can be unit-tested without a model. agent.py
# registers thin wrappers around them that also record matches and write the audit log.


_search_index: list[tuple[ProductCard, list[tuple[str, int]]]] | None = None


def search_index() -> list[tuple[ProductCard, list[tuple[str, int]]]]:
    """Build the catalogue once and keep it in memory.

    The catalogue is 102 static rows, but every chat search was re-reading all of them
    and re-parsing two JSON columns per row. Caching makes each search a list scan
    instead of a query plus 204 JSON parses, which shows up directly in how fast the
    assistant answers.
    """
    global _search_index
    if _search_index is not None:
        return _search_index

    with connect() as con:
        rows = con.execute("SELECT * FROM catalogue ORDER BY name").fetchall()

    index = []
    for row in rows:
        card = to_card(row)
        # Weighted fields: a name match matters more than a word buried in prose.
        haystacks = [
            (row["name"].lower(), 3),
            (row["search_tags"].lower(), 2),
            (row["colors"].lower(), 2),
            (card.category.lower(), 2),
            (row["description"].lower(), 1),
        ]
        index.append((card, haystacks))

    _search_index = index
    return index


def search_catalogue(
    query: str | None = None,
    category: str | None = None,
    max_price: float | None = None,
) -> tuple[int, list[ProductCard]]:
    """Return (how many products matched, the first MAX_SEARCH_RESULTS of them).

    The total is returned separately because the list is capped. Without it the agent
    sees six hoodies and tells the customer the shop sells six hoodies, when it sells
    twenty-seven.
    """
    results: list[tuple[int, ProductCard]] = []
    needle = (query or "").strip().lower()
    wanted_category = (category or "").strip().lower()

    for card, haystacks in search_index():
        if wanted_category and card.category.lower() != wanted_category:
            continue
        if max_price is not None and card.price > max_price:
            continue

        if not needle:
            results.append((0, card))
            continue

        # Substring matching on purpose: colors and tags are messy free text, so a
        # shopper asking for "gray" should still reach "dark heather gray".
        score = sum(weight for text, weight in haystacks if needle in text)
        if score:
            results.append((score, card))

    results.sort(key=lambda pair: (-pair[0], pair[1].name))
    return len(results), [card for _, card in results[:MAX_SEARCH_RESULTS]]


def nearest_alternatives(
    category: str | None = None, max_price: float | None = None
) -> dict[str, Any]:
    """What to offer when a search found nothing.

    A dead end ("we don't have that") loses the sale. This hands the agent the facts
    it needs to say something useful instead: what the category actually starts at, or
    what else we sell.
    """
    if category:
        total, _ = search_catalogue(category=category)
        if total:
            cheapest = min(
                c.price for c, _ in search_index() if c.category.lower() == category.lower()
            )
            return {
                "reason": "category_exists_but_filter_excluded_everything",
                "category": category,
                "products_in_category": total,
                "cheapest_price_in_category": cheapest,
            }
    return {"reason": "no_match", "categories_we_sell": category_counts()}


def stock_for(reference: str) -> StockAnswer:
    row = resolve_product(reference)
    if row is None:
        return StockAnswer(
            product_id=reference, name=reference, price=0.0,
            sizes_in_stock=[], sizes_sold_out=[], found=False,
        )
    with connect() as con:
        sizes = sizes_for(con, row["product_id"])
    return StockAnswer(
        product_id=row["product_id"],
        name=row["name"],
        price=row["price"],
        sizes_in_stock=[s for s in sizes if s.quantity > 0],
        sizes_sold_out=[s.size for s in sizes if s.quantity == 0],
    )


def facts_for(reference: str) -> ProductFacts | None:
    row = resolve_product(reference)
    if row is None:
        return None
    with connect() as con:
        sizes = sizes_for(con, row["product_id"])
    return ProductFacts(
        product_id=row["product_id"],
        name=row["name"],
        price=row["price"],
        garment_type=row["garment_type"],
        colors=json.loads(row["colors"]),
        description=row["description"],
        total_in_stock=sum(s.quantity for s in sizes),
    )


def category_counts() -> list[dict[str, Any]]:
    with connect() as con:
        rows = con.execute("SELECT garment_type FROM catalogue").fetchall()
    counts: dict[str, int] = {}
    for row in rows:
        name = categorize(row["garment_type"])
        counts[name] = counts.get(name, 0) + 1
    ordered = [c for c in CATEGORY_ORDER if c in counts]
    ordered += sorted(c for c in counts if c not in CATEGORY_ORDER)
    return [{"name": c, "count": counts[c]} for c in ordered]
