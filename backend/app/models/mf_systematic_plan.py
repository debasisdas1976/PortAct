from sqlalchemy import Column, Integer, Float, Date, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.enums import LowerEnum, SystematicPlanType, SystematicFrequency


class MFSystematicPlan(Base):
    """Stores SIP / STP / SWP schedules for mutual fund assets.

    The scheduler checks active plans daily and creates the appropriate
    transaction(s) when a plan's next execution date matches today.
    """
    __tablename__ = "mf_systematic_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    plan_type = Column(LowerEnum(SystematicPlanType), nullable=False, index=True)

    # Source asset (all plan types)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)

    # Target asset (STP only — the fund receiving the transfer)
    target_asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)

    amount = Column(Float, nullable=False)  # INR per installment
    frequency = Column(LowerEnum(SystematicFrequency), nullable=False)

    # For MONTHLY: day of month (1-28). For WEEKLY: day of week (0=Mon .. 6=Sun).
    # For DAILY / FORTNIGHTLY: ignored (FORTNIGHTLY uses start_date offset).
    execution_day = Column(Integer, nullable=True)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # null = perpetual
    is_active = Column(Boolean, default=True, nullable=False)

    last_executed_date = Column(Date, nullable=True)
    notes = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User")
    asset = relationship("Asset", foreign_keys=[asset_id])
    target_asset = relationship("Asset", foreign_keys=[target_asset_id])
