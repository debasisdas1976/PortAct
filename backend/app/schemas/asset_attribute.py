from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ---- Attribute Value schemas ----

class AssetAttributeValueBase(BaseModel):
    label: str = Field(..., min_length=1, max_length=100)
    color: Optional[str] = Field(None, max_length=20)
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)


class AssetAttributeValueCreate(AssetAttributeValueBase):
    pass


class AssetAttributeValueUpdate(BaseModel):
    label: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, max_length=20)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class AssetAttributeValueResponse(AssetAttributeValueBase):
    id: int
    attribute_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- Attribute schemas ----

class AssetAttributeBase(BaseModel):
    display_label: str = Field(..., min_length=1, max_length=150)
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)


class AssetAttributeCreate(AssetAttributeBase):
    values: Optional[List[AssetAttributeValueCreate]] = None


class AssetAttributeUpdate(BaseModel):
    display_label: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class AssetAttributeResponse(BaseModel):
    id: int
    user_id: int
    name: str
    display_label: str
    description: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    values: List[AssetAttributeValueResponse] = []

    class Config:
        from_attributes = True


# ---- Assignment schemas ----

class AssetAttributeAssignmentCreate(BaseModel):
    attribute_id: int
    attribute_value_id: int


class AssetAttributeAssignmentResponse(BaseModel):
    id: int
    asset_id: int
    attribute_id: int
    attribute_value_id: int
    created_at: datetime
    attribute_name: Optional[str] = None
    attribute_display_label: Optional[str] = None
    value_label: Optional[str] = None
    value_color: Optional[str] = None

    class Config:
        from_attributes = True


class BulkAssignmentUpdate(BaseModel):
    assignments: List[AssetAttributeAssignmentCreate]
