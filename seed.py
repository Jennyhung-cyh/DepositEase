"""Seed demo data for DepositEase MVP presentations."""
import json
from datetime import date, datetime, timedelta

from database import SessionLocal, engine, Base
import models

Base.metadata.create_all(bind=engine)
db = SessionLocal()

TENANTS = [
    # (full_name, email, dob, employment, contract_type, residency, landlord, deposit, repayment_months, credit_score, interest_rate, status, months_ago, monthly_rent)
    ("Jan de Vries",      "jan.devries@gmail.com",     date(1990, 4, 15),  "employed_full_time", "permanent",  "dutch_national", "Holland2Stay", 2500, 12, 84.5, 0.08, "approved",  6, 1250),
    ("Sophie Bakker",     "sophie.bakker@gmail.com",   date(1995, 7, 22),  "employed_full_time", "permanent",  "dutch_national", "Holland2Stay", 1800, 12, 76.2, 0.10, "approved",  4,  900),
    ("Lucas Müller",      "lucas.muller@gmail.com",    date(1988, 11, 3),  "employed_full_time", "fixed_term", "eu_citizen",     "Holland2Stay", 3200, 18, 68.0, 0.10, "approved",  2, 1600),
    ("Emma Jansen",       "emma.jansen@outlook.com",   date(2000, 2, 18),  "student",            None,         "dutch_national", "Holland2Stay", 1200, 6,  54.0, None, "rejected",  1,  600),
    ("Pieter Smit",       "pieter.smit@gmail.com",     date(1992, 9, 30),  "employed_part_time", "fixed_term", "dutch_national", "Our Domain",   2000, 12, 79.1, 0.08, "approved",  3, 1000),
    ("Aisha Okonkwo",     "aisha.okonkwo@gmail.com",   date(1997, 5, 12),  "employed_full_time", "permanent",  "non_eu_permit",  "Our Domain",   2800, 12, 81.3, 0.08, "approved",  5, 1400),
    ("Thomas Dubois",     "thomas.dubois@gmail.com",   date(1985, 3, 27),  "self_employed",      None,         "eu_citizen",     "Our Domain",   3500, 24, 71.5, 0.10, "approved",  1, 1750),
    ("Nora van Berg",     "nora.vanberg@gmail.com",    date(1993, 8, 14),  "employed_full_time", "permanent",  "dutch_national", "Vesteda",      2200, 12, 88.0, 0.08, "approved",  7, 1100),
    ("Kevin Tran",        "kevin.tran@gmail.com",      date(1999, 1, 5),   "student",            None,         "non_eu_permit",  "Vesteda",      1500, 12, 62.0, 0.12, "approved",  2,  750),
    ("Maria Santos",      "maria.santos@gmail.com",    date(1991, 6, 20),  "employed_full_time", "permanent",  "eu_citizen",     "Greystar",     3000, 18, 83.7, 0.08, "approved",  3, 1500),
    ("David Kim",         "david.kim@gmail.com",       date(1987, 12, 9),  "employed_full_time", "permanent",  "non_eu_permit",  "Greystar",     2600, 12, 45.0, None, "rejected",  1, 1300),
    ("Anna Kowalski",     "anna.kowalski@gmail.com",   date(1996, 4, 8),   "employed_full_time", "permanent",  "eu_citizen",     "Greystar",     1900, 12, None, None, "pending",   0,  950),
    ("Bart Visser",       "bart.visser@gmail.com",     date(2001, 3, 14),  "student",            None,         "dutch_national", "Holland2Stay", 1000, 6,  38.0, None, "rejected",  2,  500),
    ("Yuki Tanaka",       "yuki.tanaka@gmail.com",     date(1998, 9, 25),  "unemployed",         None,         "non_eu_permit",  "Our Domain",   2200, 12, 41.5, None, "rejected",  3, 1100),
    ("Radu Popescu",      "radu.popescu@gmail.com",    date(1994, 7, 1),   "self_employed",      None,         "eu_citizen",     "Vesteda",      3000, 18, 44.0, None, "rejected",  1, 1500),
    ("Fatima El Idrissi", "fatima.elidrissi@gmail.com",date(2000, 11, 17), "student",            None,         "non_eu_permit",  "Greystar",     1600, 12, 35.5, None, "rejected",  4,  800),
]

created = 0
skipped = 0

for (full_name, email, dob, emp_status, contract_type, residency,
     landlord, deposit, repay_months, credit_score, interest_rate, status, months_ago, monthly_rent) in TENANTS:

    if db.query(models.Tenant).filter(models.Tenant.email == email).first():
        skipped += 1
        continue

    tenant = models.Tenant(
        full_name=full_name,
        email=email,
        date_of_birth=dob,
        id_type="bsn",
        bsn="000000000",
        employment_status=emp_status,
        contract_type=contract_type,
        residency_status=residency,
        bank_connected=True,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    monthly_income  = 3000.0
    monthly_expenses = 1600.0
    savings_balance  = 4000.0

    db.add(models.SyntheticBankStatement(
        tenant_id=tenant.id,
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        savings_balance=savings_balance,
        overdraft_count=0,
        months_of_data=6,
        monthly_debt_payments=100.0,
        late_payments=0,
        total_payment_obligations=18,
        overdraft_days=0,
        low_balance_days=1,
        rejected_transactions=0,
        total_transactions=130,
        raw_json=json.dumps([
            {"month": i + 1, "income": monthly_income, "expenses": monthly_expenses,
             "discretionary": {"restaurant": 150, "luxury": 40, "irregular_transfers": 80, "cash_withdrawals": 60},
             "avg_daily_balance": 2000, "std_daily_balance": 160, "low_balance_days": 0}
            for i in range(6)
        ]),
    ))

    created_at = datetime.utcnow() - timedelta(days=months_ago * 30)

    monthly_repayment = None
    if status == "approved" and interest_rate:
        r = interest_rate / 12
        monthly_repayment = round(deposit * r * (1 + r) ** repay_months / ((1 + r) ** repay_months - 1), 2)

    app = models.Application(
        tenant_id=tenant.id,
        status=status,
        rental_address=f"Voorbeeldstraat {10 + created}, Amsterdam",
        rental_postal_code="1012 AB",
        contract_term_months=repay_months,
        amount_requested=float(deposit),
        monthly_rent=float(monthly_rent),
        repayment_months=repay_months if status == "approved" else None,
        credit_score=credit_score,
        affordability_ratio=round(800 / monthly_income, 3),
        dti_ratio=round(100 / monthly_income, 3),
        payment_consistency=1.0,
        interest_rate=interest_rate,
        monthly_repayment=monthly_repayment,
        landlord_name=landlord,
        decision_reason=(
            "Strong credit profile." if credit_score and credit_score >= 80
            else "Good credit profile with moderate risk." if credit_score and credit_score >= 65
            else "Acceptable credit profile. Higher interest rate applies." if credit_score and credit_score >= 60
            else "Credit score below minimum threshold." if status == "rejected"
            else None
        ),
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(app)
    db.commit()
    created += 1

print(f"Seeded {created} tenants ({skipped} already existed).")
db.close()
