"""
Schemas for news fetching progress tracking
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AssetProgress(BaseModel):
    """Progress for a single asset"""
    asset_id: int
    asset_name: str
    asset_symbol: Optional[str] = None
    status: str  # "pending", "processing", "completed", "error"
    alert_created: bool = False
    alert_message: Optional[str] = None
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class NewsProgress(BaseModel):
    """Overall progress for news fetching"""
    session_id: str
    user_id: int
    total_assets: int
    processed_assets: int
    alerts_created: int
    status: str  # "running", "completed", "failed"
    assets: list[AssetProgress]
    started_at: datetime
    completed_at: Optional[datetime] = None

# Made with Bob
