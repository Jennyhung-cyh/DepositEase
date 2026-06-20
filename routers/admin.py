from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Tenant, Application

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _is_overdue(app: Application) -> bool:
    if app.status != "approved" or not app.repayment_months or not app.created_at:
        return False
    end_date = app.created_at + timedelta(days=app.repayment_months * 30)
    return end_date < datetime.utcnow()


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    applications = db.query(Application).order_by(Application.created_at.desc()).all()

    approved = [a for a in applications if a.status == "approved"]
    rejected = [a for a in applications if a.status == "rejected"]
    pending  = [a for a in applications if a.status in ("pending", "draft")]

    total_portfolio = sum(a.amount_requested or 0 for a in approved)
    scores = [a.credit_score for a in approved if a.credit_score is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    rows = []
    overdue_count = 0
    for app in applications:
        tenant = db.get(Tenant, app.tenant_id)
        overdue = _is_overdue(app)
        if overdue:
            overdue_count += 1
        rows.append({
            "reference": f"DE-{app.id:06d}",
            "application_id": app.id,
            "tenant_name": tenant.full_name if tenant else "—",
            "email": tenant.email if tenant else "—",
            "status": app.status,
            "deposit_amount": app.amount_requested,
            "credit_score": app.credit_score,
            "interest_rate": app.interest_rate,
            "monthly_repayment": app.monthly_repayment,
            "repayment_months": app.repayment_months,
            "is_overdue": overdue,
            "created_at": app.created_at.isoformat() if app.created_at else None,
        })

    return {
        "stats": {
            "total": len(applications),
            "approved": len(approved),
            "rejected": len(rejected),
            "pending": len(pending),
            "total_portfolio_value": round(total_portfolio, 2),
            "avg_credit_score": avg_score,
        },
        "overdue_count": overdue_count,
        "applications": rows,
    }
