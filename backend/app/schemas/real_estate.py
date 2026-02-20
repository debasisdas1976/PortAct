"""Real Estate Schemas"""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


PROPERTY_TYPES = ["land", "farm_land", "house"]
AREA_UNITS = ["sqft", "acres", "hectares", "cents", "guntha"]


class RealEstateBase(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=200)
    property_type: str = Field(..., description=f"One of: {', '.join(PROPERTY_TYPES)}")
    location: str = Field(..., min_length=1, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=10)
    area: float = Field(..., gt=0)
    area_unit: str = Field("sqft", description=f"One of: {', '.join(AREA_UNITS)}")
    purchase_price: float = Field(..., gt=0)
    current_market_value: float = Field(..., gt=0)
    purchase_date: date
    registration_number: Optional[str] = Field(None, max_length=100)
    loan_outstanding: Optional[float] = Field(0, ge=0)
    rental_income_monthly: Optional[float] = Field(0, ge=0)
    is_active: bool = True
    notes: Optional[str] = None


class RealEstateCreate(RealEstateBase):
    pass


class RealEstateUpdate(BaseModel):
    nickname: Optional[str] = Field(None, min_length=1, max_length=200)
    property_type: Optional[str] = None
    location: Optional[str] = Field(None, min_length=1, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=10)
    area: Optional[float] = Field(None, gt=0)
    area_unit: Optional[str] = None
    purchase_price: Optional[float] = Field(None, gt=0)
    current_market_value: Optional[float] = Field(None, gt=0)
    purchase_date: Optional[date] = None
    registration_number: Optional[str] = Field(None, max_length=100)
    loan_outstanding: Optional[float] = Field(None, ge=0)
    rental_income_monthly: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class RealEstateResponse(RealEstateBase):
    id: int
    user_id: int
    asset_id: int
    profit_loss: float
    profit_loss_percentage: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RealEstateSummary(BaseModel):
    total_properties: int
    active_properties: int
    total_invested: float
    total_current_value: float
    total_profit_loss: float
    total_rental_income_monthly: float
    properties: list[RealEstateResponse]
