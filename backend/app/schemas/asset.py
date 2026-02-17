from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.asset import AssetType


class AssetBase(BaseModel):
    """Base asset schema"""
    asset_type: AssetType
    name: str = Field(..., min_length=1, max_length=200)
    symbol: Optional[str] = Field(None, max_length=200)  # Display symbol
    api_symbol: Optional[str] = Field(None, max_length=200)  # Symbol for API calls
    isin: Optional[str] = Field(None, max_length=50)  # ISIN code
    quantity: float = Field(default=0.0, ge=0)
    purchase_price: float = Field(default=0.0, ge=0)
    current_price: float = Field(default=0.0, ge=0)
    total_invested: float = Field(default=0.0, ge=0)
    details: Optional[Dict[str, Any]] = Field(default_factory=dict)
    notes: Optional[str] = None
    purchase_date: Optional[datetime] = None
    # Account information
    account_id: Optional[str] = None
    broker_name: Optional[str] = None
    account_holder_name: Optional[str] = None


class AssetCreate(AssetBase):
    """Schema for creating an asset"""
    pass


class AssetUpdate(BaseModel):
    """Schema for updating an asset"""
    asset_type: Optional[AssetType] = None
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    symbol: Optional[str] = Field(None, max_length=200)  # Display symbol
    api_symbol: Optional[str] = Field(None, max_length=200)  # Symbol for API calls
    isin: Optional[str] = Field(None, max_length=50)  # ISIN code
    quantity: Optional[float] = Field(None, ge=0)
    purchase_price: Optional[float] = Field(None, ge=0)
    current_price: Optional[float] = Field(None, ge=0)
    total_invested: Optional[float] = Field(None, ge=0)
    details: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class AssetInDB(AssetBase):
    """Schema for asset in database"""
    id: int
    user_id: int
    statement_id: Optional[int] = None
    current_value: float
    profit_loss: float
    profit_loss_percentage: float
    is_active: bool
    price_update_failed: bool = False
    last_price_update: Optional[datetime] = None
    price_update_error: Optional[str] = None
    last_updated: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class Asset(AssetInDB):
    """Schema for asset response"""
    pass


class AssetWithTransactions(Asset):
    """Schema for asset with transaction count"""
    transaction_count: int = 0


class AssetSummary(BaseModel):
    """Schema for portfolio summary"""
    total_assets: int
    total_invested: float
    total_current_value: float
    total_profit_loss: float
    total_profit_loss_percentage: float
    assets_by_type: Dict[str, int]
    
    class Config:
        from_attributes = True

# Made with Bob
