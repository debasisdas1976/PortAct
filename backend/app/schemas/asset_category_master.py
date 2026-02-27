from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AssetCategoryMasterUpdate(BaseModel):
    display_label: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, max_length=7)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class AssetCategoryMasterInDB(BaseModel):
    id: int
    name: str
    display_label: str
    color: Optional[str] = None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AssetCategoryMasterResponse(AssetCategoryMasterInDB):
    pass
