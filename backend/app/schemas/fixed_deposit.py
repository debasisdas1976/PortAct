"""Fixed Deposit Schemas"""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class FDTransactionBase(BaseModel):
    transaction_date: date
    amount: float = Field(..., gt=0)
    description: Optional[str] = None


class FDTransactionCreate(FDTransactionBase):
    pass


class FDTransactionUpdate(BaseModel):
    transaction_date: Optional[date] = None
    amount: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None


class FDTransactionResponse(BaseModel):
    id: int
    asset_id: int
    transaction_date: date
    amount: float
    description: Optional[str]
    is_auto_generated: bool
    created_at: datetime

    class Config:
        from_attributes = True


class FDAccountBase(BaseModel):
    bank_name: str = Field(..., min_length=1, max_length=100)
    nickname: Optional[str] = Field(None, max_length=100)
    account_number: Optional[str] = Field(None, max_length=50)
    principal_amount: float = Field(..., gt=0)
    interest_rate: float = Field(..., gt=0, le=50, description="Annual interest rate in %")
    interest_type: str = Field(..., pattern="^(simple|compound)$")
    compounding_frequency: str = Field("annually", pattern="^(monthly|quarterly|half_yearly|annually)$")
    start_date: date
    maturity_date: Optional[date] = None
    auto_update: bool = Field(False, description="Auto-generate interest transactions on page load")
    notes: Optional[str] = None


class FDAccountCreate(FDAccountBase):
    pass


class FDAccountUpdate(BaseModel):
    bank_name: Optional[str] = Field(None, min_length=1, max_length=100)
    nickname: Optional[str] = Field(None, max_length=100)
    account_number: Optional[str] = Field(None, max_length=50)
    principal_amount: Optional[float] = Field(None, gt=0)
    interest_rate: Optional[float] = Field(None, gt=0, le=50)
    interest_type: Optional[str] = Field(None, pattern="^(simple|compound)$")
    compounding_frequency: Optional[str] = Field(None, pattern="^(monthly|quarterly|half_yearly|annually)$")
    start_date: Optional[date] = None
    maturity_date: Optional[date] = None
    auto_update: Optional[bool] = None
    notes: Optional[str] = None


class FDAccountResponse(FDAccountBase):
    id: int
    user_id: int
    current_value: float
    total_interest_earned: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FDAccountWithTransactions(FDAccountResponse):
    transactions: List[FDTransactionResponse] = []
    transaction_count: int = 0


class FDSummary(BaseModel):
    total_accounts: int
    total_principal: float
    total_current_value: float
    total_interest_earned: float


class FDGenerateInterestResponse(BaseModel):
    transactions_created: int
    new_current_value: float
    total_interest_earned: float

# Made with Bob
