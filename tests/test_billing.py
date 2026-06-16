"""Tests for the billing math and cart behaviour."""
import pytest
from pydantic import ValidationError

from app.billing import Cart, calculate_bill
from app.config import AppConfig, OfferConfig, TaxConfig
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
