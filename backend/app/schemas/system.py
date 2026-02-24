from pydantic import BaseModel
from typing import Optional


class UpdateCheckResponse(BaseModel):
    """Response from the update check endpoint."""
    current_version: str
    latest_version: str
    update_available: bool
    release_url: Optional[str] = None
    release_notes: Optional[str] = None
    published_at: Optional[str] = None
    error: Optional[str] = None
