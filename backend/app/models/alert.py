from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class AlertSeverity(str, enum.Enum):
    """Enum for alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, enum.Enum):
    """Enum for alert types"""
    PRICE_CHANGE = "price_change"
    NEWS_EVENT = "news_event"
    DIVIDEND_ANNOUNCEMENT = "dividend_announcement"
    EARNINGS_REPORT = "earnings_report"
    REGULATORY_CHANGE = "regulatory_change"
    MATURITY_REMINDER = "maturity_reminder"
    REBALANCE_SUGGESTION = "rebalance_suggestion"
    MARKET_VOLATILITY = "market_volatility"


class Alert(Base):
    """Alert model for notifications and actionable insights"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)  # Optional, for asset-specific alerts
    
    # Alert details
    alert_type = Column(Enum(AlertType), nullable=False, index=True)
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.INFO)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    
    # Action suggestions
    suggested_action = Column(Text)  # Recommended action for the user
    action_url = Column(String)  # Link to relevant page/resource
    
    # Status
    is_read = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)
    is_actionable = Column(Boolean, default=True)
    
    # Timestamps
    alert_date = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True))
    dismissed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="alerts")

# Made with Bob
