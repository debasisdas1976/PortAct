"""
Provident Fund (PF/EPF) Account Schemas
"""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class PFAccountBase(BaseModel):
    """Base PF account schema"""
    nickname: str = Field(..., min_length=1, max_length=100, description="Friendly name for the account")
    uan_number: str = Field(..., min_length=12, max_length=12, description="Universal Account Number")
    pf_number: Optional[str] = Field(None, max_length=50, description="PF Account Number")
    account_holder_name: str = Field(..., min_length=1, max_length=100)
    employer_name: str = Field(..., min_length=1, max_length=200)
    date_of_joining: date
    date_of_exit: Optional[date] = None
    current_balance: float = Field(0, ge=0)
    employee_contribution: float = Field(0, ge=0)
    employer_contribution: float = Field(0, ge=0)
    pension_contribution: float = Field(0, ge=0)
    total_interest_earned: float = Field(0, ge=0)
    interest_rate: float = Field(8.25, ge=0, le=100, description="Current EPF interest rate")
    is_active: bool = Field(True, description="Whether account is active")
    notes: Optional[str] = None


class PFAccountCreate(PFAccountBase):
    """Schema for creating a PF account"""
    pass


class PFAccountUpdate(BaseModel):
    """Schema for updating a PF account"""
    nickname: Optional[str] = Field(None, min_length=1, max_length=100)
    pf_number: Optional[str] = None
    employer_name: Optional[str] = None
    date_of_exit: Optional[date] = None
    current_balance: Optional[float] = Field(None, ge=0)
    employee_contribution: Optional[float] = Field(None, ge=0)
    employer_contribution: Optional[float] = Field(None, ge=0)
    pension_contribution: Optional[float] = Field(None, ge=0)
    total_interest_earned: Optional[float] = Field(None, ge=0)
    interest_rate: Optional[float] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class PFTransactionBase(BaseModel):
    """Base PF transaction schema"""
    transaction_date: date
    transaction_type: str = Field(..., description="Transaction type: deposit, transfer_in, interest, withdrawal, transfer_out")
    amount: float = Field(..., gt=0)
    balance_after_transaction: float = Field(..., ge=0)
    contribution_type: Optional[str] = Field(None, pattern="^(epf|eps|edli)?$", description="EPF/EPS/EDLI")
    description: Optional[str] = None
    financial_year: Optional[str] = None


class PFTransactionCreate(PFTransactionBase):
    """Schema for creating a PF transaction"""
    pass


class PFTransaction(PFTransactionBase):
    """Schema for PF transaction response"""
    id: int
    asset_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class PFStatementUpload(BaseModel):
    """Schema for PF statement upload"""
    statement_type: str = "pf_statement"
    password: Optional[str] = None


class PFAccountResponse(PFAccountBase):
    """Schema for PF account response"""
    id: int
    user_id: int
    asset_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PFAccountWithTransactions(PFAccountResponse):
    """Schema for PF account with transactions"""
    transactions: list[PFTransaction] = []
    transaction_count: int = 0


class PFSummary(BaseModel):
    """Schema for PF summary statistics"""
    total_accounts: int
    active_accounts: int
    total_balance: float
    employee_contribution: float
    employer_contribution: float
    pension_contribution: float
    total_interest_earned: float
    average_interest_rate: float

# Made with Bob
