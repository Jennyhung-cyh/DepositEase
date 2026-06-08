import json
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session

from database import get_db
from models import Tenant, Application, SyntheticBankStatement

router = APIRouter(prefix="/api/v1/score", tags=["scoring"])

OBSERVATION_DAYS = 180  # 6 months


# ── Dimension 1: Ability to Pay (35%) ────────────────────────────────────────

def _ability_to_pay(monthly_rent: float, stmt: SyntheticBankStatement,
                    employment_status: str, contract_type: Optional[str]) -> float:
    income = stmt.monthly_income
    if income <= 0:
        return 0.0

    affordability = monthly_rent / income
    dti = stmt.monthly_debt_payments / income

    if affordability <= 0.25:
        aff = 100
    elif affordability <= 0.30:
        aff = 80
    elif affordability <= 0.35:
        aff = 60
    elif affordability <= 0.40:
        aff = 40
    else:
        aff = 20

    if dti <= 0.10:
        dti_s = 100
    elif dti <= 0.20:
        dti_s = 80
    elif dti <= 0.30:
        dti_s = 60
    elif dti <= 0.40:
        dti_s = 40
    else:
        dti_s = 10

    emp_bonus = 0
    if employment_status == "employed_full_time":
        emp_bonus = 10 if contract_type == "permanent" else 5
    elif employment_status == "employed_part_time":
        emp_bonus = 5

    return min(100.0, aff * 0.5 + dti_s * 0.5 + emp_bonus)


# ── Dimension 2: Financial Stability (30%) ───────────────────────────────────

def _financial_stability(stmt: SyntheticBankStatement, months: list,
                         residency_status: Optional[str]) -> float:
    incomes = [m["income"] for m in months]
    mean_inc = sum(incomes) / len(incomes)
    std_inc = math.sqrt(sum((x - mean_inc) ** 2 for x in incomes) / len(incomes))
    cv = std_inc / mean_inc if mean_inc > 0 else 1.0

    if cv <= 0.05:
        cf = 100
    elif cv <= 0.10:
        cf = 80
    elif cv <= 0.15:
        cf = 60
    elif cv <= 0.20:
        cf = 40
    else:
        cf = 20

    liquidity = stmt.savings_balance / stmt.monthly_expenses if stmt.monthly_expenses > 0 else 0
    if liquidity >= 3.0:
        liq = 100
    elif liquidity >= 2.0:
        liq = 80
    elif liquidity >= 1.0:
        liq = 60
    elif liquidity >= 0.5:
        liq = 40
    else:
        liq = 20

    res_bonus = 0
    if residency_status == "dutch_national":
        res_bonus = 10
    elif residency_status == "eu_citizen":
        res_bonus = 5

    return min(100.0, cf * 0.5 + liq * 0.5 + res_bonus)


# ── Dimension 3: Financial Discipline (20%) ──────────────────────────────────

def _financial_discipline(stmt: SyntheticBankStatement, months: list) -> float:
    pc = (1 - stmt.late_payments / stmt.total_payment_obligations
          if stmt.total_payment_obligations > 0 else 0.0)
    pc_score = max(0.0, pc) * 100

    bs_scores = []
    for m in months:
        avg = m.get("avg_daily_balance", 0)
        std = m.get("std_daily_balance", 0)
        if avg > 0:
            bs_scores.append(max(0.0, 1 - std / avg) * 100)
    bs_score = sum(bs_scores) / len(bs_scores) if bs_scores else 0.0

    disc_totals = [sum(m.get("discretionary", {}).values()) for m in months]
    mean_disc = sum(disc_totals) / len(disc_totals) if disc_totals else 0
    std_disc = math.sqrt(
        sum((x - mean_disc) ** 2 for x in disc_totals) / len(disc_totals)
    ) if disc_totals else 0
    sr_score = max(0.0, 1 - (std_disc / mean_disc if mean_disc > 0 else 1.0)) * 100

    return pc_score * 0.40 + bs_score * 0.30 + sr_score * 0.30


# ── Dimension 4: Behavioral Liquidity Risk (15%) ─────────────────────────────

def _behavioral_risk(stmt: SyntheticBankStatement) -> float:
    overdraft_rate = stmt.overdraft_days / OBSERVATION_DAYS
    if overdraft_rate == 0:
        od = 100
    elif overdraft_rate <= 0.02:
        od = 80
    elif overdraft_rate <= 0.05:
        od = 60
    elif overdraft_rate <= 0.10:
        od = 40
    else:
        od = 10

    stress_rate = stmt.low_balance_days / OBSERVATION_DAYS
    if stress_rate == 0:
        ls = 100
    elif stress_rate <= 0.05:
        ls = 80
    elif stress_rate <= 0.10:
        ls = 60
    elif stress_rate <= 0.20:
        ls = 40
    else:
        ls = 10

    rj_rate = (stmt.rejected_transactions / stmt.total_transactions
               if stmt.total_transactions > 0 else 0.0)
    if rj_rate == 0:
        rj = 100
    elif rj_rate <= 0.01:
        rj = 80
    elif rj_rate <= 0.02:
        rj = 60
    elif rj_rate <= 0.05:
        rj = 40
    else:
        rj = 10

    return od * 0.35 + ls * 0.35 + rj * 0.30


# ── Monthly repayment (annuity formula) ──────────────────────────────────────

def _monthly_repayment(principal: float, annual_rate: float, months: int) -> float:
    r = annual_rate / 12
    return round(principal * r * (1 + r) ** months / ((1 + r) ** months - 1), 2)


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/calculate")
def calculate_score(
    tenant_id: int = Form(...),
    application_id: int = Form(...),
    monthly_rent: float = Form(...),
    amount_requested: float = Form(...),
    repayment_months: int = Form(...),  # 6 or 12
    db: Session = Depends(get_db),
):
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    app = db.get(Application, application_id)
    if not app or app.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Application not found.")

    if not tenant.bank_connected:
        raise HTTPException(status_code=400, detail="Bank account not connected.")

    if not (1_000 <= amount_requested <= 4_000):
        raise HTTPException(status_code=422, detail="Loan amount must be between €1,000 and €4,000.")

    if repayment_months not in (6, 12):
        raise HTTPException(status_code=422, detail="Repayment term must be 6 or 12 months.")

    stmt = (
        db.query(SyntheticBankStatement)
        .filter(SyntheticBankStatement.tenant_id == tenant_id)
        .order_by(SyntheticBankStatement.generated_at.desc())
        .first()
    )
    if not stmt:
        raise HTTPException(status_code=400, detail="Bank statement not found.")

    months_data = json.loads(stmt.raw_json)

    ability    = _ability_to_pay(monthly_rent, stmt, tenant.employment_status, tenant.contract_type)
    stability  = _financial_stability(stmt, months_data, tenant.residency_status)
    discipline = _financial_discipline(stmt, months_data)
    behavioral = _behavioral_risk(stmt)

    credit_score = round(
        ability    * 0.40 +
        stability  * 0.20 +
        discipline * 0.20 +
        behavioral * 0.20,
        1,
    )

    if credit_score >= 80:
        interest_rate = 0.08
        status = "approved"
        reason = "Strong credit profile."
    elif credit_score >= 65:
        interest_rate = 0.10
        status = "approved"
        reason = "Good credit profile with moderate risk."
    elif credit_score >= 60:
        interest_rate = 0.12
        status = "approved"
        reason = "Acceptable credit profile. Higher interest rate applies."
    else:
        interest_rate = None
        status = "rejected"
        reason = "Credit score below minimum threshold."

    repayment = (
        _monthly_repayment(amount_requested, interest_rate, repayment_months)
        if status == "approved" else None
    )

    app.amount_requested    = amount_requested
    app.credit_score        = credit_score
    app.affordability_ratio = round(monthly_rent / stmt.monthly_income, 3) if stmt.monthly_income else None
    app.dti_ratio           = round(stmt.monthly_debt_payments / stmt.monthly_income, 3) if stmt.monthly_income else None
    app.payment_consistency = round(1 - stmt.late_payments / stmt.total_payment_obligations, 3) if stmt.total_payment_obligations else None
    app.interest_rate       = interest_rate
    app.monthly_repayment   = repayment
    app.repayment_months    = repayment_months if status == "approved" else None
    app.decision_reason     = reason
    app.status              = status
    db.commit()

    return {
        "credit_score":      credit_score,
        "status":            status,
        "interest_rate":     interest_rate,
        "monthly_repayment": repayment,
        "repayment_months":  repayment_months if status == "approved" else None,
        "decision_reason":   reason,
        "breakdown": {
            "ability_to_pay":       round(ability, 1),
            "financial_stability":  round(stability, 1),
            "financial_discipline": round(discipline, 1),
            "behavioral_risk":      round(behavioral, 1),
        },
    }
