from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from app.models.demat_account import AccountMarket


class DematAccountBase(BaseModel):
    """Base demat account schema"""
    broker_name: str

    @field_validator("broker_name")
    @classmethod
    def normalize_broker_name(cls, v: str) -> str:
        return v.strip().lower().replace(" ", "_")
    account_market: AccountMarket = Field(default=AccountMarket.DOMESTIC)
    account_id: str = Field(..., min_length=1, max_length=50)
    account_holder_name: Optional[str] = Field(None, max_length=200)
    demat_account_number: Optional[str] = Field(None, max_length=50)
    cash_balance: float = Field(default=0.0)
    cash_balance_usd: Optional[float] = None
    currency: str = Field(default='INR')
    is_active: bool = Field(default=True)
    is_primary: bool = Field(default=False)
    nickname: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    portfolio_id: Optional[int] = None


class DematAccountCreate(DematAccountBase):
    """Schema for creating a demat account"""
    pass


class DematAccountUpdate(BaseModel):
    """Schema for updating a demat account"""
    broker_name: Optional[str] = None

    @field_validator("broker_name")
    @classmethod
    def normalize_broker_name(cls, v: str | None) -> str | None:
        return v.strip().lower().replace(" ", "_") if v is not None else v
    account_market: Optional[AccountMarket] = None
    account_id: Optional[str] = Field(None, min_length=1, max_length=50)
    account_holder_name: Optional[str] = Field(None, max_length=200)
    demat_account_number: Optional[str] = Field(None, max_length=50)
    cash_balance: Optional[float] = None
    cash_balance_usd: Optional[float] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None
    is_primary: Optional[bool] = None
    nickname: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    last_statement_date: Optional[datetime] = None
    portfolio_id: Optional[int] = None


class DematAccountInDB(DematAccountBase):
    """Schema for demat account in database"""
    id: int
    user_id: int
    last_statement_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DematAccount(DematAccountInDB):
    """Schema for demat account response"""
    pass


class DematAccountWithAssets(DematAccount):
    """Schema for demat account with asset statistics"""
    asset_count: int = 0
    total_invested: float = 0.0
    current_value: float = 0.0
    total_profit_loss: float = 0.0


class DematAccountSummary(BaseModel):
    """Schema for demat accounts summary"""
    total_accounts: int
    total_cash_balance: float
    total_invested: float
    total_current_value: float
    total_profit_loss: float
    accounts_by_broker: dict
    
    class Config:
        from_attributes = True

# Made with Bob