from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AppSettingResponse(BaseModel):
    """Single app setting returned from API."""
    key: str
    value: Optional[str] = None
    value_type: str = "string"
    category: Optional[str] = None
    label: Optional[str] = None
    description: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AppSettingUpdate(BaseModel):
    """Payload to update a single setting."""
    key: str
    value: str


class AppSettingsBulkUpdate(BaseModel):
    """Payload to update multiple settings at once."""
    settings: List[AppSettingUpdate]
