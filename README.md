# Checkout Billing System

A small web app that takes items (name, price, quantity), computes a cart total, applies a configurable offer + coupon, adds tax, and shows a printable final bill.

Built as a take-home case study.

---

## Tech stack

**Backend:** FastAPI · **Templates:** Jinja2 · **Frontend:** HTMX + Tailwind (via CDN) · **Validation:** Pydantic v2 · **Config:** YAML · **Tests:** pytest (24 unit tests)

No database — the cart lives in memory for the lifetime of the server process. Keeps the demo focused on billing logic, which is what the brief asks for.

---

## Setup and run

```bash
git clone https://github.com/Adithyaadiga12/checkout-billing.git
cd checkout-billing
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000**. Run tests with `pytest -v`.

---

## What it does

- Add items via a form; cart updates live (HTMX, no page reload).
- Inline `+` / `−` quantity buttons on each cart line.
- Threshold offer: **10% off above Rs. 1000** (configurable in `config.yaml`). UI shows "Add Rs. X more to unlock" when below threshold.
- Coupon codes — apply by typing in the field below totals; stacks with the offer.
- Final printable bill at `/bill`.

### Coupons

| Code        | Effect            | Min cart value |
| ----------- | ----------------- | -------------- |
| `WELCOME10` | 10% off subtotal  | none           |
| `FLAT50`    | Rs. 50 off        | Rs. 500        |

Codes are case-insensitive. Only one active at a time. Edit `config.yaml` to add or change them.

---

## Assumptions

- Currency is INR (`Rs.`); edit `config.yaml` to change.
- Cart is in-memory per server process — restart clears it. A real deployment would use sessions or a DB.
- Offer rule: simple threshold-based percentage discount. Threshold is inclusive (`subtotal ≥ 1000` triggers).
- Same name + same price merges into one line (treated as the same SKU). Same name + different price stays separate.
- Coupons stack with the offer; each discount is applied to the original subtotal so both lines are independently auditable on the bill.
- Every money value is rounded to 2 decimals at each step.
- Validation: price > 0, quantity ≥ 1, name non-blank ≤ 80 chars. Bad input → friendly inline error.
- Auth / multi-user / persistence are out of scope.

---

## AI-assisted development — short note

I used **Claude (Anthropic's Claude Code CLI, model Claude Opus 4.7)** as my primary pair-programmer. I described the requirements and the stack I wanted to use (FastAPI + Jinja + HTMX + Tailwind — tooling I had been learning so I could speak to it in the interview). Claude scaffolded the project, wrote the Pydantic models with validators, the pure `calculate_bill` function, the HTMX-driven templates for the live cart, the pytest suite covering math edge cases (zero cart, exactly-at-threshold, multi-item, rounding), and this README. Three specific moments stand out: (1) once the first cut was working, I asked Claude to audit it against each evaluation criterion — it spotted that inline `+`/`−` qty buttons were missing, that `GET /bill` on an empty cart returned a raw JSON error, and that a "spend Rs. X more to unlock the offer" hint would be a quick UX win. (2) It got the HTMX swap idioms (`hx-target`, `hx-swap="outerHTML"`, `hx-on::after-request`) right the first time. (3) The boundary-case tests (subtotal exactly at the threshold; rounding at 33.33 × 3) came from Claude prompting me to think about edges I hadn't written down.

The main thing I had to push back on was scope: the assistant initially proposed stacking offers and a persistence layer, both of which the brief asked to keep simple. I shipped one threshold-based offer first, then added coupon codes as a deliberate extension because they generalise the discount model cleanly (offer + coupon stack into the same "total discount" line of the math). Rounding was the other thing — getting consistent two-decimal-place behaviour required rounding at each intermediate step, which the test suite now pins down.
