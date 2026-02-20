"""Recurring Deposit Schemas"""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class RDTransactionBase(BaseModel):
    transaction_date: date
    amount: float = Field(..., gt=0)
    transaction_type: str = Field(..., pattern="^(installment|interest)$")
    description: Optional[str] = None


class RDTransactionCreate(RDTransactionBase):
    pass


class RDTransactionUpdate(BaseModel):
    transaction_date: Optional[date] = None
    amount: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None


class RDTransactionResponse(BaseModel):
    id: int
    asset_id: int
    transaction_date: date
    amount: float
    transaction_type: str  # 'installment' or 'interest'
    description: Optional[str]
    is_auto_generated: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RDAccountBase(BaseModel):
    bank_name: str = Field(..., min_length=1, max_length=100)
    nickname: Optional[str] = Field(None, max_length=100)
    account_number: Optional[str] = Field(None, max_length=50)
    monthly_installment: float = Field(..., gt=0)
    interest_rate: float = Field(..., gt=0, le=50, description="Annual interest rate in %")
    start_date: date
    maturity_date: Optional[date] = None
    auto_update: bool = Field(False, description="Auto-generate installment/interest transactions on page load")
    notes: Optional[str] = None


class RDAccountCreate(RDAccountBase):
    pass


class RDAccountUpdate(BaseModel):
    bank_name: Optional[str] = Field(None, min_length=1, max_length=100)
    nickname: Optional[str] = Field(None, max_length=100)
    account_number: Optional[str] = Field(None, max_length=50)
    monthly_installment: Optional[float] = Field(None, gt=0)
    interest_rate: Optional[float] = Field(None, gt=0, le=50)
    start_date: Optional[date] = None
    maturity_date: Optional[date] = None
    auto_update: Optional[bool] = None
    notes: Optional[str] = None


class RDAccountResponse(RDAccountBase):
    id: int
    user_id: int
    total_deposited: float
    current_value: float
    total_interest_earned: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RDAccountWithTransactions(RDAccountResponse):
    transactions: List[RDTransactionResponse] = []
    transaction_count: int = 0


class RDSummary(BaseModel):
    total_accounts: int
    total_deposited: float
    total_current_value: float
    total_interest_earned: float


class RDGenerateResponse(BaseModel):
    installments_created: int
    interest_transactions_created: int
    new_current_value: float
    total_interest_earned: float

# Made with Bob
