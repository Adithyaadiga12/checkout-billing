"""Pure billing logic. Stateless and easy to unit-test."""
from app.config import AppConfig
from app.models import Bill, Item


def _round(amount: float) -> float:
    return round(amount, 2)


def _format_coupon_label(code: str, type_: str, value: float, currency_symbol: str) -> str:
    if type_ == "percent":
        return f"{code} ({value:g}% off)"
    return f"{code} ({currency_symbol}{value:.2f} off)"


def calculate_bill(
    items: list[Item],
    config: AppConfig,
    coupon_code: str | None = None,
) -> Bill:
    """Compute subtotal, threshold offer, optional coupon, tax, and final total."""
    subtotal = _round(sum(item.line_total for item in items))

    # --- Threshold offer ---
    offer = config.offer
    if subtotal >= offer.threshold and subtotal > 0:
        discount = _round(subtotal * offer.discount_percent / 100)
        offer_applied = True
        amount_to_offer = 0.0
    else:
        discount = 0.0
        offer_applied = False
        amount_to_offer = _round(offer.threshold - subtotal)

    # --- Coupon (optional, stacks with threshold offer) ---
    coupon_label = ""
    coupon_discount = 0.0
    coupon_min_subtotal = 0.0
    coupon = config.coupons.get(coupon_code) if coupon_code else None
    if coupon is not None:
        coupon_label = _format_coupon_label(
            coupon_code, coupon.type, coupon.value, config.currency_symbol
        )
        coupon_min_subtotal = coupon.min_subtotal
        if subtotal >= coupon.min_subtotal and subtotal > 0:
            if coupon.type == "percent":
                coupon_discount = _round(subtotal * coupon.value / 100)
            else:
                # Don't let a flat coupon discount more than what's left to pay
                remaining = max(0.0, subtotal - discount)
                coupon_discount = _round(min(coupon.value, remaining))
    else:
        # Coupon code on cart but not in config (shouldn't happen via UI, but be safe)
        coupon_code = None

    total_discount = discount + coupon_discount
    taxable_amount = _round(max(0.0, subtotal - total_discount))
    tax = _round(taxable_amount * config.tax.percent / 100)
    total = _round(taxable_amount + tax)

    return Bill(
        items=items,
        subtotal=subtotal,
        offer_applied=offer_applied,
        offer_name=offer.name,
        offer_threshold=offer.threshold,
        amount_to_offer=amount_to_offer,
        discount=discount,
        coupon_code=coupon_code,
        coupon_label=coupon_label,
        coupon_discount=coupon_discount,
        coupon_min_subtotal=coupon_min_subtotal,
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
        self.coupon_code: str | None = None

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

    def update_quantity(self, index: int, delta: int) -> None:
        """Adjust quantity by delta. Removes the line if quantity drops to 0."""
        if not (0 <= index < len(self._items)):
            return
        item = self._items[index]
        new_qty = item.quantity + delta
        if new_qty < 1:
            self._items.pop(index)
        else:
            item.quantity = new_qty

    def set_coupon(self, code: str | None) -> None:
        self.coupon_code = code

    def clear(self) -> None:
        self._items.clear()
        self.coupon_code = None

    @property
    def items(self) -> list[Item]:
        return list(self._items)

    def is_empty(self) -> bool:
        return len(self._items) == 0
