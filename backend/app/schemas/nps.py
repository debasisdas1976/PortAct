"""
National Pension System (NPS) Account Schemas
"""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class NPSAccountBase(BaseModel):
    """Base NPS account schema"""
    nickname: str = Field(..., min_length=1, max_length=100, description="Friendly name for the account")
    pran_number: str = Field(..., min_length=12, max_length=12, description="Permanent Retirement Account Number")
    account_holder_name: str = Field(..., min_length=1, max_length=100)
    sector_type: str = Field(..., pattern="^(government|corporate|all_citizen)$", description="NPS sector")
    tier_type: str = Field(..., pattern="^(tier_1|tier_2)$", description="Tier 1 or Tier 2")
    opening_date: date
    date_of_birth: date
    retirement_age: int = Field(60, ge=18, le=75, description="Expected retirement age")
    current_balance: float = Field(0, ge=0)
    total_contributions: float = Field(0, ge=0)
    employer_contributions: float = Field(0, ge=0)
    total_returns: float = Field(0, ge=0)
    scheme_preference: Optional[str] = Field(None, max_length=50, description="Active/Auto/Conservative")
    fund_manager: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class NPSAccountCreate(NPSAccountBase):
    """Schema for creating an NPS account"""
    portfolio_id: Optional[int] = None


class NPSAccountUpdate(BaseModel):
    """Schema for updating an NPS account"""
    nickname: Optional[str] = Field(None, min_length=1, max_length=100)
    sector_type: Optional[str] = Field(None, pattern="^(government|corporate|all_citizen)$")
    tier_type: Optional[str] = Field(None, pattern="^(tier_1|tier_2)$")
    retirement_age: Optional[int] = Field(None, ge=18, le=75)
    current_balance: Optional[float] = Field(None, ge=0)
    total_contributions: Optional[float] = Field(None, ge=0)
    employer_contributions: Optional[float] = Field(None, ge=0)
    total_returns: Optional[float] = Field(None, ge=0)
    scheme_preference: Optional[str] = None
    fund_manager: Optional[str] = None
    notes: Optional[str] = None


class NPSTransactionBase(BaseModel):
    """Base NPS transaction schema"""
    transaction_date: date
    transaction_type: str = Field(..., pattern="^(contribution|employer_contribution|returns|withdrawal|switch)$")
    amount: float = Field(..., gt=0)
    nav: Optional[float] = Field(None, gt=0, description="Net Asset Value")
    units: Optional[float] = Field(None, gt=0, description="Units allocated")
    scheme: Optional[str] = Field(None, max_length=50, description="E/C/G/A scheme")
    description: Optional[str] = None
    financial_year: Optional[str] = None


class NPSTransactionCreate(NPSTransactionBase):
    """Schema for creating an NPS transaction"""
    pass


class NPSTransaction(NPSTransactionBase):
    """Schema for NPS transaction response"""
    id: int
    asset_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class NPSStatementUpload(BaseModel):
    """Schema for NPS statement upload"""
    statement_type: str = "nps_statement"
    password: Optional[str] = None


class NPSAccountResponse(NPSAccountBase):
    """Schema for NPS account response"""
    id: int
    user_id: int
    asset_id: int
    # Override base fields to allow incomplete data in responses
    pran_number: str = ""
    account_holder_name: str = ""
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NPSAccountWithTransactions(NPSAccountResponse):
    """Schema for NPS account with transactions"""
    transactions: list[NPSTransaction] = []
    transaction_count: int = 0


class NPSSummary(BaseModel):
    """Schema for NPS summary statistics"""
    total_accounts: int
    total_balance: float
    total_contributions: float
    employer_contributions: float
    total_returns: float
    tier_1_balance: float
    tier_2_balance: float

# Made with Bob
