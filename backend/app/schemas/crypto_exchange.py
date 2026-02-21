from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CryptoExchangeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    display_label: str = Field(..., min_length=1, max_length=100)
    exchange_type: str = Field(default="exchange")
    website: Optional[str] = Field(None, max_length=200)
    is_active: bool = Field(default=True)
    sort_order: int = Field(default=0)


class CryptoExchangeCreate(CryptoExchangeBase):
    pass


class CryptoExchangeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    display_label: Optional[str] = Field(None, min_length=1, max_length=100)
    exchange_type: Optional[str] = None
    website: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class CryptoExchangeInDB(CryptoExchangeBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CryptoExchangeResponse(CryptoExchangeInDB):
    pass
