from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.asset_category_master import AssetCategoryMaster
from app.schemas.asset_category_master import AssetCategoryMasterResponse, AssetCategoryMasterUpdate

router = APIRouter()


@router.get("/", response_model=List[AssetCategoryMasterResponse])
async def get_asset_categories(
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    query = db.query(AssetCategoryMaster)
    if is_active is not None:
        query = query.filter(AssetCategoryMaster.is_active == is_active)
    return query.order_by(AssetCategoryMaster.sort_order, AssetCategoryMaster.display_label).all()


@router.get("/{category_id}", response_model=AssetCategoryMasterResponse)
async def get_asset_category(
    category_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    item = db.query(AssetCategoryMaster).filter(AssetCategoryMaster.id == category_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset category not found")
    return item


@router.put("/{category_id}", response_model=AssetCategoryMasterResponse)
async def update_asset_category(
    category_id: int,
    data: AssetCategoryMasterUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    item = db.query(AssetCategoryMaster).filter(AssetCategoryMaster.id == category_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset category not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item
