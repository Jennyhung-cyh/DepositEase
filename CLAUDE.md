# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project overview
DepositEase is a rental deposit financing platform for the Dutch housing market (RSM Fintech MVP).
Tenants apply for deposit loans, the platform runs AI credit scoring, and the landlord receives a simulated payout notification.

## Stack
- Backend: Python / FastAPI
- Frontend: HTML + vanilla JS
- Database: SQLite
- Data: synthetic bank statement generator (no real Open Banking integration)
- Deployment: Render or Railway (not yet deployed — runs locally for MVP)

## Implemented features
1. Tenant registration + document upload form (synthetic data)
2. AI credit scoring engine (affordability ratio, DTI, cash flow variance, payment consistency, behavioral liquidity risk)
3. Loan decision output with interest rate (8–12% based on credit score)
4. Landlord notification page with simulated payout confirmation
5. Tenant repayment dashboard (monthly amount, remaining installments, payment schedule)
6. Admin backend (loan portfolio overview, overdue alerts)
7. Landlord company authentication (per-company password, 8-hour session token)
8. Landlord tenant overview portal (filtered by company, with payout notifications)

## Pages
| URL | Description | Who |
|-----|-------------|-----|
| `/` | Home page | Public |
| `/apply` | Tenant registration (3-step flow) | Tenant |
| `/decision?application_id=` | Loan decision result | Tenant |
| `/tenant` | Application status + repayment dashboard | Tenant |
| `/landlord` | Look up individual guarantee by reference | Landlord |
| `/landlord/tenants` | Company login + all tenants overview | Landlord |
| `/admin` | Full loan portfolio + overdue alerts | Internal |

## Credit scoring model
Four dimensions:
- **Ability to pay (40%)**: affordability ratio = rent/income, debt-to-income ratio, employment bonus
- **Financial stability (20%)**: cash flow variance, liquidity buffer = savings/monthly expenses, residency bonus
- **Financial discipline (20%)**: payment consistency, balance stability, spending regularity
- **Behavioral liquidity risk (20%)**: overdraft frequency, low-balance days, rejected transactions

Score thresholds:
- ≥ 80 → Approved at 8%
- ≥ 65 → Approved at 10%
- ≥ 60 → Approved at 12%
- < 60 → Rejected

## Architecture constraints
- Single deployable app
- Synthetic data only — no real PSD2 or Open Banking calls
- GDPR-aware comments in data handling code
- All HTML, CSS, JS served by FastAPI

## Out of scope for MVP
- Real AFM licensing (mention partnership model in comments)
- Actual bank transfers (simulate with status updates)
- B2B landlord subscription service (Phase 2)
- Admin page authentication
- Custom landlord ("Others") access to tenant portal

## Running the project
```bash
pip install -r requirements.txt
python3 seed.py          # populate demo data (safe to re-run — skips existing records)
uvicorn main:app --reload
```

## Demo accounts
| Role | URL | Credentials |
|------|-----|-------------|
| Tenant | `/tenant` | `jan.devries@gmail.com` |
| Holland2Stay | `/landlord/tenants` | password: `h2s-2024` |
| Our Domain | `/landlord/tenants` | password: `od-2024` |
| Vesteda | `/landlord/tenants` | password: `vest-2024` |
| Greystar | `/landlord/tenants` | password: `grey-2024` |
| Admin | `/admin` | no login required |

## Git workflow
- Two collaborators: Ping (frontend) and Jenny (backend)
- Commit after each feature with clear messages
- Never push directly to main without testing locally
