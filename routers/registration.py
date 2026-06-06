import uuid
import json
import random
from datetime import date, datetime
from pathlib import Path

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


@router.post("/upload-document")
def upload_document(
    tenant_id: int = Form(...),
    doc_type: str = Form(...),   # "id_document" | "selfie" | "payslip"
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload KYC documents (ID, selfie, payslip). GDPR: files stored server-side only."""
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    if doc_type not in ("id_document", "selfie", "payslip"):
        raise HTTPException(status_code=422, detail="Invalid doc_type.")

    allowed = ALLOWED_DOC_TYPES if doc_type == "payslip" else ALLOWED_IMAGE_TYPES
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

    months = []
    for i in range(6):
        months.append({
            "month": i + 1,
            "income": round(monthly_income * random.uniform(0.92, 1.08), 2),
            "expenses": round(monthly_expenses * random.uniform(0.88, 1.12), 2),
        })

    stmt = SyntheticBankStatement(
        tenant_id=tenant_id,
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        savings_balance=savings_balance,
        overdraft_count=overdraft_count,
        months_of_data=6,
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
    employment_status: str = Form(...),   # "student" | "employed" | "expat"
    amount_requested: float = Form(...),
    db: Session = Depends(get_db),
):
    """Step 2 — record employment status and requested deposit amount."""
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    if employment_status not in ("student", "employed", "expat"):
        raise HTTPException(status_code=422, detail="Invalid employment_status.")

    if not (1_000 <= amount_requested <= 4_000):
        raise HTTPException(status_code=422, detail="Deposit amount must be €1,000–€4,000.")

    tenant.employment_status = employment_status

    app = db.get(Application, application_id)
    if not app or app.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Application not found.")

    app.amount_requested = amount_requested
    app.status = "pending"
    db.commit()

    return {"status": "pending", "application_id": app.id, "next": "/score"}
