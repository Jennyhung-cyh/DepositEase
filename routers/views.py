from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import Tenant, Application
from routers.landlord_auth import verify_token


def _repayment_schedule(app: Application) -> Optional[dict]:
    if app.status != "approved" or not all([app.monthly_repayment, app.repayment_months, app.created_at]):
        return None

    months_elapsed = max(0, (datetime.utcnow() - app.created_at).days // 30)
    months_paid    = min(months_elapsed, app.repayment_months)
    months_remaining = app.repayment_months - months_paid

    schedule = []
    for i in range(app.repayment_months):
        payment_date = app.created_at + timedelta(days=30 * (i + 1))
        schedule.append({
            "month":  i + 1,
            "date":   payment_date.isoformat(),
            "amount": app.monthly_repayment,
            "paid":   i < months_paid,
        })

    return {
        "months_paid":       months_paid,
        "months_total":      app.repayment_months,
        "months_remaining":  months_remaining,
        "amount_paid":       round(months_paid * app.monthly_repayment, 2),
        "remaining_balance": round(months_remaining * app.monthly_repayment, 2),
        "schedule":          schedule,
    }

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


@router.get("/tenant")
def get_tenant_profile(email: str = Query(...), db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.email == email.strip().lower()).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="No application found for this email address.")

    app = (
        db.query(Application)
        .filter(Application.tenant_id == tenant.id)
        .order_by(Application.created_at.desc())
        .first()
    )
    if not app:
        raise HTTPException(status_code=404, detail="No application found.")

    return {
        "full_name": tenant.full_name,
        "email": tenant.email,
        "reference": f"DE-{app.id:06d}",
        "application_id": app.id,
        "status": app.status,
        "rental_address": app.rental_address,
        "rental_postal_code": app.rental_postal_code,
        "deposit_amount": app.amount_requested,
        "monthly_rent": app.monthly_rent,
        "contract_term_months": app.contract_term_months,
        "repayment_months": app.repayment_months,
        "monthly_repayment": app.monthly_repayment,
        "interest_rate": app.interest_rate,
        "credit_score": app.credit_score,
        "decision_reason": app.decision_reason,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "repayment_schedule": _repayment_schedule(app),
    }


@router.get("/decision/{application_id}")
def get_decision(application_id: int, db: Session = Depends(get_db)):
    app = db.get(Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")

    tenant = db.get(Tenant, app.tenant_id)

    return {
        "reference": f"DE-{app.id:06d}",
        "status": app.status,
        "full_name": tenant.full_name if tenant else "Applicant",
        "deposit_amount": app.amount_requested,
        "monthly_rent": app.monthly_rent,
        "credit_score": app.credit_score,
        "interest_rate": app.interest_rate,
        "monthly_repayment": app.monthly_repayment,
        "repayment_months": app.repayment_months,
        "decision_reason": app.decision_reason,
        "rental_address": app.rental_address,
        "rental_postal_code": app.rental_postal_code,
        "created_at": app.created_at.isoformat() if app.created_at else None,
    }


@router.get("/landlord-overview")
def get_landlord_overview(
    landlord: str = Query(...),
    x_landlord_token: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    verified = verify_token(x_landlord_token or "")
    if not verified or verified != landlord:
        raise HTTPException(status_code=401, detail="Unauthorised. Please log in again.")
    applications = (
        db.query(Application)
        .filter(Application.landlord_name == landlord)
        .order_by(Application.created_at.desc())
        .all()
    )

    approved = [a for a in applications if a.status == "approved"]
    total_deposit = sum(a.amount_requested or 0 for a in approved)

    rows = []
    for app in applications:
        tenant = db.get(Tenant, app.tenant_id)
        first_name = tenant.full_name.split()[0] if tenant and tenant.full_name else "Tenant"
        rows.append({
            "reference": f"DE-{app.id:06d}",
            "application_id": app.id,
            "tenant_first_name": first_name,
            "status": app.status,
            "rental_address": app.rental_address,
            "rental_postal_code": app.rental_postal_code,
            "deposit_amount": app.amount_requested,
            "monthly_repayment": app.monthly_repayment,
            "repayment_months": app.repayment_months,
            "payout_date": app.created_at.isoformat() if app.status == "approved" and app.created_at else None,
            "created_at": app.created_at.isoformat() if app.created_at else None,
        })

    return {
        "landlord": landlord,
        "stats": {
            "total": len(applications),
            "approved": len(approved),
            "pending": len([a for a in applications if a.status in ("pending", "draft")]),
            "total_deposit_value": round(total_deposit, 2),
        },
        "tenants": rows,
    }


@router.get("/landlord/{application_id}")
def get_landlord_profile(application_id: int, db: Session = Depends(get_db)):
    app = db.get(Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")

    tenant = db.get(Tenant, app.tenant_id)
    first_name = tenant.full_name.split()[0] if tenant and tenant.full_name else "Tenant"

    return {
        "reference": f"DE-{app.id:06d}",
        "status": app.status,
        "tenant_first_name": first_name,
        "rental_address": app.rental_address,
        "rental_postal_code": app.rental_postal_code,
        "deposit_amount": app.amount_requested,
        "repayment_months": app.repayment_months,
        "monthly_repayment": app.monthly_repayment,
        "created_at": app.created_at.isoformat() if app.created_at else None,
    }
