"""Campus Customs API.

Run from inside the backend/ folder:

    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3

from dotenv import load_dotenv
from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic_ai.exceptions import ModelHTTPError

import agent as shop_agent
import tools as shop
from models import (
    ChatReply,
    ChatRequest,
    LoginRequest,
    ProductCard,
    ProductDetail,
    RegisterRequest,
    UserPublic,
)
from tools import DATA_DIR, PROJECT_ROOT, ShopDeps, connect

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT.parent / ".env")

# ------------------------------------------------------------------ passwords

# The seeded accounts store "pbkdf2_sha256$<salt>$<hex>" with no iteration count in
# the string, so the count is fixed here. 120_000 is the value the course data was
# generated with — changing it would lock the grader's test user out.
HASH_ALGO = "pbkdf2_sha256"
HASH_ITERATIONS = 120_000
SESSION_COOKIE = "cc_session"
SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev-only-campus-customs-secret")


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), HASH_ITERATIONS
    ).hex()
    return f"{HASH_ALGO}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algo != HASH_ALGO:
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), HASH_ITERATIONS
    ).hex()
    # Constant-time, so a wrong password cannot be narrowed down by timing.
    return hmac.compare_digest(candidate, digest)


# ------------------------------------------------------------------ sessions


def sign_session(user_id: int) -> str:
    sig = hmac.new(
        SESSION_SECRET.encode(), str(user_id).encode(), hashlib.sha256
    ).hexdigest()
    return f"{user_id}.{sig}"


def read_session(cookie: str | None) -> int | None:
    """Return the user id only if the cookie carries a valid signature.

    The id is signed rather than stored raw so a shopper cannot edit the cookie to
    become another customer — which matters because the agent is told who it is
    talking to based on this value.
    """
    if not cookie or "." not in cookie:
        return None
    raw_id, _, sig = cookie.partition(".")
    if not raw_id.isdigit():
        return None
    expected = hmac.new(
        SESSION_SECRET.encode(), raw_id.encode(), hashlib.sha256
    ).hexdigest()
    return int(raw_id) if hmac.compare_digest(expected, sig) else None


# ------------------------------------------------------------------ app

app = FastAPI(title="Campus Customs API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if DATA_DIR.exists():
    app.mount("/static", StaticFiles(directory=DATA_DIR), name="static")


shop.ensure_schema()


@app.get("/api/health")
def health() -> dict:
    with connect() as con:
        count = con.execute("SELECT COUNT(*) FROM catalogue").fetchone()[0]
    return {"status": "ok", "products": count}


# ------------------------------------------------------------------ catalogue


@app.get("/api/categories")
def categories() -> list[dict]:
    return shop.category_counts()


@app.get("/api/products", response_model=list[ProductCard])
def list_products(category: str | None = None, q: str | None = None) -> list[ProductCard]:
    with connect() as con:
        rows = con.execute("SELECT * FROM catalogue ORDER BY name").fetchall()

    cards = [shop.to_card(row) for row in rows]

    if category and category.lower() != "all":
        wanted = category.lower()
        cards = [c for c in cards if c.category.lower() == wanted]

    if q:
        needle = q.lower()
        by_id = {row["product_id"]: row for row in rows}
        cards = [
            c
            for c in cards
            if needle in c.name.lower()
            or needle in by_id[c.product_id]["description"].lower()
            or needle in by_id[c.product_id]["search_tags"].lower()
            or needle in by_id[c.product_id]["colors"].lower()
        ]

    return shop.attach_stock(cards)


@app.get("/api/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: str) -> ProductDetail:
    detail = shop.product_detail(product_id)
    if detail is None:
        raise HTTPException(404, f"No product '{product_id}'")
    return detail


# ------------------------------------------------------------------ accounts


def row_to_user(row: sqlite3.Row) -> UserPublic:
    # first_name / last_name were added to the table after the original rows existed,
    # so they can be NULL. Fall back to splitting the older single `name` column.
    first = row["first_name"]
    last = row["last_name"]
    if not first and not last:
        parts = (row["name"] or "").split(" ", 1)
        first = parts[0]
        last = parts[1] if len(parts) > 1 else ""
    return UserPublic(
        id=row["id"], first_name=first or "", last_name=last or "", email=row["email"]
    )


def load_user(user_id: int) -> UserPublic | None:
    with connect() as con:
        row = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return row_to_user(row) if row else None


def current_user(cc_session: str | None) -> UserPublic | None:
    user_id = read_session(cc_session)
    return load_user(user_id) if user_id else None


def set_session_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        sign_session(user_id),
        httponly=True,  # unreadable from JavaScript, so XSS cannot steal the session
        samesite="lax",
        max_age=60 * 60 * 24 * 14,
        path="/",
    )


@app.post("/api/auth/register", response_model=UserPublic, status_code=201)
def register(body: RegisterRequest, response: Response) -> UserPublic:
    email = body.email.strip().lower()
    full_name = f"{body.first_name.strip()} {body.last_name.strip()}".strip()

    with connect() as con:
        existing = con.execute(
            "SELECT 1 FROM users WHERE lower(email) = ?", (email,)
        ).fetchone()
        if existing:
            raise HTTPException(409, "An account with that email already exists.")

        cur = con.execute(
            """INSERT INTO users (name, email, password_hash, first_name, last_name)
               VALUES (?, ?, ?, ?, ?)""",
            (
                full_name,
                email,
                hash_password(body.password),
                body.first_name.strip(),
                body.last_name.strip(),
            ),
        )
        con.commit()
        user_id = cur.lastrowid

    set_session_cookie(response, user_id)
    return UserPublic(
        id=user_id,
        first_name=body.first_name.strip(),
        last_name=body.last_name.strip(),
        email=email,
    )


@app.post("/api/auth/login", response_model=UserPublic)
def login(body: LoginRequest, response: Response) -> UserPublic:
    with connect() as con:
        row = con.execute(
            "SELECT * FROM users WHERE lower(email) = ?", (body.email.strip().lower(),)
        ).fetchone()

    # Same message whether the email is unknown or the password is wrong, so the
    # endpoint cannot be used to discover which addresses have accounts.
    if row is None or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(401, "That email and password do not match.")

    set_session_cookie(response, row["id"])
    return row_to_user(row)


@app.post("/api/auth/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


@app.get("/api/auth/me", response_model=UserPublic | None)
def me(cc_session: str | None = Cookie(default=None)) -> UserPublic | None:
    return current_user(cc_session)


# ------------------------------------------------------------------ chat


@app.get("/api/chat/history")
def chat_history(cc_session: str | None = Cookie(default=None)) -> list[dict]:
    """Past conversation for the signed-in customer. Empty list for guests."""
    user = current_user(cc_session)
    return shop.load_history(user.id) if user else []


@app.post("/api/chat", response_model=ChatReply)
async def chat(
    body: ChatRequest, cc_session: str | None = Cookie(default=None)
) -> ChatReply:
    user = current_user(cc_session)

    deps = ShopDeps(
        user=user,
        current_product_id=body.product_id,
        page_path=body.page_path,
    )

    # Guests can chat, but only signed-in customers get a conversation that persists.
    history = shop.load_history(user.id) if user else []

    try:
        reply = await shop_agent.answer(
            body.message, deps, shop_agent.history_to_messages(history)
        )

        if user:
            shop.save_turn(
                user.id, "user", body.message,
                page_path=body.page_path, product_context=body.product_id,
            )
            shop.save_turn(
                user.id, "assistant", reply.reply_text, products=reply.products,
                page_path=body.page_path, product_context=body.product_id,
            )

        return reply

    except ModelHTTPError as exc:
        shop.audit("chat", {"message": body.message}, f"model {exc.status_code}", "model_error")
        # The upstream provider runs its own content filter and rejects some messages
        # with a 400 before the model ever sees them. Retrying cannot help, so answer
        # in character instead of showing the shopper a server error.
        if exc.status_code == 400:
            return ChatReply(
                reply_text=(
                    "That is not something I can help with, but I am happy to help you "
                    "find Yale gear — tell me a style, color, or budget."
                )
            )
        raise HTTPException(
            502, "The shop assistant is having trouble right now. Try again in a moment."
        ) from exc

    except Exception as exc:  # noqa: BLE001 - surfaced to the shopper as a soft failure
        shop.audit(
            "chat", {"message": body.message}, f"{type(exc).__name__}: {exc}", "error"
        )
        raise HTTPException(
            502, "The shop assistant is having trouble right now. Try again in a moment."
        ) from exc
