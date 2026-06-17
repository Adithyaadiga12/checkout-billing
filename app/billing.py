"""Pure billing logic. Stateless and easy to unit-test."""
from app.config import AppConfig, CouponConfig, OfferConfig
from app.models import Bill, Item


def _round(amount: float) -> float:
    return round(amount, 2)


def _format_coupon_label(code: str, type_: str, value: float, currency_symbol: str) -> str:
    if type_ == "percent":
        return f"{code} ({value:g}% off)"
    return f"{code} ({currency_symbol}{value:.2f} off)"


def _apply_offer(subtotal: float, offer: OfferConfig) -> tuple[float, bool, float]:
    """Compute the threshold-based offer discount.

    Returns: (discount, applied, amount_to_offer)
    - discount: rupees off the subtotal
    - applied: True if subtotal met the threshold
    - amount_to_offer: how much more the cart needs to reach the threshold (0 if already met)
    """
    if subtotal >= offer.threshold and subtotal > 0:
        return _round(subtotal * offer.discount_percent / 100), True, 0.0
    return 0.0, False, _round(offer.threshold - subtotal)


def _apply_coupon(
    subtotal: float,
    offer_discount: float,
    coupon_code: str | None,
    coupons: dict[str, CouponConfig],
    currency_symbol: str,
) -> tuple[str | None, str, float, float]:
    """Resolve and compute a coupon discount.

    Returns: (resolved_code, label, discount, min_subtotal)
    - resolved_code: the code if found in config, else None
    - label: human-readable like "WELCOME10 (10% off)" or "" when no coupon
    - discount: rupees off (0 if min_subtotal not met)
    - min_subtotal: surfaced so the UI can render "needs Rs. X more"
    """
    if not coupon_code or coupon_code not in coupons:
        return None, "", 0.0, 0.0

    coupon = coupons[coupon_code]
    label = _format_coupon_label(coupon_code, coupon.type, coupon.value, currency_symbol)

    if subtotal < coupon.min_subtotal or subtotal <= 0:
        return coupon_code, label, 0.0, coupon.min_subtotal

    if coupon.type == "percent":
        discount = _round(subtotal * coupon.value / 100)
    else:
        # Don't let a flat coupon discount more than what's left to pay after the offer
        remaining = max(0.0, subtotal - offer_discount)
        discount = _round(min(coupon.value, remaining))

    return coupon_code, label, discount, coupon.min_subtotal


def calculate_bill(
    items: list[Item],
    config: AppConfig,
    coupon_code: str | None = None,
) -> Bill:
    """Compute subtotal, threshold offer, optional coupon, tax, and final total."""
    subtotal = _round(sum(item.line_total for item in items))

    discount, offer_applied, amount_to_offer = _apply_offer(subtotal, config.offer)
    resolved_code, coupon_label, coupon_discount, coupon_min_subtotal = _apply_coupon(
        subtotal, discount, coupon_code, config.coupons, config.currency_symbol
    )

    total_discount = discount + coupon_discount
    taxable_amount = _round(max(0.0, subtotal - total_discount))
    tax = _round(taxable_amount * config.tax.percent / 100)
    total = _round(taxable_amount + tax)

    return Bill(
        items=items,
        subtotal=subtotal,
        offer_applied=offer_applied,
        offer_name=config.offer.name,
        offer_threshold=config.offer.threshold,
        amount_to_offer=amount_to_offer,
        discount=discount,
        coupon_code=resolved_code,
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
