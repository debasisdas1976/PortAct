from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.crypto_account import CryptoExchange


class CryptoAccountBase(BaseModel):
    """Base crypto account schema"""
    exchange_name: CryptoExchange
    account_id: str = Field(..., min_length=1, max_length=200)
    account_holder_name: Optional[str] = Field(None, max_length=200)
    wallet_address: Optional[str] = Field(None, max_length=200)
    cash_balance_inr: float = Field(default=0.0)
    total_value_inr: float = Field(default=0.0)
    is_active: bool = Field(default=True)
    is_primary: bool = Field(default=False)
    nickname: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class CryptoAccountCreate(CryptoAccountBase):
    """Schema for creating a crypto account"""
    pass


class CryptoAccountUpdate(BaseModel):
    """Schema for updating a crypto account"""
    exchange_name: Optional[CryptoExchange] = None
    account_holder_name: Optional[str] = Field(None, max_length=200)
    wallet_address: Optional[str] = Field(None, max_length=200)
    cash_balance_inr: Optional[float] = None
    total_value_inr: Optional[float] = None
    is_active: Optional[bool] = None
    is_primary: Optional[bool] = None
    nickname: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    last_sync_date: Optional[datetime] = None


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
    total_invested_inr: float = 0.0
    current_value_inr: float = 0.0
    total_profit_loss_inr: float = 0.0


class CryptoAccountSummary(BaseModel):
    """Schema for crypto accounts summary"""
    total_accounts: int
    total_cash_balance_inr: float
    total_invested_inr: float
    total_current_value_inr: float
    total_profit_loss_inr: float
    accounts_by_exchange: dict
    
    class Config:
        from_attributes = True

# Made with Bob