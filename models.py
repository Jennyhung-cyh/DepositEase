import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Date, DateTime,
    Float, ForeignKey, Text, Boolean,
)
from sqlalchemy.orm import relationship

from database import Base


class EmploymentStatus(str, enum.Enum):
    employed_full_time = "employed_full_time"
    employed_part_time = "employed_part_time"
    self_employed = "self_employed"
    student = "student"
    unemployed = "unemployed"


class ApplicationStatus(str, enum.Enum):
    draft = "draft"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    phone = Column(String(30), nullable=True)
    date_of_birth = Column(Date, nullable=False)

    # GDPR note: BSN is sensitive PII — stored only for KYC verification,
    # never logged or included in responses.
    id_type = Column(String(20), nullable=False)  # "bsn" | "passport"
    bsn = Column(String(9), nullable=True)
    passport_number = Column(String(30), nullable=True)

    employment_status = Column(String(20), nullable=True)
    contract_type = Column(String(20), nullable=True)        # "permanent" | "fixed_term" | "zero_hours"
    self_employed_duration = Column(String(20), nullable=True)  # "lt_1_year" | "1_2_years" | "gt_2_years"
    receives_duo = Column(Boolean, nullable=True)
    has_parttime_income = Column(Boolean, nullable=True)

    residency_status = Column(String(20), nullable=True)     # "dutch_national" | "eu_citizen" | "non_eu_permit" | "recently_arrived"
    permit_type = Column(String(20), nullable=True)          # "work_permit" | "study_permit" | "other"
    permit_expiry_date = Column(Date, nullable=True)

    bank_connected = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="tenant", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="tenant", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    # GDPR note: uploaded files contain biometric/ID data — store path only,
    # do not embed binary in DB.
    doc_type = Column(String(30), nullable=False)  # "id_document" | "selfie" | "payslip" | "tax_return" | "duo_letter"
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="documents")


class SyntheticBankStatement(Base):
    """Synthetic PSD2 data — no real Open Banking calls (out of scope for MVP)."""
    __tablename__ = "bank_statements"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    monthly_income = Column(Float, nullable=False)
    monthly_expenses = Column(Float, nullable=False)
    savings_balance = Column(Float, nullable=False)
    overdraft_count = Column(Integer, default=0)
    months_of_data = Column(Integer, default=6)

    # DTI
    monthly_debt_payments = Column(Float, default=0.0)

    # Payment consistency
    late_payments = Column(Integer, default=0)
    total_payment_obligations = Column(Integer, default=0)

    # Behavioral liquidity risk
    overdraft_days = Column(Integer, default=0)
    low_balance_days = Column(Integer, default=0)
    rejected_transactions = Column(Integer, default=0)
    total_transactions = Column(Integer, default=0)

    # raw_json: per-month income/expenses + discretionary + daily balance stats
    raw_json = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    amount_requested = Column(Float, nullable=True)
    status = Column(String(20), default=ApplicationStatus.draft)

    # Scoring outputs (populated after scoring engine runs)
    credit_score = Column(Float, nullable=True)
    affordability_ratio = Column(Float, nullable=True)
    dti_ratio = Column(Float, nullable=True)
    cash_flow_variance = Column(Float, nullable=True)
    payment_consistency = Column(Float, nullable=True)
    interest_rate = Column(Float, nullable=True)  # 8–12% based on score

    # Rental property details (collected on step 3)
    rental_address = Column(String(500), nullable=True)
    rental_postal_code = Column(String(10), nullable=True)
    contract_term_months = Column(Integer, nullable=True)  # null = not stated on contract

    # Loan terms
    monthly_repayment = Column(Float, nullable=True)
    repayment_months = Column(Integer, nullable=True)

    decision_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="applications")
