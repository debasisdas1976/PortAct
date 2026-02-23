"""
Gratuity endpoints.

Gratuity is calculated using the Payment of Gratuity Act formula:
    Gratuity = (Basic Pay × 15 × Completed Years of Service) / 26
Capped at ₹20,00,000 (₹20 lakh) as per the Act.
Eligibility requires a minimum of 5 completed years of service.
"""
import math
from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.api.dependencies import get_current_active_user, get_default_portfolio_id
from app.models.asset import Asset, AssetType
from app.models.user import User
from app.models.transaction import Transaction
from app.models.portfolio_snapshot import AssetSnapshot
from app.models.alert import Alert
from app.models.mutual_fund_holding import MutualFundHolding
from app.schemas.gratuity import (
    GratuityAccountCreate,
    GratuityAccountUpdate,
    GratuityAccountResponse,
    GratuitySummary,
)

router = APIRouter()

_GRATUITY_CAP = 2_000_000.0  # ₹20 lakh


def _compute_gratuity(basic_pay: float, date_of_joining: date) -> dict:
    today = date.today()
    days = (today - date_of_joining).days
    years_of_service = days / 365.25
    completed_years = math.floor(years_of_service)
    raw_gratuity = (basic_pay * 15 * completed_years) / 26
    is_capped = raw_gratuity > _GRATUITY_CAP
    gratuity_amount = min(raw_gratuity, _GRATUITY_CAP)
    return {
        "years_of_service": round(years_of_service, 2),
        "completed_years": completed_years,
        "gratuity_amount": gratuity_amount,
        "is_eligible": completed_years >= 5,
        "is_capped": is_capped,
    }


def _asset_to_response(asset: Asset) -> GratuityAccountResponse:
    details = asset.details or {}
    # date_of_joining may be in details or derived from purchase_date
    doj_str = details.get("date_of_joining")
    if doj_str:
        date_of_joining = date.fromisoformat(doj_str)
    elif asset.purchase_date:
        date_of_joining = asset.purchase_date.date() if hasattr(asset.purchase_date, 'date') else asset.purchase_date
    else:
        date_of_joining = date.today()
    # basic_pay may be stored as basic_pay or last_drawn_salary
    basic_pay = details.get("basic_pay") or details.get("last_drawn_salary", 0.0)
    computed = _compute_gratuity(basic_pay, date_of_joining)
    return GratuityAccountResponse(
        id=asset.id,
        user_id=asset.user_id,
        asset_id=asset.id,
        nickname=asset.name,
        employer_name=asset.broker_name or details.get("employer_name", ""),
        employee_name=asset.account_holder_name or "",
        date_of_joining=date_of_joining,
        basic_pay=basic_pay,
        is_active=asset.is_active,
        notes=asset.notes,
        created_at=asset.created_at,
        updated_at=asset.last_updated,
        **computed,
    )


@router.get("/", response_model=List[GratuityAccountResponse])
async def get_gratuity_accounts(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all gratuity accounts for the current user."""
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.GRATUITY,
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()
    return [_asset_to_response(a) for a in assets]


@router.get("/summary", response_model=GratuitySummary)
async def get_gratuity_summary(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get gratuity portfolio summary."""
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.GRATUITY,
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()
    accounts = [_asset_to_response(a) for a in assets]
    return GratuitySummary(
        total_accounts=len(accounts),
        active_accounts=sum(1 for a in accounts if a.is_active),
        total_gratuity=sum(a.gratuity_amount for a in accounts if a.is_active),
        accounts=accounts,
    )


@router.get("/{gratuity_id}", response_model=GratuityAccountResponse)
async def get_gratuity_account(
    gratuity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a specific gratuity account."""
    asset = db.query(Asset).filter(
        Asset.id == gratuity_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.GRATUITY,
    ).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gratuity account not found")
    return _asset_to_response(asset)


@router.post("/", response_model=GratuityAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_gratuity_account(
    data: GratuityAccountCreate,
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new gratuity account."""
    resolved_portfolio_id = portfolio_id or data.portfolio_id or get_default_portfolio_id(current_user.id, db)

    computed = _compute_gratuity(data.basic_pay, data.date_of_joining)
    try:
        asset = Asset(
            user_id=current_user.id,
            asset_type=AssetType.GRATUITY,
            name=data.nickname,
            symbol="GRATUITY",
            broker_name=data.employer_name,
            account_holder_name=data.employee_name,
            quantity=1.0,
            purchase_price=computed["gratuity_amount"],
            current_price=computed["gratuity_amount"],
            total_invested=0.0,
            current_value=computed["gratuity_amount"],
            purchase_date=datetime.combine(data.date_of_joining, datetime.min.time()),
            portfolio_id=resolved_portfolio_id,
            is_active=data.is_active,
            notes=data.notes,
            details={
                "basic_pay": data.basic_pay,
                "date_of_joining": data.date_of_joining.isoformat(),
            },
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        logger.info(f"Gratuity account created: id={asset.id} user={current_user.id}")
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(f"DB error creating gratuity account: {exc}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to create gratuity account")
    return _asset_to_response(asset)


@router.put("/{gratuity_id}", response_model=GratuityAccountResponse)
async def update_gratuity_account(
    gratuity_id: int,
    data: GratuityAccountUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a gratuity account."""
    asset = db.query(Asset).filter(
        Asset.id == gratuity_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.GRATUITY,
    ).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gratuity account not found")

    details = dict(asset.details or {})
    if data.nickname is not None:
        asset.name = data.nickname
    if data.employer_name is not None:
        asset.broker_name = data.employer_name
    if data.employee_name is not None:
        asset.account_holder_name = data.employee_name
    if data.date_of_joining is not None:
        details["date_of_joining"] = data.date_of_joining.isoformat()
        asset.purchase_date = datetime.combine(data.date_of_joining, datetime.min.time())
    if data.basic_pay is not None:
        details["basic_pay"] = data.basic_pay
    if data.is_active is not None:
        asset.is_active = data.is_active
    if data.notes is not None:
        asset.notes = data.notes

    asset.details = details

    # Recalculate gratuity with latest values
    doj = date.fromisoformat(details["date_of_joining"])
    computed = _compute_gratuity(details.get("basic_pay", 0.0), doj)
    asset.current_price = computed["gratuity_amount"]
    asset.current_value = computed["gratuity_amount"]

    try:
        db.commit()
        db.refresh(asset)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(f"DB error updating gratuity account id={gratuity_id}: {exc}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to update gratuity account")
    return _asset_to_response(asset)


@router.delete("/{gratuity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gratuity_account(
    gratuity_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a gratuity account."""
    asset = db.query(Asset).filter(
        Asset.id == gratuity_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.GRATUITY,
    ).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gratuity account not found")

    # Clear FK references that lack ON DELETE CASCADE/SET NULL in the DB
    db.query(Alert).filter(Alert.asset_id == gratuity_id).update(
        {Alert.asset_id: None}, synchronize_session=False
    )
    db.query(AssetSnapshot).filter(AssetSnapshot.asset_id == gratuity_id).update(
        {AssetSnapshot.asset_id: None}, synchronize_session=False
    )
    db.query(MutualFundHolding).filter(MutualFundHolding.asset_id == gratuity_id).delete(
        synchronize_session=False
    )
    db.query(Transaction).filter(Transaction.asset_id == gratuity_id).delete(
        synchronize_session=False
    )

    db.delete(asset)
    db.commit()
