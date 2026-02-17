from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.asset import Asset, AssetType
from app.schemas.asset import (
    Asset as AssetSchema,
    AssetCreate,
    AssetUpdate,
    AssetWithTransactions,
    AssetSummary
)
from app.services.price_updater import update_asset_price

router = APIRouter()


@router.get("/", response_model=List[AssetSchema])
async def get_assets(
    asset_type: Optional[AssetType] = None,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all assets for the current user with optional filtering
    """
    query = db.query(Asset).filter(Asset.user_id == current_user.id)
    
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    
    if is_active is not None:
        query = query.filter(Asset.is_active == is_active)
    
    assets = query.offset(skip).limit(limit).all()
    
    # Calculate current metrics for each asset
    for asset in assets:
        asset.calculate_metrics()
    
    db.commit()
    
    return assets


@router.get("/summary", response_model=AssetSummary)
async def get_portfolio_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get portfolio summary with aggregated metrics
    """
    assets = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.is_active == True
    ).all()
    
    # Calculate metrics
    for asset in assets:
        asset.calculate_metrics()
    db.commit()
    
    total_invested = sum(asset.total_invested for asset in assets)
    total_current_value = sum(asset.current_value for asset in assets)
    total_profit_loss = total_current_value - total_invested
    total_profit_loss_percentage = (
        (total_profit_loss / total_invested * 100) if total_invested > 0 else 0
    )
    
    # Count assets by type
    assets_by_type = {}
    for asset_type in AssetType:
        count = len([a for a in assets if a.asset_type == asset_type])
        if count > 0:
            assets_by_type[asset_type.value] = count
    
    return AssetSummary(
        total_assets=len(assets),
        total_invested=total_invested,
        total_current_value=total_current_value,
        total_profit_loss=total_profit_loss,
        total_profit_loss_percentage=total_profit_loss_percentage,
        assets_by_type=assets_by_type
    )


@router.get("/{asset_id}", response_model=AssetSchema)
async def get_asset(
    asset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific asset by ID
    """
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    asset.calculate_metrics()
    db.commit()
    
    return asset


@router.post("/", response_model=AssetSchema, status_code=status.HTTP_201_CREATED)
async def create_asset(
    asset_data: AssetCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new asset
    """
    new_asset = Asset(
        user_id=current_user.id,
        **asset_data.model_dump()
    )
    
    new_asset.calculate_metrics()
    
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)
    
    return new_asset


@router.put("/{asset_id}", response_model=AssetSchema)
async def update_asset(
    asset_id: int,
    asset_update: AssetUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing asset
    """
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Update fields
    update_data = asset_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(asset, field, value)
    
    asset.calculate_metrics()
    
    db.commit()
    db.refresh(asset)
    
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete an asset
    """
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    db.delete(asset)
    db.commit()
    
    return None


@router.post("/{asset_id}/update-price", response_model=AssetSchema)
async def manually_update_asset_price(
    asset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger price update for a specific asset
    """
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Attempt to update the price
    success = update_asset_price(asset, db)
    
    if not success:
        # Return the asset with error information
        db.refresh(asset)
        return asset
    
    # Return updated asset
    db.refresh(asset)
    return asset


@router.post("/update-all-prices")
async def update_all_asset_prices(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger price update for all active assets
    """
    assets = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.is_active == True
    ).all()
    
    updated_count = 0
    failed_count = 0
    failed_assets = []
    
    for asset in assets:
        if update_asset_price(asset, db):
            updated_count += 1
        else:
            failed_count += 1
            failed_assets.append({
                "id": asset.id,
                "name": asset.name,
                "symbol": asset.symbol,
                "error": asset.price_update_error
            })
    
    return {
        "updated": updated_count,
        "failed": failed_count,
        "failed_assets": failed_assets,
        "total": len(assets)
    }

# Made with Bob
