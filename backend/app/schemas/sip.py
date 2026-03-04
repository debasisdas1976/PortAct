from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from datetime import date
from enum import auto
from app.core.enums import UpperStrEnum


class SIPPeriodicity(UpperStrEnum):
    WEEKLY = auto()
    MONTHLY = auto()
    QUARTERLY = auto()


class TopupType(UpperStrEnum):
    PERCENTAGE = auto()
    FIXED = auto()


class SIPTopup(BaseModel):
    topup_type: TopupType
    topup_value: float = Field(..., gt=0, description="Percentage (e.g. 10 for 10%) or fixed amount (e.g. 500)")


class SIPPeriod(BaseModel):
    sip_amount: float = Field(..., gt=0, description="SIP installment amount in INR")
    start_date: date
    end_date: date
    periodicity: SIPPeriodicity = SIPPeriodicity.MONTHLY
    topup: Optional[SIPTopup] = None

    @model_validator(mode="after")
    def end_after_start(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class SIPPreviewRequest(BaseModel):
    asset_id: int
    periods: List[SIPPeriod] = Field(..., min_length=1, max_length=10)


class SIPTransactionPreview(BaseModel):
    sip_number: int
    total_sips_in_period: int
    period_index: int
    transaction_date: date
    nav_date: date
    sip_amount: float
    nav: float
    units: float
    description: str
    nav_source: str  # "exact" or "previous_trading_day"


class SIPPreviewResponse(BaseModel):
    asset_id: int
    asset_name: str
    scheme_code: str
    total_transactions: int
    total_amount: float
    total_units: float
    average_nav: float
    transactions: List[SIPTransactionPreview]
    warnings: List[str]


class SIPCreateRequest(BaseModel):
    asset_id: int
    periods: List[SIPPeriod] = Field(..., min_length=1, max_length=10)
    update_asset_metrics: bool = True
