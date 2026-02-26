from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


def _normalize_name(v: str) -> str:
    """Normalize master-table name: lowercase, strip, spaces to underscores."""
    return v.strip().lower().replace(" ", "_")


class BankBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        return _normalize_name(v)
    display_label: str = Field(..., min_length=1, max_length=100)
    bank_type: str = Field(default="commercial")
    website: Optional[str] = Field(None, max_length=200)
    has_parser: bool = Field(default=False)
    supported_formats: Optional[str] = Field(None, max_length=500)
    is_active: bool = Field(default=True)
    sort_order: int = Field(default=0)


class BankCreate(BankBase):
    pass


class BankUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str | None) -> str | None:
        return _normalize_name(v) if v is not None else v
    display_label: Optional[str] = Field(None, min_length=1, max_length=100)
    bank_type: Optional[str] = None
    website: Optional[str] = Field(None, max_length=200)
    has_parser: Optional[bool] = None
    supported_formats: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class BankInDB(BankBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BankResponse(BankInDB):
    pass
