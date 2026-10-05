"""Shared Pydantic types for the Campus Customs API and agent."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class SizeStock(BaseModel):
    size: str
    quantity: int

    @property
    def in_stock(self) -> bool:
        return self.quantity > 0


class ProductCard(BaseModel):
    """The shape every product card renders from, on the Products page and in chat.

    Problem 7 requires chat-recommended products to render as the same cards as the
    Products grid and to open the same detail page, so both paths return this type.
    """

    product_id: str
    name: str
    garment_type: str
    category: str = Field(description="Normalized browse category, e.g. 'Hoodies'.")
    price: float
    image_url: str
    colors: list[str]
    blurb: str = Field(description="First sentence of the description, for the card.")
    in_stock_sizes: list[str] = Field(
        default=[],
        description="Sizes with stock left, so the grid can warn before the click.",
    )


class ProductDetail(ProductCard):
    description: str
    search_tags: list[str]
    sizes: list[SizeStock]

    @property
    def total_stock(self) -> int:
        return sum(s.quantity for s in self.sizes)


# ---------------------------------------------------------------- accounts


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    """What the browser and the agent are allowed to see about a customer.

    Deliberately excludes password_hash so a hashed credential can never leak into
    an API response or into the agent's context window.
    """

    id: int
    first_name: str
    last_name: str
    email: EmailStr

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


# ---------------------------------------------------------------- chat


class ChatRequest(BaseModel):
    """What the chat widget sends on every turn.

    `product_id` is the page context Problem 8 needs: when the shopper is looking at a
    product and asks "do you have this in pink?", this is what "this" refers to.
    """

    message: str = Field(min_length=1, max_length=2000)
    page_path: str | None = None
    product_id: str | None = None


class ChatReply(BaseModel):
    """What the widget renders: prose plus the cards to show beneath it.

    `products` is never written by the language model. It is rebuilt from the database
    using the ids the tools actually returned, so the assistant cannot invent a product,
    a price, or a stock level even if it hallucinates in its prose.
    """

    reply_text: str
    products: list[ProductCard] = []


class StockAnswer(BaseModel):
    """A stock lookup, as the agent sees it."""

    product_id: str
    name: str
    price: float
    sizes_in_stock: list[SizeStock]
    sizes_sold_out: list[str]
    found: bool = True


class ProductFacts(BaseModel):
    """Description and price for one product, as the agent sees it."""

    product_id: str
    name: str
    price: float
    garment_type: str
    colors: list[str]
    description: str
    total_in_stock: int
