import logging
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db, SessionLocal
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
from app.services.price_updater import update_asset_price, PRICE_UPDATABLE_TYPES
from app.services.price_refresh_tracker import price_refresh_tracker
from app.schemas.price_refresh_progress import PriceRefreshProgress

logger = logging.getLogger(__name__)
from app.services.currency_converter import convert_usd_to_inr, get_usd_to_inr_rate
from app.models.portfolio import Portfolio
from app.models.demat_account import DematAccount
from app.models.asset_type_master import AssetTypeMaster
from app.models.alert import Alert
from app.models.portfolio_snapshot import AssetSnapshot
from app.models.mutual_fund_holding import MutualFundHolding
from app.models.transaction import Transaction, TransactionType
from app.services.xirr_service import calculate_asset_xirr

router = APIRouter()


@router.get("/", response_model=List[AssetSchema])
async def get_assets(
    asset_type: Optional[AssetType] = None,
    is_active: Optional[bool] = None,
    portfolio_id: Optional[int] = None,
    demat_account_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all assets for the current user with optional filtering
    """
    query = db.query(Asset).filter(Asset.user_id == current_user.id)

    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)

    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)

    if is_active is not None:
        query = query.filter(Asset.is_active == is_active)

    if demat_account_id is not None:
        query = query.filter(Asset.demat_account_id == demat_account_id)

    assets = query.offset(skip).limit(limit).all()
    
    # Calculate current metrics for each asset
    for asset in assets:
        asset.calculate_metrics()

    # Known default interest rates for fixed-rate asset types
    _DEFAULT_RATES = {
        AssetType.SSY: 8.2,
        AssetType.PF: 8.25,
        AssetType.PPF: 7.1,
    }

    # Lazily compute XIRR for assets that have transactions but null XIRR (skip manually set)
    null_xirr_assets = [a for a in assets if a.xirr is None and not a.xirr_manual]
    if null_xirr_assets:
        null_xirr_ids = [a.id for a in null_xirr_assets]
        all_txns = db.query(Transaction).filter(
            Transaction.asset_id.in_(null_xirr_ids)
        ).order_by(Transaction.transaction_date).all()
        txn_by_asset: dict[int, list] = {}
        for txn in all_txns:
            txn_by_asset.setdefault(txn.asset_id, []).append(txn)
        for asset in null_xirr_assets:
            asset_txns = txn_by_asset.get(asset.id, [])
            if asset_txns:
                buy_qty = sum(t.quantity or 0 for t in asset_txns if t.transaction_type == TransactionType.BUY)
                sell_qty = sum(t.quantity or 0 for t in asset_txns if t.transaction_type == TransactionType.SELL)
                if abs((buy_qty - sell_qty) - (asset.quantity or 0)) < 0.0001:
                    asset.xirr = calculate_asset_xirr(asset_txns, asset.current_value or 0)
                else:
                    asset.xirr = asset.fallback_xirr()
            else:
                asset.xirr = asset.fallback_xirr()
            # For fixed-rate asset types, fall back to default rate
            if asset.xirr is None and asset.asset_type in _DEFAULT_RATES:
                asset.xirr = _DEFAULT_RATES[asset.asset_type]

    db.commit()

    return assets


@router.get("/summary", response_model=AssetSummary)
async def get_portfolio_summary(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get portfolio summary with aggregated metrics
    """
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.is_active == True
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()
    
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


@router.get("/price-refresh-progress/{session_id}", response_model=PriceRefreshProgress)
async def get_price_refresh_progress(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get the progress of a price refresh session."""
    progress = price_refresh_tracker.get_progress(session_id)
    if not progress:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if progress.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised")
    return progress


@router.get("/price-refresh-active")
async def get_active_price_refresh(
    current_user: User = Depends(get_current_active_user),
):
    """Get the currently active price refresh session for this user, if any."""
    active = price_refresh_tracker.get_active_session(current_user.id)
    if not active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active session")
    return active


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
    asset_dict = asset_data.model_dump()

    # Crypto assets must belong to a crypto account
    if asset_dict.get('asset_type') == AssetType.CRYPTO and not asset_dict.get('crypto_account_id'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Crypto assets must belong to a crypto account. Please select a crypto account."
        )

    # Get currency from details if present (for crypto assets)
    currency = None
    if 'details' in asset_dict and asset_dict['details']:
        currency = asset_dict['details'].get('currency', 'USD')
    
    # Convert USD to INR for crypto assets if currency is USD
    if asset_dict.get('asset_type') == AssetType.CRYPTO and currency == 'USD':
        # Convert purchase_price, current_price, and total_invested from USD to INR
        if 'purchase_price' in asset_dict and asset_dict['purchase_price']:
            asset_dict['purchase_price'] = convert_usd_to_inr(asset_dict['purchase_price'])

        if 'current_price' in asset_dict and asset_dict['current_price']:
            asset_dict['current_price'] = convert_usd_to_inr(asset_dict['current_price'])

        if 'total_invested' in asset_dict and asset_dict['total_invested']:
            asset_dict['total_invested'] = convert_usd_to_inr(asset_dict['total_invested'])

    # Convert USD to INR for US stock assets (user enters USD, store INR)
    if asset_dict.get('asset_type') == AssetType.US_STOCK:
        usd_rate = get_usd_to_inr_rate()
        if 'details' not in asset_dict or not asset_dict['details']:
            asset_dict['details'] = {}
        asset_dict['details']['usd_to_inr_rate'] = usd_rate
        if 'purchase_price' in asset_dict and asset_dict['purchase_price']:
            asset_dict['details']['avg_cost_usd'] = asset_dict['purchase_price']
            asset_dict['purchase_price'] = asset_dict['purchase_price'] * usd_rate
        if 'current_price' in asset_dict and asset_dict['current_price']:
            asset_dict['details']['price_usd'] = asset_dict['current_price']
            asset_dict['current_price'] = asset_dict['current_price'] * usd_rate
        if 'total_invested' in asset_dict and asset_dict['total_invested']:
            asset_dict['details']['market_value_usd'] = asset_dict['total_invested']
            asset_dict['total_invested'] = asset_dict['total_invested'] * usd_rate

    # Convert USD to INR for ESOP/RSU/Commodity assets if currency is USD
    if asset_dict.get('asset_type') in [AssetType.ESOP, AssetType.RSU, AssetType.COMMODITY]:
        esop_currency = None
        if 'details' in asset_dict and asset_dict['details']:
            esop_currency = asset_dict['details'].get('currency', 'INR')
        if esop_currency == 'USD':
            if 'purchase_price' in asset_dict and asset_dict['purchase_price']:
                asset_dict['purchase_price'] = convert_usd_to_inr(asset_dict['purchase_price'])
            if 'current_price' in asset_dict and asset_dict['current_price']:
                asset_dict['current_price'] = convert_usd_to_inr(asset_dict['current_price'])
            if 'total_invested' in asset_dict and asset_dict['total_invested']:
                asset_dict['total_invested'] = convert_usd_to_inr(asset_dict['total_invested'])

    # Derive portfolio from demat account if provided
    if asset_dict.get('demat_account_id'):
        demat = db.query(DematAccount).filter(
            DematAccount.id == asset_dict['demat_account_id'],
            DematAccount.user_id == current_user.id,
        ).first()
        if not demat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Demat account not found."
            )
        if demat.portfolio_id:
            asset_dict['portfolio_id'] = demat.portfolio_id

    # Auto-assign to default portfolio if still not set
    if not asset_dict.get('portfolio_id'):
        default_portfolio = db.query(Portfolio).filter(
            Portfolio.user_id == current_user.id,
            Portfolio.is_default == True,
        ).first()
        if default_portfolio:
            asset_dict['portfolio_id'] = default_portfolio.id

    new_asset = Asset(
        user_id=current_user.id,
        **asset_dict
    )

    new_asset.calculate_metrics()

    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)

    # Immediately fetch the latest price for crypto assets
    if new_asset.asset_type == AssetType.CRYPTO and new_asset.symbol:
        try:
            update_asset_price(new_asset, db)
            db.refresh(new_asset)
        except Exception:
            pass  # Price update is best-effort; don't fail the creation

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

    # Validate asset type change against allowed_conversions from DB
    new_type = update_data.get('asset_type')
    if new_type and new_type != asset.asset_type:
        type_master = db.query(AssetTypeMaster).filter(
            AssetTypeMaster.name == asset.asset_type.value
        ).first()
        allowed = type_master.allowed_conversions if type_master else None
        if not allowed or new_type.value not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot change asset type from {asset.asset_type.value} to {new_type.value}"
            )

    # Convert USD to INR for crypto assets if currency is USD
    if asset.asset_type == AssetType.CRYPTO:
        details = update_data.get('details') or {}
        currency = details.get('currency', 'USD') if details else None
        if currency == 'USD':
            if 'purchase_price' in update_data and update_data['purchase_price']:
                update_data['purchase_price'] = convert_usd_to_inr(update_data['purchase_price'])
            if 'current_price' in update_data and update_data['current_price']:
                update_data['current_price'] = convert_usd_to_inr(update_data['current_price'])
            if 'total_invested' in update_data and update_data['total_invested']:
                update_data['total_invested'] = convert_usd_to_inr(update_data['total_invested'])

    # Convert USD to INR for US stock assets (user enters USD, store INR)
    if asset.asset_type == AssetType.US_STOCK:
        usd_rate = get_usd_to_inr_rate()
        details = update_data.get('details') or dict(asset.details or {})
        details['usd_to_inr_rate'] = usd_rate
        if 'purchase_price' in update_data and update_data['purchase_price']:
            details['avg_cost_usd'] = update_data['purchase_price']
            update_data['purchase_price'] = update_data['purchase_price'] * usd_rate
        if 'current_price' in update_data and update_data['current_price']:
            details['price_usd'] = update_data['current_price']
            update_data['current_price'] = update_data['current_price'] * usd_rate
        if 'total_invested' in update_data and update_data['total_invested']:
            details['market_value_usd'] = update_data['total_invested']
            update_data['total_invested'] = update_data['total_invested'] * usd_rate
        update_data['details'] = details

    # Convert USD to INR for ESOP/RSU/Commodity assets if currency is USD
    if asset.asset_type in [AssetType.ESOP, AssetType.RSU, AssetType.COMMODITY]:
        details = update_data.get('details') or dict(asset.details or {})
        esop_currency = details.get('currency', 'INR') if details else None
        if esop_currency == 'USD':
            if 'purchase_price' in update_data and update_data['purchase_price']:
                update_data['purchase_price'] = convert_usd_to_inr(update_data['purchase_price'])
            if 'current_price' in update_data and update_data['current_price']:
                update_data['current_price'] = convert_usd_to_inr(update_data['current_price'])
            if 'total_invested' in update_data and update_data['total_invested']:
                update_data['total_invested'] = convert_usd_to_inr(update_data['total_invested'])

    # If user explicitly sets XIRR, mark it as manual
    if 'xirr' in update_data and update_data['xirr'] is not None:
        update_data['xirr_manual'] = True
    elif 'xirr' in update_data and update_data['xirr'] is None and 'xirr_manual' not in update_data:
        update_data['xirr_manual'] = False

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

    # Clear FK references that lack ON DELETE CASCADE
    db.query(Alert).filter(Alert.asset_id == asset_id).update(
        {Alert.asset_id: None}, synchronize_session=False
    )
    db.query(AssetSnapshot).filter(AssetSnapshot.asset_id == asset_id).update(
        {AssetSnapshot.asset_id: None}, synchronize_session=False
    )
    db.query(MutualFundHolding).filter(MutualFundHolding.asset_id == asset_id).delete(
        synchronize_session=False
    )
    db.query(Transaction).filter(Transaction.asset_id == asset_id).delete(
        synchronize_session=False
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


@router.post("/update-all-prices", status_code=status.HTTP_202_ACCEPTED)
async def update_all_asset_prices(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Trigger async price update for all active price-updatable assets.
    Returns immediately with a session_id. Poll /price-refresh-progress/{session_id}.
    """
    # Prevent concurrent sessions for the same user
    active = price_refresh_tracker.get_active_session(current_user.id)
    if active:
        return {
            "message": "Price refresh already in progress",
            "session_id": active.session_id,
            "total_assets": active.total_assets,
            "status": "already_running",
        }

    assets = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.is_active == True,
        Asset.asset_type.in_(PRICE_UPDATABLE_TYPES),
    ).all()

    if not assets:
        return {"message": "No price-updatable assets found", "total_assets": 0}

    session_id = price_refresh_tracker.create_session(current_user.id, assets)
    asset_ids = [a.id for a in assets]

    def _update_prices():
        bg_db = SessionLocal()
        try:
            bg_assets = bg_db.query(Asset).filter(Asset.id.in_(asset_ids)).all()
            for asset in bg_assets:
                price_refresh_tracker.set_asset_processing(session_id, asset.id)
                success = update_asset_price(asset, bg_db)
                if success:
                    price_refresh_tracker.update_asset_status(
                        session_id, asset.id, "completed"
                    )
                else:
                    price_refresh_tracker.update_asset_status(
                        session_id, asset.id, "error",
                        error_message=asset.price_update_error,
                    )
            price_refresh_tracker.complete_session(session_id)
        except Exception as exc:
            logger.error(f"Error in background price refresh: {exc}")
            price_refresh_tracker.fail_session(session_id, str(exc))
        finally:
            bg_db.close()

    background_tasks.add_task(_update_prices)

    return {
        "message": "Price refresh started in background",
        "session_id": session_id,
        "total_assets": len(assets),
        "status": "processing",
    }

# Made with Bob
