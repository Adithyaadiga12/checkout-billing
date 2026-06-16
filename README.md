# Checkout Billing System

A small web app that takes items (name, price, quantity), computes a cart total, applies a configurable offer, adds tax, and shows a printable final bill.

Built as a take-home case study.

---

## Tech stack

| Layer       | Choice                                                |
| ----------- | ----------------------------------------------------- |
| Backend     | **FastAPI** (Python 3.10+)                            |
| Templates   | **Jinja2**                                            |
| Frontend    | **HTMX** for partial swaps + **Tailwind CSS** via CDN |
| Validation  | **Pydantic v2**                                       |
| Config      | **PyYAML** (`config.yaml` — offer & tax are editable) |
| Tests       | **pytest** (24 unit tests)                            |
| Server      | **uvicorn**                                           |

No database. The cart lives in memory for one server process — keeps the demo focused on the billing logic, which is what the assignment actually asks for.

---

## Setup and run

```bash
# 1. Clone and enter
git clone https://github.com/Adithyaadiga12/checkout-billing.git
cd checkout-billing

# 2. Create a virtualenv (Python 3.10+)
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the dev server
uvicorn app.main:app --reload

# 5. Open http://127.0.0.1:8000
```

### Run the tests

```bash
pytest -v
```

---

## How to use the app

1. Open `http://127.0.0.1:8000`.
2. Add items using the **Name / Price / Quantity** form. The cart updates without a page reload (HTMX swap).
3. Adjust quantity inline with the **−** / **+** buttons next to each line, or remove a line with the trash icon.
4. While below the offer threshold the cart shows **"Add Rs. X more to unlock the offer"**. Once you cross it, that turns into a green confirmation showing how much was saved.
5. Apply a **coupon code** in the field below the totals. Try `WELCOME10` (10% off, no minimum) or `FLAT50` (Rs. 50 off, minimum cart value Rs. 500). The coupon stacks with the threshold offer.
6. Click **View final bill** to see the printable bill view (`/bill`). Use **Print bill** to save as PDF.

---

## How the math works

For a cart of items, the bill is computed in six steps:

```
1. subtotal          = sum(item.price × item.quantity)
2. offer_discount    = subtotal × offer.discount_percent / 100   (only if subtotal ≥ offer.threshold)
3. coupon_discount   = coupon-defined amount                    (only if a valid coupon is applied)
4. taxable_amount    = max(0, subtotal − offer_discount − coupon_discount)
5. tax               = taxable_amount × tax.percent / 100
6. total             = taxable_amount + tax
```

Every intermediate value is rounded to 2 decimal places, matching how most POS systems display money.

**Worked example** (default config: 10% off above Rs. 1000, GST 18%):

| Step           | Value      | Notes                                          |
| -------------- | ---------- | ---------------------------------------------- |
| Subtotal       | Rs. 1300.00 | 1× Bag @ 800 + 1× Notebook @ 500              |
| Discount       | Rs. 130.00  | 1300 ≥ 1000, so 10% off                       |
| Taxable amount | Rs. 1170.00 | 1300 − 130                                    |
| GST (18%)      | Rs. 210.60  | 1170 × 0.18                                   |
| **Total**      | **Rs. 1380.60** | 1170 + 210.60                            |

---

## API endpoints

All endpoints render HTML (mostly HTMX partials for the cart). The app is server-rendered — no JSON API.

| Method | Path                  | Returns      | Purpose                                            |
| ------ | --------------------- | ------------ | -------------------------------------------------- |
| GET    | `/`                   | Full page    | Add-item form + live cart                          |
| POST   | `/items`              | `#cart-region` partial | Add an item (form fields: name, price, quantity) |
| DELETE | `/items/{index}`      | `#cart-region` partial | Remove a line by index                   |
| POST   | `/items/{index}/inc`  | `#cart-region` partial | Increment line quantity by 1            |
| POST   | `/items/{index}/dec`  | `#cart-region` partial | Decrement line quantity by 1 (removes when it hits 0) |
| POST   | `/cart/clear`         | `#cart-region` partial | Empty the cart                           |
| POST   | `/cart/coupon`        | `#cart-region` partial | Apply a coupon (form field: `code`, case-insensitive). Renders inline error on invalid code or unmet minimum. |
| DELETE | `/cart/coupon`        | `#cart-region` partial | Remove the applied coupon                        |
| GET    | `/bill`               | Full page    | Final printable bill (friendly empty state if cart is empty) |

---

## Configuring the offer and tax

Edit `config.yaml`:

```yaml
offer:
  name: "10% off on orders above Rs. 1000"
  threshold: 1000.00
  discount_percent: 10.0

tax:
  name: "GST"
  percent: 18.0
```

Restart the server after editing. The default rule is: **if `subtotal ≥ threshold`, apply `discount_percent` off the subtotal.**

### Coupon codes

Codes live in the same `config.yaml`:

```yaml
coupons:
  WELCOME10:
    type: percent
    value: 10
    min_subtotal: 0
  FLAT50:
    type: flat
    value: 50
    min_subtotal: 500
```

| Code        | Effect                          | Minimum cart value |
| ----------- | ------------------------------- | ------------------ |
| `WELCOME10` | 10% off subtotal                | none               |
| `FLAT50`    | Rs. 50 off                      | Rs. 500            |

Codes are matched case-insensitively. Only one coupon can be active at a time — applying a new code replaces the previous one. Coupons **stack with** the threshold offer (both lines show separately on the bill so the math stays transparent). If the cart drops below a coupon's minimum, the code stays attached to the cart but the discount goes to Rs. 0 with a "needs cart value ≥ Rs. X" warning, so the user can either add more items or remove the coupon.

---

## Project layout

```
checkout-billing/
├── app/
│   ├── main.py          # FastAPI routes
│   ├── billing.py       # Pure billing math + in-memory Cart
│   ├── models.py        # Pydantic models (Item, Bill) with validation
│   ├── config.py        # Loads config.yaml into a typed AppConfig
│   └── templates/
│       ├── base.html
│       ├── index.html
│       ├── bill.html
│       └── partials/cart.html
├── tests/
│   └── test_billing.py  # 18 unit tests for math, validation, and cart
├── config.yaml          # Offer & tax — change without touching code
├── requirements.txt
├── pyproject.toml       # pytest config
└── README.md
```

---

## Assumptions

- **Currency:** Indian Rupees (`Rs.`) by default — easy to change in `config.yaml`.
- **Cart scope:** in-memory, single process. Refreshing the browser keeps the cart (server-side). Restarting the server clears it. A real deployment would use sessions or a DB.
- **Offer rule:** one simple threshold-based percentage discount. The threshold is inclusive (`subtotal ≥ 1000` triggers the 10%).
- **Coupons:** two demo codes live in `config.yaml` (percent and flat). They stack with the threshold offer and are applied to the original subtotal — i.e. each line on the bill is computed independently from the subtotal, not chained. This keeps the bill readable; a stricter "highest-discount-wins" rule would also be defensible.
- **Tax:** flat percentage applied to `(subtotal − offer_discount − coupon_discount)`. No per-item tax slabs, no inclusive-tax logic.
- **Rounding:** every money value is rounded to 2 decimal places at each step (subtotal, discount, taxable amount, tax, total) to match how POS systems usually display amounts.
- **Item merging:** adding the same name + same price increases the quantity of the existing line. Same name with a different price stays as a separate line (treated as a different SKU).
- **Validation:** price must be > 0, quantity must be a positive integer, name must be non-blank ≤ 80 chars. Bad input returns a friendly inline error in the cart panel.
- **Auth / multi-user:** out of scope.

---

## AI-assisted development — short note

I used **Claude (Anthropic's Claude Code CLI, model Claude Opus 4.7)** as my primary pair-programmer for this case study.

**How it helped.** I described the requirements and the stack I wanted (FastAPI + Jinja + HTMX + Tailwind, matching tooling I had recently been learning so I could speak to it in the interview). From there, Claude scaffolded the project layout, wrote the Pydantic models with field validators, generated the pure `calculate_bill` function, set up the HTMX-driven templates for live cart updates, and produced the pytest suite covering the math edge cases (zero cart, exactly-at-threshold, multi-item, rounding) and the cart merging behaviour. It also drafted this README.

Three specific moments where it added clear value:

1. **Audit against the rubric.** Once the first cut was working, I asked Claude to grade what I had against each evaluation criterion. It pointed out that the inline `+`/`−` quantity buttons were missing, that `GET /bill` on an empty cart returned a raw JSON error (unfriendly UX), and that a "spend Rs. X more to unlock the offer" hint would be a quick visible polish. I picked which of those to apply.
2. **HTMX patterns.** It got the swap targets (`hx-target="#cart-region"`, `hx-swap="outerHTML"`) and the post-submit form reset (`hx-on::after-request`) right on the first try — those are the kind of small idioms that are easy to look up but slow to assemble.
3. **Test edge cases.** The test for "subtotal exactly at the threshold" (Rs. 1000 → offer applies because of the `≥` rule) and the rounding test came from Claude prompting me to think about boundary conditions I hadn't written down.

**Challenges.** Scope control was the main one. The brief said "simple offer", so I started with one threshold-based percentage discount and shipped that first. Coupon codes came later, as a deliberate extension — I picked that addition over things like multi-currency, persistence, or admin UI because coupons are the most natural next step in a real checkout and they generalise the discount model cleanly (offer + coupon stack into the same "total discount" line of the math). The second was rounding — getting consistent two-decimal-place behaviour required rounding at each intermediate step rather than only at the end, which the test suite now pins down.
