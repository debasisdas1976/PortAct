from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


class GratuityAccountBase(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=100)
    employer_name: str = Field(..., min_length=1, max_length=200)
    employee_name: str = Field(..., min_length=1, max_length=200)
    date_of_joining: date
    basic_pay: float = Field(..., gt=0, description="Monthly basic salary component (INR)")
    is_active: bool = True
    notes: Optional[str] = None


class GratuityAccountCreate(GratuityAccountBase):
    portfolio_id: Optional[int] = None


class GratuityAccountUpdate(BaseModel):
    nickname: Optional[str] = Field(None, min_length=1, max_length=100)
    employer_name: Optional[str] = Field(None, min_length=1, max_length=200)
    employee_name: Optional[str] = Field(None, min_length=1, max_length=200)
    date_of_joining: Optional[date] = None
    basic_pay: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class GratuityAccountResponse(GratuityAccountBase):
    id: int
    user_id: int
    asset_id: int
    # Override base fields to allow incomplete data in responses
    employer_name: str = ""
    employee_name: str = ""
    years_of_service: float
    completed_years: int
    gratuity_amount: float
    is_eligible: bool  # True if completed_years >= 5
    is_capped: bool    # True if gratuity would exceed ₹20 lakh cap
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GratuitySummary(BaseModel):
    total_accounts: int
    active_accounts: int
    total_gratuity: float
    accounts: list[GratuityAccountResponse]
