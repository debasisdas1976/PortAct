"""
Pension endpoints.

Tracks pension income from various sources: EPS (Employee Pension Scheme),
family pension, superannuation funds, annuity plans, government pensions.
"""
from datetime import datetime, timezone
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
from app.schemas.pension import (
    PensionAccountCreate,
    PensionAccountUpdate,
    PensionAccountResponse,
    PensionSummary,
)

router = APIRouter()


def _asset_to_response(asset: Asset) -> PensionAccountResponse:
    details = asset.details or {}
    monthly_pension = details.get("monthly_pension", 0.0)
    start_str = details.get("start_date")
    if start_str:
        start_date = start_str
    elif asset.purchase_date:
        start_date = (asset.purchase_date.date() if hasattr(asset.purchase_date, "date") else asset.purchase_date)
    else:
        start_date = None
    return PensionAccountResponse(
        id=asset.id,
        user_id=asset.user_id,
        asset_id=asset.id,
        nickname=asset.name,
        plan_name=details.get("plan_name") or asset.name or "",
        provider_name=asset.broker_name or details.get("provider_name", ""),
        pension_type=details.get("pension_type", ""),
        account_number=asset.account_id or details.get("account_number"),
        account_holder_name=asset.account_holder_name or "",
        monthly_pension=monthly_pension,
        total_corpus=asset.total_invested or 0.0,
        start_date=start_date,
        is_active=asset.is_active,
        notes=asset.notes,
        annual_pension=monthly_pension * 12,
        created_at=asset.created_at,
        updated_at=asset.last_updated,
    )


@router.get("/", response_model=List[PensionAccountResponse])
async def get_pension_accounts(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all pension accounts for the current user."""
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.PENSION,
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()
    return [_asset_to_response(a) for a in assets]


@router.get("/summary", response_model=PensionSummary)
async def get_pension_summary(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get pension portfolio summary."""
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.PENSION,
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()
    accounts = [_asset_to_response(a) for a in assets]
    active = [a for a in accounts if a.is_active]
    return PensionSummary(
        total_accounts=len(accounts),
        active_accounts=len(active),
        total_monthly_pension=sum(a.monthly_pension for a in active),
        total_annual_pension=sum(a.annual_pension for a in active),
        total_corpus=sum(a.total_corpus for a in active),
        accounts=accounts,
    )


@router.get("/{pension_id}", response_model=PensionAccountResponse)
async def get_pension_account(
    pension_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a specific pension account."""
    asset = db.query(Asset).filter(
        Asset.id == pension_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.PENSION,
    ).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pension account not found")
    return _asset_to_response(asset)


@router.post("/", response_model=PensionAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_pension_account(
    data: PensionAccountCreate,
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new pension account."""
    resolved_portfolio_id = portfolio_id or data.portfolio_id or get_default_portfolio_id(current_user.id, db)

    try:
        asset = Asset(
            user_id=current_user.id,
            asset_type=AssetType.PENSION,
            name=data.nickname,
            symbol="PENSION",
            broker_name=data.provider_name,
            account_id=data.account_number,
            account_holder_name=data.account_holder_name,
            quantity=1.0,
            purchase_price=data.monthly_pension,
            current_price=data.monthly_pension,
            total_invested=data.total_corpus,
            current_value=data.monthly_pension,
            purchase_date=datetime.combine(data.start_date, datetime.min.time()),
            portfolio_id=resolved_portfolio_id,
            is_active=data.is_active,
            notes=data.notes,
            details={
                "plan_name": data.plan_name,
                "pension_type": data.pension_type,
                "monthly_pension": data.monthly_pension,
                "start_date": data.start_date.isoformat(),
            },
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        logger.info(f"Pension account created: id={asset.id} user={current_user.id}")
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(f"DB error creating pension account: {exc}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to create pension account")
    return _asset_to_response(asset)


@router.put("/{pension_id}", response_model=PensionAccountResponse)
async def update_pension_account(
    pension_id: int,
    data: PensionAccountUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a pension account."""
    asset = db.query(Asset).filter(
        Asset.id == pension_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.PENSION,
    ).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pension account not found")

    details = dict(asset.details or {})
    if data.nickname is not None:
        asset.name = data.nickname
    if data.provider_name is not None:
        asset.broker_name = data.provider_name
        details["provider_name"] = data.provider_name
    if data.account_number is not None:
        asset.account_id = data.account_number
    if data.account_holder_name is not None:
        asset.account_holder_name = data.account_holder_name
    if data.plan_name is not None:
        details["plan_name"] = data.plan_name
    if data.pension_type is not None:
        details["pension_type"] = data.pension_type
    if data.monthly_pension is not None:
        details["monthly_pension"] = data.monthly_pension
        asset.current_price = data.monthly_pension
        asset.current_value = data.monthly_pension
    if data.total_corpus is not None:
        asset.total_invested = data.total_corpus
    if data.start_date is not None:
        details["start_date"] = data.start_date.isoformat()
        asset.purchase_date = datetime.combine(data.start_date, datetime.min.time())
    if data.is_active is not None:
        asset.is_active = data.is_active
    if data.notes is not None:
        asset.notes = data.notes

    asset.details = details

    try:
        db.commit()
        db.refresh(asset)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(f"DB error updating pension account id={pension_id}: {exc}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to update pension account")
    return _asset_to_response(asset)


@router.delete("/{pension_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pension_account(
    pension_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a pension account."""
    asset = db.query(Asset).filter(
        Asset.id == pension_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.PENSION,
    ).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pension account not found")

    # Clear FK references that lack ON DELETE CASCADE/SET NULL in the DB
    db.query(Alert).filter(Alert.asset_id == pension_id).update(
        {Alert.asset_id: None}, synchronize_session=False
    )
    db.query(AssetSnapshot).filter(AssetSnapshot.asset_id == pension_id).update(
        {AssetSnapshot.asset_id: None}, synchronize_session=False
    )
    db.query(MutualFundHolding).filter(MutualFundHolding.asset_id == pension_id).delete(
        synchronize_session=False
    )
    db.query(Transaction).filter(Transaction.asset_id == pension_id).delete(
        synchronize_session=False
    )

    db.delete(asset)
    db.commit()
