from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AssetTypeMasterUpdate(BaseModel):
    display_label: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class AssetTypeMasterInDB(BaseModel):
    id: int
    name: str
    display_label: str
    category: str
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AssetTypeMasterResponse(AssetTypeMasterInDB):
    pass
