# Checkout Billing System

A small web app that takes items (name, price, quantity), computes a cart total, applies a configurable offer, adds tax, and shows a final printable bill.

Built as a take-home case study.

---

## Tech stack

| Layer    | Choice                                                      |
| -------- | ----------------------------------------------------------- |
| Backend  | **FastAPI** (Python 3.10+)                                  |
| Templates| **Jinja2**                                                  |
| Frontend | **HTMX** for partial swaps + **Tailwind CSS** via CDN       |
| Validation | **Pydantic v2**                                           |
| Config   | **PyYAML** (`config.yaml` — offer & tax are editable)       |
| Tests    | **pytest**                                                  |
| Server   | **uvicorn**                                                 |

No database. The cart lives in memory for one server process — keeps the demo focused on the billing logic, which is the part the assignment actually asks for.

---

## Setup and run

```bash
# 1. Clone and enter
git clone <your-repo-url> checkout-billing
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
2. Add items using the **Name / Price / Quantity** form. The cart updates without a page reload (HTMX).
3. Remove a line with the `×` button, or **Clear all** to empty the cart.
4. When the cart is non-empty the right panel shows a live breakdown: subtotal → offer → tax → total.
5. Click **View final bill** for the printable bill view (`/bill`). Use **Print bill** to save as PDF.

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

Restart the server after editing. The default rule is: **if `subtotal >= threshold`, apply `discount_percent` off the subtotal.**

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
│   └── test_billing.py  # 15 unit tests for math + validation + cart
├── config.yaml          # Offer & tax — change without touching code
├── requirements.txt
├── pyproject.toml       # pytest config
└── README.md
```

---

## Assumptions

- **Currency:** Indian Rupees (`Rs.`) by default — easy to change in `config.yaml`.
- **Cart scope:** in-memory, single process. Refreshing the browser keeps the cart (server-side). Restarting the server clears it. A real deployment would use sessions or a DB.
- **Offer rule:** one simple threshold-based percentage discount. The threshold is inclusive (`subtotal >= 1000` triggers the 10%).
- **Tax:** flat percentage applied to `(subtotal − discount)`. No per-item tax slabs, no inclusive-tax logic.
- **Rounding:** every money value is rounded to 2 decimal places at each step (subtotal, discount, taxable amount, tax, total) to match how POS systems usually display amounts.
- **Item merging:** adding the same name + same price increases the quantity of the existing line. Same name with a different price stays as a separate line (treated as a different SKU).
- **Validation:** price must be > 0, quantity must be a positive integer, name must be non-blank ≤ 80 chars. Bad input returns a friendly inline error in the cart panel.
- **Auth / multi-user:** out of scope.

---

## AI-assisted development — short note

I used **Claude (Anthropic's Claude Code CLI, model Claude Opus 4.7)** as my primary pair-programmer for this case study.

**How it helped.** I described the requirements and the stack I wanted (FastAPI + Jinja + HTMX + Tailwind, matching tooling I had recently learned so I could speak to it in the interview). Claude scaffolded the project layout, wrote the Pydantic models with sensible field validators, generated the pure `calculate_bill` function, set up the HTMX-driven templates for live cart updates, and produced the pytest suite covering the math edge cases (zero cart, exactly-at-threshold, multi-item, rounding) and the cart merging behaviour. It also drafted this README. My role was to specify the scope (one configurable offer, in-memory cart, no DB), make the trade-off decisions (single repo, simple offer rule, tests > extra features), review every file, and run the tests locally.

**Challenges.** The main thing I had to push back on was scope: the assistant initially suggested stacking offers, coupon codes, and a persistence layer, all of which the brief explicitly asked to keep simple. Keeping the offer logic to one well-tested rule made the code easier to defend in the interview. The second was rounding — getting consistent two-decimal-place behaviour required rounding at each intermediate step rather than only at the end, which the test suite now pins down.
