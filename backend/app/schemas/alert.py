from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.alert import AlertSeverity, AlertType


class AlertBase(BaseModel):
    """Base alert schema"""
    alert_type: AlertType
    severity: AlertSeverity = AlertSeverity.INFO
    title: str
    message: str
    suggested_action: Optional[str] = None
    action_url: Optional[str] = None


class AlertCreate(AlertBase):
    """Schema for creating an alert"""
    asset_id: Optional[int] = None


class AlertUpdate(BaseModel):
    """Schema for updating an alert"""
    is_read: Optional[bool] = None
    is_dismissed: Optional[bool] = None


class AlertInDB(AlertBase):
    """Schema for alert in database"""
    id: int
    user_id: int
    asset_id: Optional[int] = None
    is_read: bool
    is_dismissed: bool
    is_actionable: bool
    alert_date: datetime
    read_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class Alert(AlertInDB):
    """Schema for alert response"""
    pass


class AlertWithAsset(Alert):
    """Schema for alert with asset details"""
    asset_name: Optional[str] = None
    asset_type: Optional[str] = None

# Made with Bob
