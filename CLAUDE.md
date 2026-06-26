# CLAUDE.md

Agent and developer instructions for the DepositEase codebase.
For project overview, features, pages, API reference, and demo accounts — read **README.md** first.

---

## Before making any change

1. Read the relevant router in `routers/` before editing backend logic.
2. Read the corresponding template in `templates/` and its JS in `static/js/` before touching frontend.
3. Check `models.py` if the change affects stored fields — adding a column requires deleting `depositease.db` and re-running `seed.py`, or running `ALTER TABLE` manually on the live DB.
4. Run `uvicorn main:app --reload` and test the affected page in a browser before marking a task done.

---

## Coding rules

- No comments unless the WHY is non-obvious. GDPR comments in the existing code are intentional — keep them.
- No docstrings beyond the single-line ones already on key endpoints.
- No new dependencies without explicit approval — the stack is intentionally minimal.
- No mocking — the synthetic bank generator in `registration.py::connect_bank` is the test double; do not layer `unittest.mock` on top.
- No feature flags — just change the code.
- Prefer editing existing files to creating new ones.
- Do not add error handling for impossible cases — trust FastAPI validation and SQLAlchemy.

---

## Backend conventions

- All API routes live under `/api/v1/` and are registered in `main.py` via `app.include_router(...)`.
- POST endpoints use `Form(...)` — not JSON body. Match the existing pattern in every router.
- DB sessions come from `Depends(get_db)` — never instantiate a session manually.
- Use `db.get(Model, pk)` for primary-key lookups; `db.query(Model).filter(...)` for conditional queries.
- `Application.status` transitions: `draft` → `pending` (after income step) → `approved` or `rejected` (after scoring).
- Reference numbers are formatted as `DE-{app.id:06d}` — never change this format.
- The `credit_score` calculation line in `scoring.py` is authoritative for weights (40/20/20/20). The dimension-level comments in that file showing 35/30/20/15 are stale and wrong — ignore them.

---

## Scoring engine internals (routers/scoring.py)

These details are not in README — they matter when touching the scoring logic.

### Sub-dimension formulas

**Dimension 1 — Ability to Pay (weight 0.40)**
- `aff`: rent/income — ≤25%→100, ≤30%→80, ≤35%→60, ≤40%→40, >40%→20
- `dti_s`: debt/income — ≤10%→100, ≤20%→80, ≤30%→60, ≤40%→40, >40%→10
- `emp_bonus`: full-time permanent +10, full-time fixed or part-time +5
- Result: `min(100, aff*0.5 + dti_s*0.5 + emp_bonus)`

**Dimension 2 — Financial Stability (weight 0.20)**
- `cf`: CV of monthly income — ≤5%→100, ≤10%→80, ≤15%→60, ≤20%→40, >20%→20
- `liq`: savings/monthly_expenses — ≥3→100, ≥2→80, ≥1→60, ≥0.5→40, <0.5→20
- `res_bonus`: dutch_national +10, eu_citizen +5
- Result: `min(100, cf*0.5 + liq*0.5 + res_bonus)`

**Dimension 3 — Financial Discipline (weight 0.20)**
- Payment consistency (1 − late/total) × 100 → weight 40%
- Balance stability (1 − std/avg daily balance, per month averaged) → weight 30%
- Spending regularity (1 − CV of monthly discretionary totals) → weight 30%

**Dimension 4 — Behavioral Liquidity Risk (weight 0.20)**
- Overdraft rate (overdraft_days / 180): 0→100, ≤2%→80, ≤5%→60, ≤10%→40, >10%→10 → weight 35%
- Low-balance stress rate (low_balance_days / 180): same thresholds → weight 35%
- Rejected transaction rate (rejected / total): 0→100, ≤1%→80, ≤2%→60, ≤5%→40, >5%→10 → weight 30%

### Monthly repayment formula
Standard annuity: `P × r(1+r)^n / ((1+r)^n − 1)` where `r = annual_rate / 12`.

---

## Data model details (models.py)

README covers the high-level purpose. These field-level details matter when writing queries or adding columns.

**Tenant** — identity: `full_name`, `email` (unique), `date_of_birth`, `id_type` (bsn/passport), `bsn`, `passport_number`. Employment: `employment_status`, `contract_type`, `self_employed_duration`, `receives_duo`, `has_parttime_income`. Residency: `residency_status`, `permit_type`, `permit_expiry_date`. Flag: `bank_connected`.

**Document** — `doc_type` ∈ {`id_document`, `selfie`, `payslip`, `tax_return`, `duo_letter`, `rental_contract`}. Only `stored_filename` (path) goes in DB — never binary content.

**SyntheticBankStatement** — aggregated over 6 months: `monthly_income`, `monthly_expenses`, `savings_balance`, `monthly_debt_payments`, `late_payments`, `total_payment_obligations`, `overdraft_days`, `low_balance_days`, `rejected_transactions`, `total_transactions`. Per-month detail in `raw_json` (list of dicts with `income`, `expenses`, `discretionary`, `avg_daily_balance`, `std_daily_balance`, `low_balance_days`).

**Application** — scoring outputs: `credit_score`, `affordability_ratio`, `dti_ratio`, `payment_consistency`, `interest_rate`. Rental: `rental_address`, `rental_postal_code`, `monthly_rent`, `contract_term_months`, `landlord_name`. Loan terms: `amount_requested`, `monthly_repayment`, `repayment_months`. `status` ∈ {`draft`, `pending`, `approved`, `rejected`}.

---

## Landlord auth internals (routers/landlord_auth.py)

- Passwords are hardcoded in `LANDLORD_PASSWORDS` dict — move to env vars before any production deployment; do not remove that comment.
- Login generates `secrets.token_hex(32)`, stored in module-level `_sessions` dict (resets on server restart).
- Session TTL: 8 hours. Expired sessions are evicted on next access.
- Client sends the token as the `X-Landlord-Token` request header.
- `views.py::get_landlord_overview` calls `verify_token()` from `landlord_auth.py` to gate the company overview endpoint.
- Frontend stores the token in `localStorage` as `landlordToken` and the company name as `landlordName`.

---

## Frontend conventions

- All JS is vanilla — no React, Vue, or jQuery. Do not introduce any framework.
- Templates extend `base.html` via `{% extends "base.html" %}` + `{% block content %}`. The `page` variable highlights the active nav link.
- Multi-step form state in `register.js` lives in `currentStep` and `formData` — do not refactor into a component model.
- POST calls use `fetch()` with `FormData`; GET calls use query strings.
- Monetary values: `€` prefix, 2 decimal places. Dates: `DD MMM YYYY` (e.g. `15 Jun 2025`).

---

## Database rules

- Schema is auto-created by `Base.metadata.create_all(bind=engine)` on startup — never use Alembic or any migration tool.
- Never commit `depositease.db` — it is runtime state.
- Never commit files under `uploads/` — they are KYC documents.
- `seed.py` is idempotent: it skips any tenant whose email already exists. Safe to re-run at any time.

---

## GDPR constraints

- `bsn` and `passport_number` must never appear in API responses, logs, or error messages — GDPR-sensitive PII.
- Uploaded KYC files: store path only in `documents.stored_filename`; never embed binary in DB.
- Any new PII field must include a `# GDPR note:` comment explaining the data category and why it is stored.

---

## Security rules

- Never interpolate user input into raw SQL — use SQLAlchemy ORM exclusively.
- Never disable Jinja2 auto-escaping — all user-supplied strings must pass through the template engine.
- Never log form fields that may contain PII.
- Admin page has no authentication by design (MVP scope) — do not add auth without explicit instruction.

---

## What NOT to build without explicit instruction

- Real PSD2 / Open Banking integration
- Actual payment processing or bank transfers
- AFM licensing compliance features
- Admin page authentication
- Portal for the "Others" landlord option
- B2B landlord subscription billing (Phase 2)

---

## 404 / error handling

- The `http_exception_handler` in `main.py` routes errors by path prefix: `/api/v1/*` → JSON `{"detail": ...}`, everything else → `templates/404.html`.
- Do not change this routing logic without testing both branches.

---

## Manual testing checklist

When modifying any feature, verify all items that apply:

- [ ] `GET /health` → `{"status": "ok"}`
- [ ] Home page loads without JS errors
- [ ] `/apply` — full 3-step flow for a new email produces a decision page
- [ ] `/decision?application_id=<id>` — shows score, rate, and monthly repayment
- [ ] `/tenant` — email lookup returns dashboard and repayment schedule
- [ ] `/landlord` — reference number lookup (e.g. `DE-000001`) returns guarantee status
- [ ] `/landlord/tenants` — login succeeds, tenant table renders, logout clears state
- [ ] `/admin` — portfolio stats and application table load correctly
- [ ] Unknown URL → styled HTML 404 page (not FastAPI default JSON)
- [ ] `/api/v1/nonexistent` → JSON error (not HTML)

---

## Prompt engineering guidelines

- Do not modify backend logic (routers/, scoring engine, models) when the task is frontend-only
- Do not modify frontend templates when the task is backend-only
- When adding a new page, always update the Pages table in this file and in README.md
- Do not add new demo accounts or seed data without being asked
- Do not add authentication to the admin page — it is intentionally open for MVP
- Keep all HTML, CSS, and JS inside the existing templates/ and static/ structure; do not introduce new frameworks
- When in doubt about scope, ask before implementing

## Git workflow

- Two collaborators: **Ping** (backend — FastAPI, Python, database) and **Jenny** (frontend — HTML, CSS, JS).
- Commit after each self-contained change with a short imperative message.
- Never push directly to `main` without testing locally first.
