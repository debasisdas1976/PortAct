from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import distinct
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.asset_type_master import AssetTypeMaster
from app.schemas.asset_type_master import AssetTypeMasterResponse, AssetTypeMasterUpdate

router = APIRouter()


@router.get("/", response_model=List[AssetTypeMasterResponse])
async def get_asset_types(
    is_active: Optional[bool] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    query = db.query(AssetTypeMaster)
    if is_active is not None:
        query = query.filter(AssetTypeMaster.is_active == is_active)
    if category:
        query = query.filter(AssetTypeMaster.category == category)
    return query.order_by(AssetTypeMaster.sort_order, AssetTypeMaster.display_label).all()


@router.get("/categories", response_model=List[str])
async def get_categories(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    rows = db.query(distinct(AssetTypeMaster.category)).order_by(AssetTypeMaster.category).all()
    return [r[0] for r in rows]


@router.get("/{asset_type_id}", response_model=AssetTypeMasterResponse)
async def get_asset_type(
    asset_type_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    item = db.query(AssetTypeMaster).filter(AssetTypeMaster.id == asset_type_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset type not found")
    return item


@router.put("/{asset_type_id}", response_model=AssetTypeMasterResponse)
async def update_asset_type(
    asset_type_id: int,
    data: AssetTypeMasterUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    item = db.query(AssetTypeMaster).filter(AssetTypeMaster.id == asset_type_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset type not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item
