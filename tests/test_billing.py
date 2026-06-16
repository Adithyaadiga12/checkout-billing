"""Tests for the billing math and cart behaviour."""
import pytest
from pydantic import ValidationError

from app.billing import Cart, calculate_bill
from app.config import AppConfig, CouponConfig, OfferConfig, TaxConfig
from app.models import Item


@pytest.fixture
def config() -> AppConfig:
    return AppConfig(
        currency="INR",
        currency_symbol="Rs.",
        offer=OfferConfig(
            name="10% off above Rs. 1000",
            threshold=1000.0,
            discount_percent=10.0,
        ),
        tax=TaxConfig(name="GST", percent=18.0),
        coupons={
            "WELCOME10": CouponConfig(type="percent", value=10.0, min_subtotal=0),
            "FLAT50": CouponConfig(type="flat", value=50.0, min_subtotal=500.0),
        },
    )


# ---------- Item validation ----------

def test_item_rejects_zero_price():
    with pytest.raises(ValidationError):
        Item(name="x", price=0, quantity=1)


def test_item_rejects_negative_quantity():
    with pytest.raises(ValidationError):
        Item(name="x", price=10, quantity=-1)


def test_item_rejects_blank_name():
    with pytest.raises(ValidationError):
        Item(name="   ", price=10, quantity=1)


def test_item_line_total():
    item = Item(name="Pen", price=12.5, quantity=4)
    assert item.line_total == 50.0


# ---------- Billing math ----------

def test_empty_cart_is_zero(config):
    bill = calculate_bill([], config)
    assert bill.subtotal == 0
    assert bill.discount == 0
    assert bill.tax == 0
    assert bill.total == 0
    assert bill.offer_applied is False
    assert bill.amount_to_offer == 1000.0  # full threshold distance


def test_below_threshold_no_offer(config):
    # 500 < 1000 threshold — no discount, 18% GST applies
    items = [Item(name="Book", price=500, quantity=1)]
    bill = calculate_bill(items, config)
    assert bill.subtotal == 500.0
    assert bill.offer_applied is False
    assert bill.discount == 0.0
    assert bill.amount_to_offer == 500.0  # need 500 more to reach threshold
    assert bill.taxable_amount == 500.0
    assert bill.tax == 90.0  # 500 * 0.18
    assert bill.total == 590.0


def test_at_threshold_triggers_offer(config):
    # Exactly at threshold — offer should apply (>= rule)
    items = [Item(name="Bag", price=1000, quantity=1)]
    bill = calculate_bill(items, config)
    assert bill.offer_applied is True
    assert bill.discount == 100.0  # 10% of 1000
    assert bill.amount_to_offer == 0.0
    assert bill.taxable_amount == 900.0
    assert bill.tax == 162.0  # 900 * 0.18
    assert bill.total == 1062.0


def test_above_threshold_with_multiple_items(config):
    items = [
        Item(name="Shoes", price=800, quantity=1),
        Item(name="Socks", price=150, quantity=2),
    ]
    bill = calculate_bill(items, config)
    # subtotal = 800 + 300 = 1100
    assert bill.subtotal == 1100.0
    assert bill.offer_applied is True
    assert bill.discount == 110.0
    assert bill.taxable_amount == 990.0
    assert bill.tax == 178.2
    assert bill.total == 1168.2


def test_rounding_to_two_decimals(config):
    # Choose values that produce more than 2 decimals to verify rounding
    items = [Item(name="Tea", price=33.33, quantity=3)]
    bill = calculate_bill(items, config)
    # subtotal = 99.99, below threshold so no offer
    assert bill.subtotal == 99.99
    assert bill.offer_applied is False
    assert bill.tax == round(99.99 * 0.18, 2)
    assert bill.total == round(99.99 + bill.tax, 2)


# ---------- Cart behaviour ----------

def test_cart_merges_same_item():
    cart = Cart()
    cart.add(Item(name="Pen", price=10, quantity=2))
    cart.add(Item(name="pen", price=10, quantity=3))  # case-insensitive same name
    assert len(cart.items) == 1
    assert cart.items[0].quantity == 5


def test_cart_keeps_separate_if_price_differs():
    cart = Cart()
    cart.add(Item(name="Pen", price=10, quantity=1))
    cart.add(Item(name="Pen", price=15, quantity=1))
    assert len(cart.items) == 2


def test_cart_remove_by_index():
    cart = Cart()
    cart.add(Item(name="A", price=10, quantity=1))
    cart.add(Item(name="B", price=20, quantity=1))
    cart.remove(0)
    assert len(cart.items) == 1
    assert cart.items[0].name == "B"


def test_cart_remove_invalid_index_is_noop():
    cart = Cart()
    cart.add(Item(name="A", price=10, quantity=1))
    cart.remove(5)  # should not raise
    assert len(cart.items) == 1


def test_cart_clear():
    cart = Cart()
    cart.add(Item(name="A", price=10, quantity=1))
    cart.clear()
    assert cart.is_empty()


def test_cart_update_quantity_increments():
    cart = Cart()
    cart.add(Item(name="A", price=10, quantity=2))
    cart.update_quantity(0, +1)
    assert cart.items[0].quantity == 3


def test_cart_update_quantity_to_zero_removes_line():
    cart = Cart()
    cart.add(Item(name="A", price=10, quantity=1))
    cart.update_quantity(0, -1)
    assert cart.is_empty()


def test_cart_update_quantity_invalid_index_is_noop():
    cart = Cart()
    cart.add(Item(name="A", price=10, quantity=2))
    cart.update_quantity(5, +1)
    assert cart.items[0].quantity == 2


# ---------- Config edge cases ----------

def test_zero_tax_config():
    cfg = AppConfig(
        currency="INR",
        currency_symbol="Rs.",
        offer=OfferConfig(name="none", threshold=999999, discount_percent=0),
        tax=TaxConfig(name="None", percent=0),
    )
    items = [Item(name="X", price=100, quantity=1)]
    bill = calculate_bill(items, cfg)
    assert bill.tax == 0
    assert bill.total == 100


# ---------- Coupons ----------

def test_percent_coupon_applies_to_subtotal(config):
    items = [Item(name="X", price=300, quantity=1)]
    bill = calculate_bill(items, config, coupon_code="WELCOME10")
    assert bill.coupon_code == "WELCOME10"
    assert bill.coupon_discount == 30.0  # 10% of 300
    assert bill.offer_applied is False   # 300 < 1000 threshold
    # taxable = 300 - 30 = 270, tax = 270 * 0.18 = 48.60
    assert bill.taxable_amount == 270.0
    assert bill.tax == 48.6
    assert bill.total == 318.6


def test_flat_coupon_respects_min_subtotal_not_met(config):
    # 300 < FLAT50.min_subtotal (500) — coupon is on the bill but discount stays 0
    items = [Item(name="X", price=300, quantity=1)]
    bill = calculate_bill(items, config, coupon_code="FLAT50")
    assert bill.coupon_code == "FLAT50"
    assert bill.coupon_discount == 0.0
    assert bill.coupon_min_subtotal == 500.0
    # Bill should compute as if no coupon
    assert bill.total == round(300 * 1.18, 2)


def test_flat_coupon_applies_when_min_met(config):
    items = [Item(name="X", price=600, quantity=1)]
    bill = calculate_bill(items, config, coupon_code="FLAT50")
    assert bill.coupon_discount == 50.0
    assert bill.taxable_amount == 550.0
    assert bill.tax == 99.0  # 550 * 0.18
    assert bill.total == 649.0


def test_coupon_stacks_with_threshold_offer(config):
    # subtotal 1300 -> 10% offer = 130, WELCOME10 = 130 -> total discount 260
    items = [
        Item(name="A", price=800, quantity=1),
        Item(name="B", price=500, quantity=1),
    ]
    bill = calculate_bill(items, config, coupon_code="WELCOME10")
    assert bill.subtotal == 1300.0
    assert bill.offer_applied is True
    assert bill.discount == 130.0
    assert bill.coupon_discount == 130.0
    assert bill.taxable_amount == 1040.0
    assert bill.tax == 187.2
    assert bill.total == 1227.2


def test_unknown_coupon_is_ignored(config):
    items = [Item(name="X", price=300, quantity=1)]
    bill = calculate_bill(items, config, coupon_code="NOPE")
    assert bill.coupon_code is None
    assert bill.coupon_discount == 0.0


def test_cart_clear_also_drops_coupon():
    cart = Cart()
    cart.add(Item(name="A", price=10, quantity=1))
    cart.set_coupon("WELCOME10")
    cart.clear()
    assert cart.coupon_code is None
    assert cart.is_empty()
