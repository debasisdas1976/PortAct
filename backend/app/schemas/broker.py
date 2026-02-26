from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from datetime import datetime

BROKER_TYPES = Literal["discount", "full_service", "international", "aggregator"]
SUPPORTED_MARKETS = Literal["domestic", "international", "both"]


def _normalize_name(v: str) -> str:
    """Normalize master-table name: lowercase, strip, spaces to underscores."""
    return v.strip().lower().replace(" ", "_")


class BrokerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        return _normalize_name(v)
    display_label: str = Field(..., min_length=1, max_length=500)
    broker_type: BROKER_TYPES = Field(default="discount")
    supported_markets: SUPPORTED_MARKETS = Field(default="domestic")
    website: Optional[str] = Field(None, max_length=200)
    has_parser: bool = Field(default=False)
    supported_formats: Optional[str] = Field(None, max_length=500)
    is_active: bool = Field(default=True)
    sort_order: int = Field(default=0)


class BrokerCreate(BrokerBase):
    pass


class BrokerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str | None) -> str | None:
        return _normalize_name(v) if v is not None else v
    display_label: Optional[str] = Field(None, min_length=1, max_length=500)
    broker_type: Optional[BROKER_TYPES] = None
    supported_markets: Optional[SUPPORTED_MARKETS] = None
    website: Optional[str] = Field(None, max_length=200)
    has_parser: Optional[bool] = None
    supported_formats: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class BrokerInDB(BrokerBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BrokerResponse(BrokerInDB):
    pass
