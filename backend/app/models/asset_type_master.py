from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class AssetTypeMaster(Base):
    """Master table for asset types with category grouping"""
    __tablename__ = "asset_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    display_label = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    allowed_conversions = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
