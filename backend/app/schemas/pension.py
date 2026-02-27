from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


PENSION_TYPES = ["eps", "family_pension", "superannuation", "annuity", "government", "other"]


class PensionAccountBase(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=100)
    plan_name: str = Field(..., min_length=1, max_length=200)
    provider_name: str = Field(..., min_length=1, max_length=200)
    pension_type: str = Field(..., description=f"One of: {', '.join(PENSION_TYPES)}")
    account_number: Optional[str] = Field(None, max_length=100)
    account_holder_name: str = Field(..., min_length=1, max_length=200)
    monthly_pension: float = Field(..., ge=0, description="Monthly pension amount (INR)")
    total_corpus: float = Field(0.0, ge=0, description="Total pension corpus / fund value (INR)")
    start_date: date
    is_active: bool = True
    notes: Optional[str] = None


class PensionAccountCreate(PensionAccountBase):
    portfolio_id: Optional[int] = None


class PensionAccountUpdate(BaseModel):
    nickname: Optional[str] = Field(None, min_length=1, max_length=100)
    plan_name: Optional[str] = Field(None, min_length=1, max_length=200)
    provider_name: Optional[str] = Field(None, min_length=1, max_length=200)
    pension_type: Optional[str] = None
    account_number: Optional[str] = Field(None, max_length=100)
    account_holder_name: Optional[str] = Field(None, min_length=1, max_length=200)
    monthly_pension: Optional[float] = Field(None, ge=0)
    total_corpus: Optional[float] = Field(None, ge=0)
    start_date: Optional[date] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class PensionAccountResponse(PensionAccountBase):
    id: int
    user_id: int
    asset_id: int
    # Override base fields to allow incomplete data in responses
    plan_name: str = ""
    provider_name: str = ""
    pension_type: str = ""
    account_holder_name: str = ""
    annual_pension: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PensionSummary(BaseModel):
    total_accounts: int
    active_accounts: int
    total_monthly_pension: float
    total_annual_pension: float
    total_corpus: float
    accounts: list[PensionAccountResponse]
