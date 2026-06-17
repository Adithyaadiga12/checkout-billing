"""FastAPI application — checkout billing system."""
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.billing import Cart, calculate_bill
from app.config import AppConfig, get_config
from app.models import Bill, Item

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Checkout Billing System")
cart = Cart()


def _current_state() -> tuple[AppConfig, Bill | None]:
    """Snapshot of (config, current bill). Bill is None for an empty cart."""
    config = get_config()
    bill = (
        calculate_bill(cart.items, config, cart.coupon_code)
        if not cart.is_empty()
        else None
    )
    return config, bill


def _render_cart(
    request: Request,
    *,
    error: str | None = None,
    coupon_error: str | None = None,
) -> HTMLResponse:
    """Render the cart partial. Always 200 — htmx 1.9 only swaps successful responses."""
    config, bill = _current_state()
    return templates.TemplateResponse(
        "partials/cart.html",
        {
            "request": request,
            "cart": cart,
            "bill": bill,
            "config": config,
            "error": error,
            "coupon_error": coupon_error,
        },
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    config, bill = _current_state()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "cart": cart, "bill": bill, "config": config},
    )


@app.post("/items", response_class=HTMLResponse)
def add_item(
    request: Request,
    name: str = Form(...),
    price: float = Form(...),
    quantity: int = Form(...),
):
    try:
        item = Item(name=name, price=price, quantity=quantity)
    except ValidationError as e:
        first = e.errors()[0]
        return _render_cart(request, error=f"{first['loc'][-1]}: {first['msg']}")
    cart.add(item)
    return _render_cart(request)


@app.delete("/items/{index}", response_class=HTMLResponse)
def remove_item(request: Request, index: int):
    cart.remove(index)
    return _render_cart(request)


@app.post("/items/{index}/inc", response_class=HTMLResponse)
def increment_item(request: Request, index: int):
    cart.update_quantity(index, +1)
    return _render_cart(request)


@app.post("/items/{index}/dec", response_class=HTMLResponse)
def decrement_item(request: Request, index: int):
    cart.update_quantity(index, -1)
    return _render_cart(request)


@app.post("/cart/clear", response_class=HTMLResponse)
def clear_cart(request: Request):
    cart.clear()
    return _render_cart(request)


@app.post("/cart/coupon", response_class=HTMLResponse)
def apply_coupon(request: Request, code: str = Form(...)):
    config = get_config()
    normalized = code.strip().upper()
    error: str | None = None

    if not normalized:
        error = "Please enter a coupon code."
    elif normalized not in config.coupons:
        error = f"Coupon code '{normalized}' is not valid."
    else:
        coupon = config.coupons[normalized]
        subtotal = sum(it.line_total for it in cart.items)
        if subtotal < coupon.min_subtotal:
            error = (
                f"Minimum cart value {config.currency_symbol}{coupon.min_subtotal:.2f} "
                f"required for {normalized}."
            )
        else:
            cart.set_coupon(normalized)

    return _render_cart(request, coupon_error=error)


@app.delete("/cart/coupon", response_class=HTMLResponse)
def remove_coupon(request: Request):
    cart.set_coupon(None)
    return _render_cart(request)


@app.get("/bill", response_class=HTMLResponse)
def view_bill(request: Request):
    config, bill = _current_state()
    return templates.TemplateResponse(
        "bill.html",
        {"request": request, "bill": bill, "config": config},
    )
