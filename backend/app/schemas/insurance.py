from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


POLICY_TYPES = ["term_life", "endowment", "ulip", "health", "vehicle", "home", "personal_accident"]
PREMIUM_FREQUENCIES = ["monthly", "quarterly", "semi_annual", "annual", "single_premium"]


class InsurancePolicyBase(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=100)
    policy_name: str = Field(..., min_length=1, max_length=200)
    policy_number: str = Field(..., min_length=1, max_length=100)
    insurer_name: str = Field(..., min_length=1, max_length=200)
    policy_type: str = Field(..., description=f"One of: {', '.join(POLICY_TYPES)}")
    insured_name: str = Field(..., min_length=1, max_length=200)
    sum_assured: float = Field(..., gt=0)
    premium_amount: float = Field(..., gt=0)
    premium_frequency: str = Field(..., description=f"One of: {', '.join(PREMIUM_FREQUENCIES)}")
    policy_start_date: date
    policy_end_date: Optional[date] = None  # Maturity / expiry date
    current_value: Optional[float] = Field(None, ge=0, description="Fund value / surrender value (for ULIP/endowment)")
    total_premium_paid: Optional[float] = Field(None, ge=0)
    nominee: Optional[str] = None
    is_active: bool = True
    notes: Optional[str] = None


class InsurancePolicyCreate(InsurancePolicyBase):
    pass


class InsurancePolicyUpdate(BaseModel):
    nickname: Optional[str] = Field(None, min_length=1, max_length=100)
    policy_name: Optional[str] = Field(None, min_length=1, max_length=200)
    policy_number: Optional[str] = Field(None, min_length=1, max_length=100)
    insurer_name: Optional[str] = Field(None, min_length=1, max_length=200)
    policy_type: Optional[str] = None
    insured_name: Optional[str] = Field(None, min_length=1, max_length=200)
    sum_assured: Optional[float] = Field(None, gt=0)
    premium_amount: Optional[float] = Field(None, gt=0)
    premium_frequency: Optional[str] = None
    policy_start_date: Optional[date] = None
    policy_end_date: Optional[date] = None
    current_value: Optional[float] = Field(None, ge=0)
    total_premium_paid: Optional[float] = Field(None, ge=0)
    nominee: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class InsurancePolicyResponse(InsurancePolicyBase):
    id: int
    user_id: int
    asset_id: int
    annual_premium: float   # Normalised to annual regardless of frequency
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InsuranceSummary(BaseModel):
    total_policies: int
    active_policies: int
    total_sum_assured: float
    total_current_value: float   # Sum of fund/surrender values (investment policies)
    total_annual_premium: float  # Total annual outflow across all policies
    total_premium_paid: float
    policies: list[InsurancePolicyResponse]
