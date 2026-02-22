"""
Insurance Policy endpoints.

Tracks all types of insurance policies (term life, endowment, ULIP,
health, vehicle, home, personal accident).

For investment-linked policies (endowment, ULIP) current_value holds the
fund / surrender value.  For pure-protection policies the sum_assured
represents the coverage amount and current_value defaults to 0.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.asset import Asset, AssetType
from app.models.user import User
from app.schemas.insurance import (
    InsurancePolicyCreate,
    InsurancePolicyUpdate,
    InsurancePolicyResponse,
    InsuranceSummary,
    PREMIUM_FREQUENCIES,
)

router = APIRouter()

_ANNUAL_MULTIPLIER = {
    "monthly": 12,
    "quarterly": 4,
    "semi_annual": 2,
    "annual": 1,
    "single_premium": 0,  # One-time; no ongoing outflow
}


def _annual_premium(amount: float, frequency: str) -> float:
    return amount * _ANNUAL_MULTIPLIER.get(frequency, 1)


def _asset_to_response(asset: Asset) -> InsurancePolicyResponse:
    details = asset.details or {}
    premium_amount = details.get("premium_amount", 0.0)
    premium_frequency = details.get("premium_frequency", "annual")
    policy_end_date = details.get("policy_end_date")
    return InsurancePolicyResponse(
        id=asset.id,
        user_id=asset.user_id,
        asset_id=asset.id,
        nickname=asset.name,
        policy_name=details.get("policy_name") or asset.name or "",
        policy_number=asset.account_id or details.get("policy_number", ""),
        insurer_name=asset.broker_name or details.get("insurer", ""),
        policy_type=details.get("policy_type", ""),
        insured_name=asset.account_holder_name or "",
        sum_assured=details.get("sum_assured", 0.0),
        premium_amount=premium_amount,
        premium_frequency=premium_frequency,
        policy_start_date=asset.purchase_date.date() if asset.purchase_date else None,
        policy_end_date=policy_end_date,
        current_value=asset.current_value,
        total_premium_paid=asset.total_invested,
        nominee=details.get("nominee"),
        is_active=asset.is_active,
        notes=asset.notes,
        annual_premium=_annual_premium(premium_amount, premium_frequency),
        created_at=asset.created_at,
        updated_at=asset.last_updated,
    )


@router.get("/", response_model=List[InsurancePolicyResponse])
async def get_insurance_policies(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all insurance policies for the current user."""
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.INSURANCE_POLICY,
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()
    return [_asset_to_response(a) for a in assets]


@router.get("/summary", response_model=InsuranceSummary)
async def get_insurance_summary(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get insurance portfolio summary."""
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.INSURANCE_POLICY,
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()
    policies = [_asset_to_response(a) for a in assets]
    active = [p for p in policies if p.is_active]
    return InsuranceSummary(
        total_policies=len(policies),
        active_policies=len(active),
        total_sum_assured=sum(p.sum_assured for p in active),
        total_current_value=sum(p.current_value or 0 for p in active),
        total_annual_premium=sum(p.annual_premium for p in active),
        total_premium_paid=sum(p.total_premium_paid or 0 for p in active),
        policies=policies,
    )


@router.get("/{policy_id}", response_model=InsurancePolicyResponse)
async def get_insurance_policy(
    policy_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a specific insurance policy."""
    asset = db.query(Asset).filter(
        Asset.id == policy_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.INSURANCE_POLICY,
    ).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insurance policy not found")
    return _asset_to_response(asset)


@router.post("/", response_model=InsurancePolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_insurance_policy(
    data: InsurancePolicyCreate,
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new insurance policy."""
    current_value = data.current_value or 0.0
    try:
        asset = Asset(
            user_id=current_user.id,
            asset_type=AssetType.INSURANCE_POLICY,
            name=data.nickname,
            symbol="INSURANCE",
            account_id=data.policy_number,
            broker_name=data.insurer_name,
            account_holder_name=data.insured_name,
            quantity=1.0,
            purchase_price=data.sum_assured,
            current_price=current_value or data.sum_assured,
            total_invested=data.total_premium_paid or 0.0,
            current_value=current_value,
            purchase_date=datetime.combine(data.policy_start_date, datetime.min.time()),
            portfolio_id=portfolio_id or data.portfolio_id,
            is_active=data.is_active,
            notes=data.notes,
            details={
                "policy_name": data.policy_name,
                "policy_type": data.policy_type,
                "sum_assured": data.sum_assured,
                "premium_amount": data.premium_amount,
                "premium_frequency": data.premium_frequency,
                "policy_end_date": data.policy_end_date.isoformat() if data.policy_end_date else None,
                "nominee": data.nominee,
            },
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        logger.info(f"Insurance policy created: id={asset.id} user={current_user.id}")
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(f"DB error creating insurance policy: {exc}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to create insurance policy")
    return _asset_to_response(asset)


@router.put("/{policy_id}", response_model=InsurancePolicyResponse)
async def update_insurance_policy(
    policy_id: int,
    data: InsurancePolicyUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update an insurance policy."""
    asset = db.query(Asset).filter(
        Asset.id == policy_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.INSURANCE_POLICY,
    ).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insurance policy not found")

    details = dict(asset.details or {})

    if data.nickname is not None:
        asset.name = data.nickname
    if data.policy_name is not None:
        details["policy_name"] = data.policy_name
    if data.policy_number is not None:
        asset.account_id = data.policy_number
    if data.insurer_name is not None:
        asset.broker_name = data.insurer_name
    if data.policy_type is not None:
        details["policy_type"] = data.policy_type
    if data.insured_name is not None:
        asset.account_holder_name = data.insured_name
    if data.sum_assured is not None:
        details["sum_assured"] = data.sum_assured
        asset.purchase_price = data.sum_assured
    if data.premium_amount is not None:
        details["premium_amount"] = data.premium_amount
    if data.premium_frequency is not None:
        details["premium_frequency"] = data.premium_frequency
    if data.policy_start_date is not None:
        asset.purchase_date = datetime.combine(data.policy_start_date, datetime.min.time())
    if data.policy_end_date is not None:
        details["policy_end_date"] = data.policy_end_date.isoformat()
    if data.current_value is not None:
        asset.current_value = data.current_value
        asset.current_price = data.current_value
    if data.total_premium_paid is not None:
        asset.total_invested = data.total_premium_paid
    if data.nominee is not None:
        details["nominee"] = data.nominee
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
        logger.error(f"DB error updating insurance policy id={policy_id}: {exc}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to update insurance policy")
    return _asset_to_response(asset)


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_insurance_policy(
    policy_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete an insurance policy."""
    asset = db.query(Asset).filter(
        Asset.id == policy_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.INSURANCE_POLICY,
    ).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insurance policy not found")
    try:
        db.delete(asset)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(f"DB error deleting insurance policy id={policy_id}: {exc}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to delete insurance policy")
