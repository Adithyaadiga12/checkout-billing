"""Pydantic models for cart items and bills."""
from pydantic import BaseModel, Field, field_validator


class Item(BaseModel):
    """A single item in the cart."""

    name: str = Field(min_length=1, max_length=80)
    price: float = Field(gt=0)
    quantity: int = Field(gt=0)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be blank")
        return v

    @property
    def line_total(self) -> float:
        return round(self.price * self.quantity, 2)


class Bill(BaseModel):
    """Final computed bill."""

    items: list[Item]
    subtotal: float
    offer_applied: bool
    offer_name: str
    offer_threshold: float
    amount_to_offer: float  # 0 when offer already applied; otherwise "spend this much more"
    discount: float
    taxable_amount: float
    tax_name: str
    tax_percent: float
    tax: float
    total: float
