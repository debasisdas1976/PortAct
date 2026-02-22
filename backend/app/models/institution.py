from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class InstitutionMaster(Base):
    """Generic master table for institutions (NPS fund managers, insurance providers, NPS CRAs, etc.)"""
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, index=True)
    display_label = Column(String(100), nullable=False)
    category = Column(String(30), nullable=False, index=True)  # "nps_fund_manager", "insurance_provider", "nps_cra"
    website = Column(String(200))
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
