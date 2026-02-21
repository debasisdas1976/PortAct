from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class BrokerMaster(Base):
    """Master table for stock brokers"""
    __tablename__ = "brokers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    display_label = Column(String(100), nullable=False)
    broker_type = Column(String(20), default="discount")  # "full_service", "discount", "international"
    supported_markets = Column(String(20), default="domestic")  # "domestic", "international", "both"
    website = Column(String(200))  # Website URL for favicon
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
