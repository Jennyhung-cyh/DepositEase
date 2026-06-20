# DepositEase

**Rental deposit financing platform for the Dutch housing market.**

DepositEase is an RSM Fintech MVP that helps tenants cover their rental deposit upfront. Instead of paying a large lump sum, tenants apply for a short-term deposit loan, receive an instant AI-powered credit decision, and repay in monthly instalments. Landlords receive a simulated payout confirmation and can track their tenants' deposit status online.

---

## The problem

Moving to a new rental property in the Netherlands typically requires paying 1–3 months' rent as a deposit upfront — often €1,500–€4,500. For many tenants, especially students, expats, and young professionals, this is a significant financial barrier.

## The solution

DepositEase covers the deposit on behalf of the tenant. The tenant repays over 6–24 months at a competitive interest rate (8–12% p.a.), determined by an AI credit scoring engine that analyses synthetic bank statement data.

---

## Features

### For Tenants
- **3-step application** — identity verification, income & bank connection, rental details
- **Instant AI credit decision** — scored across 4 financial dimensions in seconds
- **Decision page** — shows approval status, interest rate, and monthly repayment amount
- **Repayment dashboard** — track progress, view full payment schedule, see remaining balance

### For Landlords
- **Individual lookup** — verify a tenant's deposit guarantee by reference number (e.g. `DE-000001`)
- **Company portal** — password-protected overview of all tenants and payout notifications, filtered by property management company
- **Supported companies** — Holland2Stay, Our Domain, Vesteda, Greystar

### For Admins (Internal)
- **Portfolio overview** — all applications with status, credit score, interest rate, and deposit amount
- **Overdue alerts** — flags loans where the repayment period has ended
- **Status filters** — filter by Approved / Pending / Rejected / Overdue

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.13, FastAPI |
| Frontend | HTML5, vanilla JavaScript, CSS3 |
| Database | SQLite (via SQLAlchemy ORM) |
| Data | Synthetic bank statement generator (no real PSD2/Open Banking) |
| Auth | In-memory session tokens (landlord portal) |

---

## Project structure

```
DepositEase/
├── main.py                  # FastAPI app, routes
├── models.py                # SQLAlchemy ORM models
├── database.py              # DB connection & session
├── seed.py                  # Demo data generator
├── requirements.txt
│
├── routers/
│   ├── registration.py      # Tenant registration API
│   ├── scoring.py           # AI credit scoring engine
│   ├── views.py             # Profile & decision APIs
│   ├── admin.py             # Admin overview API
│   └── landlord_auth.py     # Landlord authentication
│
├── templates/               # Jinja2 HTML templates
│   ├── base.html
│   ├── home.html
│   ├── register.html        # Apply flow (3 steps)
│   ├── decision.html        # Credit decision result
│   ├── tenant.html          # Tenant dashboard
│   ├── landlord.html        # Landlord lookup
│   ├── landlord_tenants.html # Landlord portal
│   └── admin.html           # Admin dashboard
│
├── static/
│   ├── css/style.css
│   └── js/
│       ├── register.js
│       ├── tenant.js
│       └── landlord.js
│
└── uploads/                 # Uploaded documents (auto-created)
```

---

## Getting started

### Prerequisites
- Python 3.10 or higher
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Jennyhung-cyh/DepositEase.git
cd DepositEase

# 2. Install dependencies
pip install -r requirements.txt

# 3. Seed demo data (creates 17 sample tenants across all landlords)
python3 seed.py

# 4. Start the server
uvicorn main:app --reload
```

Then open **http://localhost:8000** in your browser.

> Re-running `seed.py` is safe — it skips records that already exist.

---

## Pages

| URL | Description | Access |
|-----|-------------|--------|
| `/` | Home page | Public |
| `/apply` | Tenant application (3 steps) | Public |
| `/decision?application_id=` | Credit decision result | Public |
| `/tenant` | Repayment dashboard (lookup by email) | Tenant |
| `/landlord` | Guarantee lookup by reference number | Landlord |
| `/landlord/tenants` | Company portal (login required) | Landlord |
| `/admin` | Internal portfolio overview | Internal |

---

## Demo accounts

### Tenant dashboard
Go to `/tenant` and enter any of these emails:

| Name | Email | Status |
|------|-------|--------|
| Jan de Vries | jan.devries@gmail.com | Approved |
| Sophie Bakker | sophie.bakker@gmail.com | Approved |
| Emma Jansen | emma.jansen@gmail.com | Rejected |
| Anna Kowalski | anna.kowalski@gmail.com | Pending |

### Landlord portal
Go to `/landlord/tenants` and select your company:

| Company | Password |
|---------|----------|
| Holland2Stay | `h2s-2024` |
| Our Domain | `od-2024` |
| Vesteda | `vest-2024` |
| Greystar | `grey-2024` |

### Admin dashboard
Go to `/admin` — no login required.

---

## Credit scoring model

Applications are scored across four dimensions:

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Ability to pay | 40% | Affordability ratio (rent/income), debt-to-income ratio, employment type |
| Financial stability | 20% | Cash flow variance, liquidity buffer (savings/expenses), residency status |
| Financial discipline | 20% | Payment consistency, balance stability, spending regularity |
| Behavioral liquidity risk | 20% | Overdraft frequency, low-balance days, rejected transactions |

**Score thresholds:**

| Score | Decision | Interest rate |
|-------|----------|---------------|
| ≥ 80 | Approved | 8% p.a. |
| ≥ 65 | Approved | 10% p.a. |
| ≥ 60 | Approved | 12% p.a. |
| < 60 | Rejected | — |

---

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/register/identity` | Step 1 — identity fields |
| POST | `/api/v1/register/upload-document` | Document upload |
| POST | `/api/v1/register/connect-bank` | Simulated bank connection |
| POST | `/api/v1/register/income` | Step 2 — income & residency |
| POST | `/api/v1/register/rental` | Step 3 — rental details |
| POST | `/api/v1/score/calculate` | Run credit scoring |
| GET | `/api/v1/profile/tenant` | Tenant profile & repayment schedule |
| GET | `/api/v1/profile/decision/{id}` | Decision result |
| GET | `/api/v1/profile/landlord/{id}` | Individual guarantee lookup |
| GET | `/api/v1/profile/landlord-overview` | Company tenant overview (auth required) |
| GET | `/api/v1/admin/overview` | Admin portfolio data |
| POST | `/api/v1/landlord/auth` | Landlord login |
| POST | `/api/v1/landlord/logout` | Landlord logout |

Full interactive docs available at **http://localhost:8000/docs**

---

## Notes

- **No real banking data** — all bank statements are synthetically generated; no PSD2 or Open Banking calls are made
- **GDPR** — BSN numbers and uploaded documents are flagged in code and never included in API responses or logs
- **AFM licensing** — real money lending requires AFM authorisation; this MVP simulates the product under a partnership model assumption
- **Landlord passwords** — currently hardcoded for MVP; should be moved to environment variables before production deployment

---

## Team

| Name | Role |
|------|------|
| Jenny | Frontend (HTML, CSS, JavaScript) |
| Ping | Backend (FastAPI, Python, database) |

RSM Fintech — 2026
