"""Pure billing logic. Stateless and easy to unit-test."""
from app.config import AppConfig
from app.models import Bill, Item


def _round(amount: float) -> float:
    return round(amount, 2)


def calculate_bill(items: list[Item], config: AppConfig) -> Bill:
    """Compute subtotal, offer discount, tax, and final total for a cart."""
    subtotal = _round(sum(item.line_total for item in items))

    offer = config.offer
    if subtotal >= offer.threshold and subtotal > 0:
        discount = _round(subtotal * offer.discount_percent / 100)
        offer_applied = True
    else:
        discount = 0.0
        offer_applied = False

    taxable_amount = _round(subtotal - discount)
    tax = _round(taxable_amount * config.tax.percent / 100)
    total = _round(taxable_amount + tax)

    return Bill(
        items=items,
        subtotal=subtotal,
        offer_applied=offer_applied,
        offer_name=offer.name,
        discount=discount,
        taxable_amount=taxable_amount,
        tax_name=config.tax.name,
        tax_percent=config.tax.percent,
        tax=tax,
        total=total,
    )


class Cart:
    """In-memory cart. One instance per running server process."""

    def __init__(self) -> None:
        self._items: list[Item] = []

    def add(self, item: Item) -> None:
        # Merge with an existing line if name + price match exactly.
        for existing in self._items:
            if existing.name.lower() == item.name.lower() and existing.price == item.price:
                existing.quantity += item.quantity
                return
        self._items.append(item)

    def remove(self, index: int) -> None:
        if 0 <= index < len(self._items):
            self._items.pop(index)

    def clear(self) -> None:
        self._items.clear()

    @property
    def items(self) -> list[Item]:
        return list(self._items)

    def is_empty(self) -> bool:
        return len(self._items) == 0
