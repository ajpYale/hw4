"""The Campus Customs shop assistant: a PydanticAI agent over the course model."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

import tools as shop
from models import ChatReply, ProductFacts, StockAnswer
from tools import ShopDeps

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
PROMPT_PATH = BACKEND_DIR / "prompts" / "prompt.md"

# The key lives in hw4/.env if present, otherwise the parent folder's .env.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT.parent / ".env")

MODEL_NAME = os.environ.get("CAMPUS_CUSTOMS_MODEL", "gpt-5.6-luna")
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# How many model turns one customer message may take. Each tool call costs a round
# trip, so this bounds both latency and spend on a single reply.
MAX_TOOL_STEPS = 5
MAX_TOOL_CALLS = 6


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def build_agent() -> Agent[ShopDeps, str]:
    api_key = os.environ.get("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError(
            "PORTKEY_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    client = AsyncOpenAI(
        api_key="unused-openai-key",
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": api_key},
        timeout=60.0,
    )
    model = OpenAIChatModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))

    # prompt.md goes in as `instructions`, not `system_prompt`. PydanticAI only sends a
    # system_prompt when the message history is empty, so a signed-in customer with
    # saved history would otherwise get a model with no voice, tool or safety rules.
    # Instructions are sent on every request.
    agent = Agent(
        model,
        deps_type=ShopDeps,
        instructions=load_system_prompt(),
        retries=2,
    )

    @agent.instructions
    def who_and_where(ctx: RunContext[ShopDeps]) -> str:
        """Per-turn context: who is shopping and what they are looking at.

        This is an instructions function rather than part of prompt.md because it
        changes every request, and Problem 8 needs "do you have this in pink?" to
        resolve against the product currently on screen.
        """
        lines: list[str] = []

        if ctx.deps.user:
            lines.append(
                f"You are talking to {ctx.deps.user.full_name} "
                f"({ctx.deps.user.email}). Greet them by first name when it feels "
                f"natural, but do not repeat it every message."
            )
        else:
            lines.append(
                "You are talking to a guest who is not logged in. Do not ask for "
                "personal details."
            )

        if ctx.deps.current_product_id:
            facts = shop.facts_for(ctx.deps.current_product_id)
            if facts:
                lines.append(
                    f"They are currently viewing the product page for "
                    f"'{facts.name}' (product_id: {facts.product_id}). If they say "
                    f'"this" or "it" without naming something else, they mean this '
                    f"product."
                )

        return "\n".join(lines)

    # ---------------------------------------------------------------- tools

    @agent.tool
    def search_products(
        ctx: RunContext[ShopDeps],
        query: str | None = None,
        category: str | None = None,
        max_price: float | None = None,
    ) -> dict:
        """Search the Campus Customs catalogue.

        Use this whenever the customer asks what we carry, asks about a type of item,
        a color, a design, or a budget. The matching products are shown to the
        customer as clickable cards automatically, so summarise rather than listing
        them all out.

        The result has a `total_matches` count and a shorter `showing` list. Quote
        `total_matches` when you tell the customer how many we have — the list is only
        a sample of them.

        Args:
            query: Free text such as "hoodie", "gray", "Harvard game", "baseball".
            category: One of Hoodies, Crewnecks, T-Shirts, Quarter-Zips, Jackets,
                Performance. Use this when the customer names a garment type.
            max_price: Only return products at or below this price in dollars.
        """
        total, cards = shop.search_catalogue(
            query=query, category=category, max_price=max_price
        )
        ctx.deps.remember([c.product_id for c in cards])
        shop.audit(
            "search_products",
            {"query": query, "category": category, "max_price": max_price},
            f"{total} matches, showing {len(cards)}: {[c.product_id for c in cards]}",
        )
        result: dict = {
            "total_matches": total,
            "showing": [
                {
                    "product_id": c.product_id,
                    "name": c.name,
                    "category": c.category,
                    "price": c.price,
                    "colors": c.colors,
                }
                for c in cards
            ],
        }

        # A bare "we don't have that" ends the conversation. Hand the agent something
        # to offer instead — what the category really starts at, or what we do sell.
        if total == 0:
            result["alternatives"] = shop.nearest_alternatives(
                category=category, max_price=max_price
            )

        return result

    @agent.tool
    def get_product_facts(ctx: RunContext[ShopDeps], product: str) -> ProductFacts | str:
        """Look up the description, price, colors and total stock for one product.

        Use this for "what is this made of", "what colors does it come in", "how much
        is it" and similar questions about a specific item.

        Args:
            product: The product_id, or the product name if you do not have the id.
        """
        facts = shop.facts_for(product)
        shop.audit(
            "get_product_facts",
            {"product": product},
            facts.product_id if facts else "not found",
            stop_reason="ok" if facts else "no_match",
        )
        if facts is None:
            return f"No product matching '{product}' is in the catalogue."
        ctx.deps.remember([facts.product_id])
        return facts

    @agent.tool
    def check_stock(ctx: RunContext[ShopDeps], product: str) -> StockAnswer | str:
        """Check which sizes of a product are in stock and how many are left.

        Always use this before telling a customer whether something is available.
        Report sold-out sizes honestly.

        Args:
            product: The product_id, or the product name if you do not have the id.
        """
        answer = shop.stock_for(product)
        shop.audit(
            "check_stock",
            {"product": product},
            f"in_stock={[s.size for s in answer.sizes_in_stock]} "
            f"sold_out={answer.sizes_sold_out}"
            if answer.found
            else "not found",
            stop_reason="ok" if answer.found else "no_match",
        )
        if not answer.found:
            return f"No product matching '{product}' is in the catalogue."
        ctx.deps.remember([answer.product_id])
        return answer

    @agent.tool_plain
    def list_categories() -> list[dict]:
        """List the garment categories the shop sells and how many designs are in each.

        Use this for broad questions like "what do you sell?".
        """
        counts = shop.category_counts()
        shop.audit("list_categories", {}, f"{len(counts)} categories")
        return counts

    return agent


def history_to_messages(history: list[dict]) -> list[ModelMessage]:
    """Turn stored chat rows into the message list PydanticAI replays to the model.

    Only the prose is replayed. The product cards attached to an old reply are not
    resent, because the model does not need them to follow the thread and they would
    cost tokens on every subsequent turn.
    """
    messages: list[ModelMessage] = []
    for row in history:
        if row["role"] == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=row["content"])]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=row["content"])]))
    return messages


async def answer(
    message: str,
    deps: ShopDeps,
    history: list | None = None,
) -> ChatReply:
    """Run one customer turn and return prose plus the cards to render.

    The product cards are rebuilt from the database using the ids the tools recorded,
    never from anything the model wrote, so a hallucinated price cannot reach the page.
    """
    agent = build_agent()
    result = await agent.run(
        message,
        deps=deps,
        message_history=history or [],
        usage_limits=UsageLimits(
            request_limit=MAX_TOOL_STEPS,
            tool_calls_limit=MAX_TOOL_CALLS,
        ),
    )

    # One entry per completed agent loop, so the audit trail shows how each turn ended
    # and not just which tools it called. Failed runs are logged by main.py.
    usage = result.usage
    shop.audit(
        "chat",
        {"message": message, "product_id": deps.current_product_id},
        f"{usage.requests} model requests, {usage.tool_calls} tool calls, "
        f"{len(deps.matched)} products shown",
        stop_reason=result.response.finish_reason or "stop",
    )

    return ChatReply(
        reply_text=result.output,
        products=shop.cards_for_ids(deps.matched),
    )
