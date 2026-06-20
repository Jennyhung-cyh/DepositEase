import uuid
import json
import random
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Tenant, Document, Application, SyntheticBankStatement

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_DOC_TYPES = ALLOWED_IMAGE_TYPES | {"application/pdf"}

router = APIRouter(prefix="/api/v1/register", tags=["registration"])

EMPLOYMENT_STATUSES = ("employed_full_time", "employed_part_time", "self_employed", "student", "unemployed")
CONTRACT_TYPES = ("permanent", "fixed_term", "zero_hours")
SELF_EMPLOYED_DURATIONS = ("lt_1_year", "1_2_years", "gt_2_years")
RESIDENCY_STATUSES = ("dutch_national", "eu_citizen", "non_eu_permit", "recently_arrived")
PERMIT_TYPES = ("work_permit", "study_permit", "other")


def _save_upload(file: UploadFile, subdir: str) -> tuple[str, str]:
    dest_dir = UPLOAD_DIR / subdir
    dest_dir.mkdir(exist_ok=True)
    ext = Path(file.filename).suffix or ".bin"
    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest = dest_dir / stored_name
    content = file.file.read()
    dest.write_bytes(content)
    return file.filename, stored_name


@router.post("/identity")
def submit_identity(
    full_name: str = Form(...),
    email: str = Form(...),
    date_of_birth: str = Form(...),
    id_type: str = Form(...),       # "bsn" | "passport"
    id_number: str = Form(...),
    db: Session = Depends(get_db),
):
    """Step 1a — persist identity fields, return tenant_id for subsequent uploads."""
    existing = db.query(Tenant).filter(Tenant.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    try:
        dob = date.fromisoformat(date_of_birth)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format. Use YYYY-MM-DD.")

    if id_type not in ("bsn", "passport"):
        raise HTTPException(status_code=422, detail="id_type must be 'bsn' or 'passport'.")

    tenant = Tenant(
        full_name=full_name.strip(),
        email=email.strip().lower(),
        date_of_birth=dob,
        id_type=id_type,
        bsn=id_number.strip() if id_type == "bsn" else None,
        passport_number=id_number.strip() if id_type == "passport" else None,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    app = Application(tenant_id=tenant.id, status="draft")
    db.add(app)
    db.commit()
    db.refresh(app)

    return {"tenant_id": tenant.id, "application_id": app.id}


DOC_TYPES = ("id_document", "selfie", "payslip", "tax_return", "duo_letter", "rental_contract")
DOC_TYPES_ALLOWING_PDF = ("payslip", "tax_return", "duo_letter", "rental_contract")


@router.post("/upload-document")
def upload_document(
    tenant_id: int = Form(...),
    doc_type: str = Form(...),   # see DOC_TYPES
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload KYC / income documents. GDPR: files stored server-side only."""
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    if doc_type not in DOC_TYPES:
        raise HTTPException(status_code=422, detail="Invalid doc_type.")

    allowed = ALLOWED_DOC_TYPES if doc_type in DOC_TYPES_ALLOWING_PDF else ALLOWED_IMAGE_TYPES
    if file.content_type not in allowed:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}")

    original, stored = _save_upload(file, doc_type)
    doc = Document(
        tenant_id=tenant_id,
        doc_type=doc_type,
        original_filename=original,
        stored_filename=stored,
    )
    db.add(doc)
    db.commit()
    return {"status": "uploaded", "doc_type": doc_type}


@router.post("/connect-bank")
def connect_bank(
    tenant_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """Simulate PSD2 bank connection — generates synthetic statement data.
    Real Open Banking integration is out of scope for MVP (AFM partnership model)."""
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    monthly_income = round(random.uniform(1_800, 4_500), 2)
    monthly_expenses = round(monthly_income * random.uniform(0.45, 0.80), 2)
    savings_balance = round(random.uniform(500, 8_000), 2)
    overdraft_count = random.randint(0, 3)
    monthly_debt_payments = round(monthly_income * random.uniform(0.0, 0.25), 2)

    # Payment consistency
    total_payment_obligations = random.randint(12, 30)
    late_payments = random.choices([0, 1, 2, 3], weights=[60, 25, 10, 5])[0]

    # Behavioral liquidity risk (aggregated over 6 months)
    overdraft_days = random.choices(range(0, 16), weights=[40] + [6] * 10 + [4] * 5)[0]
    total_transactions = random.randint(80, 200)
    rejected_transactions = random.choices([0, 1, 2, 3, 4], weights=[55, 25, 12, 5, 3])[0]

    months = []
    total_low_balance_days = 0
    for i in range(6):
        month_income = round(monthly_income * random.uniform(0.92, 1.08), 2)
        month_expenses = round(monthly_expenses * random.uniform(0.88, 1.12), 2)

        disc_total = month_expenses * random.uniform(0.25, 0.45)
        discretionary = {
            "restaurant": round(disc_total * random.uniform(0.30, 0.50), 2),
            "luxury": round(disc_total * random.uniform(0.05, 0.20), 2),
            "irregular_transfers": round(disc_total * random.uniform(0.10, 0.30), 2),
            "cash_withdrawals": round(disc_total * random.uniform(0.05, 0.20), 2),
        }

        avg_daily_balance = round(savings_balance * random.uniform(0.6, 1.4), 2)
        std_daily_balance = round(avg_daily_balance * random.uniform(0.10, 0.40), 2)
        month_low_days = random.choices(range(0, 8), weights=[50, 20, 12, 8, 5, 2, 2, 1])[0]
        total_low_balance_days += month_low_days

        months.append({
            "month": i + 1,
            "income": month_income,
            "expenses": month_expenses,
            "discretionary": discretionary,
            "avg_daily_balance": avg_daily_balance,
            "std_daily_balance": std_daily_balance,
            "low_balance_days": month_low_days,
        })

    stmt = SyntheticBankStatement(
        tenant_id=tenant_id,
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        savings_balance=savings_balance,
        overdraft_count=overdraft_count,
        months_of_data=6,
        monthly_debt_payments=monthly_debt_payments,
        late_payments=late_payments,
        total_payment_obligations=total_payment_obligations,
        overdraft_days=overdraft_days,
        low_balance_days=total_low_balance_days,
        rejected_transactions=rejected_transactions,
        total_transactions=total_transactions,
        raw_json=json.dumps(months),
    )
    db.add(stmt)
    tenant.bank_connected = True
    db.commit()

    return {
        "status": "connected",
        "bank_name": "ING Bank (simulated)",
        "months_retrieved": 6,
        "monthly_income_estimate": monthly_income,
    }


@router.post("/income")
def submit_income(
    tenant_id: int = Form(...),
    application_id: int = Form(...),
    employment_status: str = Form(...),                 # see EMPLOYMENT_STATUSES
    contract_type: Optional[str] = Form(None),             # required if employed full/part-time
    self_employed_duration: Optional[str] = Form(None),    # required if self-employed
    receives_duo: Optional[str] = Form(None),              # "yes" | "no" — required if student
    has_parttime_income: Optional[str] = Form(None),       # "yes" | "no" — required if student
    residency_status: str = Form(...),                  # see RESIDENCY_STATUSES
    permit_type: Optional[str] = Form(None),               # required if non-EU permit
    permit_expiry_date: Optional[str] = Form(None),        # required if non-EU permit, "YYYY-MM-DD"
    db: Session = Depends(get_db),
):
    """Step 2 — record employment/residency profile.
    Requested deposit amount is collected on the loan application step (not here)."""
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    if employment_status not in EMPLOYMENT_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid employment_status.")
    if residency_status not in RESIDENCY_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid residency_status.")

    # Conditional follow-ups — validate when applicable, discard otherwise so
    # stale answers from a previously selected branch are never persisted.
    if employment_status in ("employed_full_time", "employed_part_time"):
        if contract_type not in CONTRACT_TYPES:
            raise HTTPException(status_code=422, detail="Please select your contract type.")
    else:
        contract_type = None

    if employment_status == "self_employed":
        if self_employed_duration not in SELF_EMPLOYED_DURATIONS:
            raise HTTPException(status_code=422, detail="Please select how long you've been self-employed.")
    else:
        self_employed_duration = None

    duo_bool = parttime_bool = None
    if employment_status == "student":
        if receives_duo not in ("yes", "no") or has_parttime_income not in ("yes", "no"):
            raise HTTPException(status_code=422, detail="Please answer the student income questions.")
        duo_bool = receives_duo == "yes"
        parttime_bool = has_parttime_income == "yes"

    permit_expiry = None
    if residency_status == "non_eu_permit":
        if permit_type not in PERMIT_TYPES:
            raise HTTPException(status_code=422, detail="Please select your permit type.")
        try:
            permit_expiry = date.fromisoformat(permit_expiry_date)
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="Enter a valid permit expiry date (YYYY-MM-DD).")
    else:
        permit_type = None

    tenant.employment_status = employment_status
    tenant.contract_type = contract_type
    tenant.self_employed_duration = self_employed_duration
    tenant.receives_duo = duo_bool
    tenant.has_parttime_income = parttime_bool
    tenant.residency_status = residency_status
    tenant.permit_type = permit_type
    tenant.permit_expiry_date = permit_expiry

    app = db.get(Application, application_id)
    if not app or app.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Application not found.")

    app.status = "pending"
    db.commit()

    return {"status": "pending", "application_id": app.id, "next": "/rental"}


@router.post("/rental")
def submit_rental(
    tenant_id: int = Form(...),
    application_id: int = Form(...),
    rental_address: str = Form(...),
    rental_postal_code: str = Form(...),
    deposit_amount: float = Form(...),
    repayment_months: int = Form(...),
    contract_term_months: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    """Step 3 — rental property details, deposit amount, and repayment term selection."""
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    app = db.get(Application, application_id)
    if not app or app.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Application not found.")

    if deposit_amount <= 0:
        raise HTTPException(status_code=422, detail="Deposit amount must be greater than €0.")

    if repayment_months <= 0 or repayment_months > 120:
        raise HTTPException(status_code=422, detail="Repayment term must be between 1 and 120 months.")

    min_months = contract_term_months if contract_term_months else 12
    if repayment_months < min_months:
        raise HTTPException(
            status_code=422,
            detail=f"Repayment term must be at least {min_months} months to match the contract term.",
        )

    app.rental_address = rental_address.strip()
    app.rental_postal_code = rental_postal_code.strip().upper()
    app.contract_term_months = contract_term_months
    app.amount_requested = deposit_amount
    app.repayment_months = repayment_months
    app.status = "pending"
    db.commit()

    return {"status": "pending", "application_id": app.id, "next": "/score"}
