"""
Sukanya Samriddhi Yojana (SSY) Account Schemas
"""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class SSYAccountBase(BaseModel):
    """Base SSY account schema"""
    nickname: str = Field(..., min_length=1, max_length=100, description="Friendly name for the account")
    account_number: str = Field(..., min_length=1, max_length=50)
    bank_name: str = Field(..., min_length=1, max_length=100)
    post_office_name: Optional[str] = Field(None, max_length=200)
    girl_name: str = Field(..., min_length=1, max_length=100, description="Name of the girl child")
    girl_dob: date = Field(..., description="Date of birth of the girl child")
    guardian_name: str = Field(..., min_length=1, max_length=100)
    opening_date: date
    maturity_date: Optional[date] = None  # 21 years from opening or marriage after 18
    interest_rate: float = Field(8.2, ge=0, le=100, description="Current interest rate")
    current_balance: float = Field(0, ge=0)
    total_deposits: float = Field(0, ge=0)
    total_interest_earned: float = Field(0, ge=0)
    financial_year: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None


class SSYAccountCreate(SSYAccountBase):
    """Schema for creating an SSY account"""
    pass


class SSYAccountUpdate(BaseModel):
    """Schema for updating an SSY account"""
    nickname: Optional[str] = Field(None, min_length=1, max_length=100)
    bank_name: Optional[str] = None
    post_office_name: Optional[str] = None
    guardian_name: Optional[str] = None
    interest_rate: Optional[float] = Field(None, ge=0, le=100)
    current_balance: Optional[float] = Field(None, ge=0)
    total_deposits: Optional[float] = Field(None, ge=0)
    total_interest_earned: Optional[float] = Field(None, ge=0)
    financial_year: Optional[str] = None
    notes: Optional[str] = None


class SSYTransactionBase(BaseModel):
    """Base SSY transaction schema"""
    transaction_date: date
    transaction_type: str = Field(..., pattern="^(deposit|interest|withdrawal|maturity)$")
    amount: float = Field(..., gt=0)
    balance_after_transaction: float = Field(..., ge=0)
    description: Optional[str] = None
    financial_year: Optional[str] = None


class SSYTransactionCreate(SSYTransactionBase):
    """Schema for creating an SSY transaction"""
    pass


class SSYTransaction(SSYTransactionBase):
    """Schema for SSY transaction response"""
    id: int
    asset_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class SSYStatementUpload(BaseModel):
    """Schema for SSY statement upload"""
    statement_type: str = "ssy_statement"
    password: Optional[str] = None


class SSYAccountResponse(SSYAccountBase):
    """Schema for SSY account response"""
    id: int
    user_id: int
    asset_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SSYAccountWithTransactions(SSYAccountResponse):
    """Schema for SSY account with transactions"""
    transactions: list[SSYTransaction] = []
    transaction_count: int = 0


class SSYSummary(BaseModel):
    """Schema for SSY summary statistics"""
    total_accounts: int
    total_balance: float
    total_deposits: float
    total_interest_earned: float
    average_interest_rate: float

# Made with Bob
