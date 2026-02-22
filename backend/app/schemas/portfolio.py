from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PortfolioBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class PortfolioCreate(PortfolioBase):
    pass


class PortfolioUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class Portfolio(PortfolioBase):
    id: int
    user_id: int
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PortfolioWithSummary(Portfolio):
    """Extended schema with computed asset count and total value."""
    asset_count: int = 0
    total_invested: float = 0.0
    total_current_value: float = 0.0

# Made with Bob
