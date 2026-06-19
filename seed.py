"""Creates a demo tenant with an approved application for testing the profile views."""
import json
from datetime import date

from database import SessionLocal, engine, Base
import models

Base.metadata.create_all(bind=engine)
db = SessionLocal()

EMAIL = "demo@depositease.nl"

existing = db.query(models.Tenant).filter(models.Tenant.email == EMAIL).first()
if existing:
    app = db.query(models.Application).filter(models.Application.tenant_id == existing.id).first()
    print(f"Already exists → email: {EMAIL}  |  ref: DE-{app.id:06d}")
    db.close()
    exit()

tenant = models.Tenant(
    full_name="Jan de Vries",
    email=EMAIL,
    date_of_birth=date(1990, 4, 15),
    id_type="bsn",
    bsn="123456789",
    employment_status="employed_full_time",
    contract_type="permanent",
    residency_status="dutch_national",
    bank_connected=True,
)
db.add(tenant)
db.commit()
db.refresh(tenant)

db.add(models.SyntheticBankStatement(
    tenant_id=tenant.id,
    monthly_income=3200.00,
    monthly_expenses=1800.00,
    savings_balance=5500.00,
    overdraft_count=0,
    months_of_data=6,
    monthly_debt_payments=150.00,
    late_payments=0,
    total_payment_obligations=18,
    overdraft_days=0,
    low_balance_days=2,
    rejected_transactions=0,
    total_transactions=142,
    raw_json=json.dumps([
        {"month": i + 1, "income": 3200, "expenses": 1800,
         "discretionary": {"restaurant": 180, "luxury": 50,
                           "irregular_transfers": 100, "cash_withdrawals": 80},
         "avg_daily_balance": 2100, "std_daily_balance": 180, "low_balance_days": 0}
        for i in range(6)
    ]),
))

app = models.Application(
    tenant_id=tenant.id,
    status="approved",
    rental_address="Kalverstraat 92, Amsterdam",
    rental_postal_code="1012 PH",
    contract_term_months=12,
    amount_requested=2500.00,
    repayment_months=12,
    credit_score=84.5,
    affordability_ratio=0.281,
    dti_ratio=0.047,
    payment_consistency=1.0,
    interest_rate=0.08,
    monthly_repayment=217.47,
    decision_reason="Strong credit profile.",
)
db.add(app)
db.commit()
db.refresh(app)

print(f"Demo tenant created")
print(f"  Email : {EMAIL}")
print(f"  Ref   : DE-{app.id:06d}")
db.close()
