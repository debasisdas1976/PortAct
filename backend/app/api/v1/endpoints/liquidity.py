"""
Liquidity Insight API — serves global M2 + asset price history for the
Liquidity Insight dashboard.
"""

import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.services.liquidity_service import get_liquidity_data, refresh_liquidity_data

router = APIRouter()


@router.get("")
async def get_liquidity(
    _current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Return cached global M2 money supply (FRED) and asset price history
    (Yahoo Finance) for the Liquidity Insight dashboard.

    Response shape:
      {
        "m2": { "US": [...], "EU": [...], "CN": [...], "JP": [...] },
        "assets": { "spx": [...], "gold": [...], "btc": [...] },
        "last_updated": "2025-01-01T00:00:00",
        "fred_configured": true,
        "m2_series": ["US", "EU", "CN", "JP"]
      }
    Each series is a list of { "date": "YYYY-MM-DD", "value": float }.
    """
    return await asyncio.to_thread(get_liquidity_data, db)


@router.post("/refresh")
async def refresh_liquidity(
    _current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Force-refresh the liquidity data cache from FRED + Yahoo Finance."""
    await asyncio.to_thread(refresh_liquidity_data, db)
    return {"status": "ok", "message": "Liquidity data refreshed successfully"}
