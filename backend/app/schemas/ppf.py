from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date


class PPFAccountBase(BaseModel):
    """Base PPF account schema"""
    nickname: str = Field(..., min_length=1, max_length=100, description="Friendly name for the PPF account")
    account_number: str = Field(..., min_length=1, max_length=50)
    bank_name: str = Field(..., min_length=1, max_length=200)
    account_holder_name: str = Field(..., min_length=1, max_length=200)
    opening_date: date
    maturity_date: Optional[date] = None
    interest_rate: float = Field(..., ge=0, le=100)  # Annual interest rate percentage
    current_balance: float = Field(default=0.0, ge=0)
    total_deposits: float = Field(default=0.0, ge=0)
    total_interest_earned: float = Field(default=0.0, ge=0)
    financial_year: Optional[str] = None  # e.g., "2025-26"
    notes: Optional[str] = None


class PPFAccountCreate(PPFAccountBase):
    """Schema for creating a PPF account"""
    portfolio_id: Optional[int] = None


class PPFAccountUpdate(BaseModel):
    """Schema for updating a PPF account"""
    nickname: Optional[str] = Field(None, min_length=1, max_length=100)
    account_number: Optional[str] = Field(None, min_length=1, max_length=50)
    bank_name: Optional[str] = Field(None, min_length=1, max_length=200)
    account_holder_name: Optional[str] = Field(None, min_length=1, max_length=200)
    opening_date: Optional[date] = None
    maturity_date: Optional[date] = None
    interest_rate: Optional[float] = Field(None, ge=0, le=100)
    current_balance: Optional[float] = Field(None, ge=0)
    total_deposits: Optional[float] = Field(None, ge=0)
    total_interest_earned: Optional[float] = Field(None, ge=0)
    financial_year: Optional[str] = None
    notes: Optional[str] = None


class PPFTransactionBase(BaseModel):
    """Base PPF transaction schema"""
    transaction_date: date
    transaction_type: str = Field(..., pattern="^(deposit|interest|withdrawal)$")
    amount: float = Field(..., gt=0)
    balance_after_transaction: float = Field(..., ge=0)
    description: Optional[str] = None
    financial_year: Optional[str] = None


class PPFTransactionCreate(PPFTransactionBase):
    """Schema for creating a PPF transaction"""
    pass


class PPFTransaction(PPFTransactionBase):
    """Schema for PPF transaction response"""
    id: int
    asset_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class PPFStatementUpload(BaseModel):
    """Schema for PPF statement upload"""
    statement_type: str = "ppf_statement"
    password: Optional[str] = None  # For password-protected PDFs


class PPFAccountResponse(PPFAccountBase):
    """Schema for PPF account response"""
    id: int
    user_id: int
    asset_id: int  # Link to the asset record
    # Override base fields to allow empty strings in responses (data may be incomplete)
    account_number: str = ""
    bank_name: str = ""
    account_holder_name: str = ""
    # Override to remove ge=0 constraint; interest is stored explicitly, not derived
    total_interest_earned: float = 0.0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PPFAccountWithTransactions(PPFAccountResponse):
    """Schema for PPF account with transactions"""
    transactions: list[PPFTransaction] = []
    transaction_count: int = 0


class PPFSummary(BaseModel):
    """Schema for PPF portfolio summary"""
    total_accounts: int
    total_balance: float
    total_deposits: float
    total_interest_earned: float
    average_interest_rate: float
    accounts: list[PPFAccountResponse] = []

# Made with Bob