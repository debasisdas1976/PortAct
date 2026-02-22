from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.bank_account import BankType


class BankAccountBase(BaseModel):
    """Base bank account schema"""
    bank_name: str
    account_type: BankType
    account_number: str = Field(..., min_length=1, max_length=50)
    account_holder_name: Optional[str] = Field(None, max_length=200)
    ifsc_code: Optional[str] = Field(None, max_length=20)
    branch_name: Optional[str] = Field(None, max_length=200)
    current_balance: float = Field(default=0.0)
    available_balance: float = Field(default=0.0)
    credit_limit: float = Field(default=0.0, ge=0)
    is_active: bool = Field(default=True)
    is_primary: bool = Field(default=False)
    nickname: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    portfolio_id: Optional[int] = None


class BankAccountCreate(BankAccountBase):
    """Schema for creating a bank account"""
    pass


class BankAccountUpdate(BaseModel):
    """Schema for updating a bank account"""
    bank_name: Optional[str] = None
    account_type: Optional[BankType] = None
    account_holder_name: Optional[str] = Field(None, max_length=200)
    ifsc_code: Optional[str] = Field(None, max_length=20)
    branch_name: Optional[str] = Field(None, max_length=200)
    current_balance: Optional[float] = None
    available_balance: Optional[float] = None
    credit_limit: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None
    is_primary: Optional[bool] = None
    nickname: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    last_statement_date: Optional[datetime] = None
    portfolio_id: Optional[int] = None


class BankAccountInDB(BankAccountBase):
    """Schema for bank account in database"""
    id: int
    user_id: int
    last_statement_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class BankAccount(BankAccountInDB):
    """Schema for bank account response"""
    pass


class BankAccountWithExpenses(BankAccount):
    """Schema for bank account with expense count"""
    expense_count: int = 0
    total_debits: float = 0.0
    total_credits: float = 0.0


class BankAccountSummary(BaseModel):
    """Schema for bank accounts summary"""
    total_accounts: int
    total_balance: float
    total_credit_limit: float
    accounts_by_type: dict
    accounts_by_bank: dict
    
    class Config:
        from_attributes = True

# Made with Bob