# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project overview
DepositEase is a rental deposit financing platform for the Dutch housing market (RSM Fintech MVP).
Tenants apply for deposit loans (€1,000–€4,000), the platform runs AI credit scoring, and the landlord receives a simulated payout notification.

## Stack
- Backend: Python / FastAPI
- Frontend: HTML + vanilla JS
- Database: SQLite
- Data: synthetic bank statement generator (no real Open Banking integration)
- Deployment: Render or Railway

## Key features to implement
1. Tenant registration + document upload form (synthetic data)
2. AI credit scoring engine (affordability ratio, DTI, cash flow variance, payment consistency)
3. Loan decision output with interest rate (8–12% based on credit score)
4. Landlord notification page (simulated payout confirmation)
5. Tenant repayment dashboard (monthly amount, remaining installments)
6. Admin backend (loan portfolio overview, overdue alerts)

## Credit scoring model
Three dimensions from the business plan:
- Ability to pay: affordability ratio = rent/income, debt-to-income ratio
- Financial stability: cash flow variance, liquidity buffer = savings/monthly expenses
- Financial discipline: payment consistency, balance stability, overdraft frequency

## Architecture constraints
- Single deployable app
- Synthetic data only — no real PSD2 or Open Banking calls
- GDPR-aware comments in data handling code
- All HTML, CSS, JS served by FastAPI

## Out of scope for MVP
- Real AFM licensing (mention partnership model in comments)
- Actual bank transfers (simulate with status updates)
- B2B landlord subscription service (Phase 2)

## Running the project
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

## Git workflow
- Two collaborators: Jenny (frontend) and Ping (backend)
- Commit after each feature with clear messages
- Never push directly to main without testing locally
