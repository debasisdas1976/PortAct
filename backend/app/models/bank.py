from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class BankMaster(Base):
    """Master table for banks"""
    __tablename__ = "banks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    display_label = Column(String(100), nullable=False)
    bank_type = Column(String(20), default="commercial")  # "commercial", "payment", "small_finance", "post_office"
    website = Column(String(200))  # Website URL for favicon
    has_parser = Column(Boolean, default=False)  # Whether a dedicated statement parser exists
    supported_formats = Column(String(500))  # JSON per account-type config or comma-separated legacy
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
