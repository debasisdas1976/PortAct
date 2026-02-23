from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CryptoAccountBase(BaseModel):
    """Base crypto account schema"""
    exchange_name: str = Field(..., min_length=1, max_length=50)
    account_id: str = Field(..., min_length=1, max_length=200)
    account_holder_name: Optional[str] = Field(None, max_length=200)
    wallet_address: Optional[str] = Field(None, max_length=200)
    cash_balance_usd: float = Field(default=0.0)
    total_value_usd: float = Field(default=0.0)
    is_active: bool = Field(default=True)
    is_primary: bool = Field(default=False)
    nickname: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    portfolio_id: Optional[int] = None


class CryptoAccountCreate(CryptoAccountBase):
    """Schema for creating a crypto account"""
    pass


class CryptoAccountUpdate(BaseModel):
    """Schema for updating a crypto account"""
    exchange_name: Optional[str] = Field(None, min_length=1, max_length=50)
    account_holder_name: Optional[str] = Field(None, max_length=200)
    wallet_address: Optional[str] = Field(None, max_length=200)
    cash_balance_usd: Optional[float] = None
    total_value_usd: Optional[float] = None
    is_active: Optional[bool] = None
    is_primary: Optional[bool] = None
    nickname: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    last_sync_date: Optional[datetime] = None
    portfolio_id: Optional[int] = None


class CryptoAccountInDB(CryptoAccountBase):
    """Schema for crypto account in database"""
    id: int
    user_id: int
    last_sync_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CryptoAccount(CryptoAccountInDB):
    """Schema for crypto account response"""
    pass


class CryptoAccountWithAssets(CryptoAccount):
    """Schema for crypto account with asset statistics"""
    asset_count: int = 0
    total_invested_usd: float = 0.0
    current_value_usd: float = 0.0
    total_profit_loss_usd: float = 0.0


class CryptoAccountSummary(BaseModel):
    """Schema for crypto accounts summary"""
    total_accounts: int
    total_cash_balance_usd: float
    total_invested_usd: float
    total_current_value_usd: float
    total_profit_loss_usd: float
    accounts_by_exchange: dict

    class Config:
        from_attributes = True
