"""Real Estate CRUD endpoints.

Supports three property sub-types (land, farm_land, house) all stored under
AssetType.REAL_ESTATE with a `property_type` discriminator in the details JSON.
"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.asset import Asset, AssetType
from app.models.user import User
from app.schemas.real_estate import (
    RealEstateCreate,
    RealEstateUpdate,
    RealEstateResponse,
    RealEstateSummary,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _asset_to_response(asset: Asset) -> RealEstateResponse:
    d = asset.details or {}
    purchase_price = d.get("purchase_price", asset.total_invested)
    current_market_value = d.get("current_market_value", asset.current_value)
    profit_loss = current_market_value - purchase_price
    profit_loss_pct = (profit_loss / purchase_price * 100) if purchase_price else 0.0
    return RealEstateResponse(
        id=asset.id,
        user_id=asset.user_id,
        asset_id=asset.id,
        nickname=asset.name,
        property_type=d.get("property_type", "land"),
        location=d.get("location", ""),
        city=d.get("city"),
        state=d.get("state"),
        pincode=d.get("pincode"),
        area=d.get("area", 0),
        area_unit=d.get("area_unit", "sqft"),
        purchase_price=purchase_price,
        current_market_value=current_market_value,
        purchase_date=(
            asset.purchase_date.date()
            if asset.purchase_date
            else datetime.now(timezone.utc).date()
        ),
        registration_number=d.get("registration_number"),
        loan_outstanding=d.get("loan_outstanding", 0),
        rental_income_monthly=d.get("rental_income_monthly", 0),
        is_active=asset.is_active,
        notes=asset.notes,
        profit_loss=round(profit_loss, 2),
        profit_loss_percentage=round(profit_loss_pct, 2),
        created_at=asset.created_at,
        updated_at=asset.last_updated,
    )


def _get_properties(db: Session, user_id: int, property_type: Optional[str] = None) -> list[Asset]:
    """Return REAL_ESTATE assets, optionally filtered by property_type (Python-side)."""
    assets = (
        db.query(Asset)
        .filter(
            Asset.user_id == user_id,
            Asset.asset_type == AssetType.REAL_ESTATE,
        )
        .order_by(Asset.created_at.desc())
        .all()
    )
    if property_type:
        assets = [a for a in assets if (a.details or {}).get("property_type") == property_type]
    return assets


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[RealEstateResponse])
async def list_properties(
    property_type: Optional[str] = Query(None, description="Filter by land, farm_land, or house"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all real estate properties for the current user."""
    assets = _get_properties(db, current_user.id, property_type)
    return [_asset_to_response(a) for a in assets]


@router.get("/summary", response_model=RealEstateSummary)
async def property_summary(
    property_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Summary statistics for real estate properties."""
    assets = _get_properties(db, current_user.id, property_type)
    properties = [_asset_to_response(a) for a in assets]
    total_invested = sum(p.purchase_price for p in properties)
    total_current = sum(p.current_market_value for p in properties)
    return RealEstateSummary(
        total_properties=len(properties),
        active_properties=sum(1 for p in properties if p.is_active),
        total_invested=total_invested,
        total_current_value=total_current,
        total_profit_loss=round(total_current - total_invested, 2),
        total_rental_income_monthly=sum(p.rental_income_monthly or 0 for p in properties),
        properties=properties,
    )


@router.get("/{property_id}", response_model=RealEstateResponse)
async def get_property(
    property_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a specific real estate property."""
    asset = db.query(Asset).filter(
        Asset.id == property_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.REAL_ESTATE,
    ).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return _asset_to_response(asset)


@router.post("/", response_model=RealEstateResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    data: RealEstateCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new real estate property."""
    profit_loss = data.current_market_value - data.purchase_price
    profit_loss_pct = (profit_loss / data.purchase_price * 100) if data.purchase_price else 0

    asset = Asset(
        user_id=current_user.id,
        asset_type=AssetType.REAL_ESTATE,
        name=data.nickname,
        symbol=data.property_type.upper(),
        quantity=1,
        purchase_price=data.purchase_price,
        current_price=data.current_market_value,
        total_invested=data.purchase_price,
        current_value=data.current_market_value,
        profit_loss=round(profit_loss, 2),
        profit_loss_percentage=round(profit_loss_pct, 2),
        purchase_date=datetime.combine(data.purchase_date, datetime.min.time()),
        is_active=data.is_active,
        notes=data.notes,
        details={
            "property_type": data.property_type,
            "location": data.location,
            "city": data.city,
            "state": data.state,
            "pincode": data.pincode,
            "area": data.area,
            "area_unit": data.area_unit,
            "purchase_price": data.purchase_price,
            "current_market_value": data.current_market_value,
            "registration_number": data.registration_number,
            "loan_outstanding": data.loan_outstanding or 0,
            "rental_income_monthly": data.rental_income_monthly or 0,
        },
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    logger.info(f"Real estate created: id={asset.id} type={data.property_type} user={current_user.id}")
    return _asset_to_response(asset)


@router.put("/{property_id}", response_model=RealEstateResponse)
async def update_property(
    property_id: int,
    data: RealEstateUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a real estate property."""
    asset = db.query(Asset).filter(
        Asset.id == property_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.REAL_ESTATE,
    ).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

    upd = data.dict(exclude_unset=True)
    d = dict(asset.details or {})

    # Update details JSON
    for key in (
        "property_type", "location", "city", "state", "pincode",
        "area", "area_unit", "registration_number",
        "loan_outstanding", "rental_income_monthly",
    ):
        if key in upd:
            d[key] = upd[key]

    if "nickname" in upd:
        asset.name = upd["nickname"]
    if "purchase_price" in upd:
        d["purchase_price"] = upd["purchase_price"]
        asset.total_invested = upd["purchase_price"]
        asset.purchase_price = upd["purchase_price"]
    if "current_market_value" in upd:
        d["current_market_value"] = upd["current_market_value"]
        asset.current_value = upd["current_market_value"]
        asset.current_price = upd["current_market_value"]
    if "purchase_date" in upd:
        asset.purchase_date = datetime.combine(upd["purchase_date"], datetime.min.time())
    if "is_active" in upd:
        asset.is_active = upd["is_active"]
    if "notes" in upd:
        asset.notes = upd["notes"]

    asset.details = d

    # Recalculate P/L
    purchase = d.get("purchase_price", asset.total_invested)
    current = d.get("current_market_value", asset.current_value)
    asset.profit_loss = round(current - purchase, 2)
    asset.profit_loss_percentage = round(
        (asset.profit_loss / purchase * 100) if purchase else 0, 2,
    )
    asset.last_updated = datetime.now(timezone.utc)

    db.commit()
    db.refresh(asset)
    return _asset_to_response(asset)


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a real estate property."""
    asset = db.query(Asset).filter(
        Asset.id == property_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.REAL_ESTATE,
    ).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    db.delete(asset)
    db.commit()
