from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class InstitutionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    display_label: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=30)
    website: Optional[str] = Field(None, max_length=200)
    has_parser: bool = Field(default=False)
    supported_formats: Optional[str] = Field(None, max_length=100)
    is_active: bool = Field(default=True)
    sort_order: int = Field(default=0)


class InstitutionCreate(InstitutionBase):
    pass


class InstitutionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    display_label: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, min_length=1, max_length=30)
    website: Optional[str] = Field(None, max_length=200)
    has_parser: Optional[bool] = None
    supported_formats: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class InstitutionInDB(InstitutionBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InstitutionResponse(InstitutionInDB):
    pass
