from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.asset import Asset
from app.models.mf_systematic_plan import MFSystematicPlan
from app.core.enums import SystematicPlanType
from app.schemas.mf_systematic_plan import (
    MFPlanCreate, MFPlanUpdate, MFPlanResponse, MFPlanListResponse,
)

router = APIRouter()

MF_ASSET_TYPES = {"equity_mutual_fund", "hybrid_mutual_fund", "debt_mutual_fund"}


def _validate_mf_asset(asset_id: int, user: User, db: Session) -> Asset:
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.user_id == user.id).first()
    if not asset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asset not found")
    asset_type_val = asset.asset_type.value if hasattr(asset.asset_type, 'value') else str(asset.asset_type)
    if asset_type_val not in MF_ASSET_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Only mutual fund assets are supported. Got: {asset_type_val}")
    return asset


def _plan_to_response(plan: MFSystematicPlan) -> MFPlanResponse:
    return MFPlanResponse(
        id=plan.id,
        plan_type=plan.plan_type.value if hasattr(plan.plan_type, 'value') else str(plan.plan_type),
        asset_id=plan.asset_id,
        asset_name=plan.asset.name if plan.asset else "Unknown",
        target_asset_id=plan.target_asset_id,
        target_asset_name=plan.target_asset.name if plan.target_asset else None,
        amount=plan.amount,
        frequency=plan.frequency.value if hasattr(plan.frequency, 'value') else str(plan.frequency),
        execution_day=plan.execution_day,
        start_date=plan.start_date,
        end_date=plan.end_date,
        is_active=plan.is_active,
        last_executed_date=plan.last_executed_date,
        notes=plan.notes,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.get("", response_model=MFPlanListResponse)
async def list_plans(
    plan_type: Optional[str] = Query(None, description="Filter by plan type: sip, stp, swp"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    query = db.query(MFSystematicPlan).filter(MFSystematicPlan.user_id == current_user.id)
    if plan_type:
        query = query.filter(MFSystematicPlan.plan_type == SystematicPlanType(plan_type))
    plans = query.order_by(MFSystematicPlan.created_at.desc()).all()
    return MFPlanListResponse(
        plans=[_plan_to_response(p) for p in plans],
        total=len(plans),
    )


@router.post("", response_model=MFPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    data: MFPlanCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _validate_mf_asset(data.asset_id, current_user, db)
    if data.target_asset_id:
        _validate_mf_asset(data.target_asset_id, current_user, db)

    plan = MFSystematicPlan(
        user_id=current_user.id,
        plan_type=data.plan_type,
        asset_id=data.asset_id,
        target_asset_id=data.target_asset_id,
        amount=data.amount,
        frequency=data.frequency,
        execution_day=data.execution_day,
        start_date=data.start_date,
        end_date=data.end_date,
        notes=data.notes,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _plan_to_response(plan)


@router.put("/{plan_id}", response_model=MFPlanResponse)
async def update_plan(
    plan_id: int,
    data: MFPlanUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    plan = db.query(MFSystematicPlan).filter(
        MFSystematicPlan.id == plan_id,
        MFSystematicPlan.user_id == current_user.id,
    ).first()
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")

    if data.target_asset_id is not None:
        _validate_mf_asset(data.target_asset_id, current_user, db)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)

    db.commit()
    db.refresh(plan)
    return _plan_to_response(plan)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    plan = db.query(MFSystematicPlan).filter(
        MFSystematicPlan.id == plan_id,
        MFSystematicPlan.user_id == current_user.id,
    ).first()
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")
    db.delete(plan)
    db.commit()


@router.patch("/{plan_id}/toggle", response_model=MFPlanResponse)
async def toggle_plan(
    plan_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    plan = db.query(MFSystematicPlan).filter(
        MFSystematicPlan.id == plan_id,
        MFSystematicPlan.user_id == current_user.id,
    ).first()
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")
    plan.is_active = not plan.is_active
    db.commit()
    db.refresh(plan)
    return _plan_to_response(plan)
