"""
Schemas for price refresh progress tracking
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AssetPriceProgress(BaseModel):
    """Progress for a single asset price update"""
    asset_id: int
    asset_name: str
    asset_symbol: Optional[str] = None
    asset_type: str
    status: str  # "pending", "processing", "completed", "error"
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class PriceRefreshProgress(BaseModel):
    """Overall progress for price refresh"""
    session_id: str
    user_id: int
    total_assets: int
    updated_assets: int
    failed_assets: int
    status: str  # "running", "completed", "failed"
    assets: list[AssetPriceProgress]
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_detail: Optional[str] = None
