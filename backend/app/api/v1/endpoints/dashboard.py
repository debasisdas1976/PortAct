from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.asset import Asset, AssetType
from app.models.bank_account import BankAccount
from app.models.demat_account import DematAccount
from app.models.crypto_account import CryptoAccount
from app.models.transaction import Transaction, TransactionType
from app.models.alert import Alert
from app.models.portfolio_snapshot import PortfolioSnapshot, AssetSnapshot
from app.services.xirr_service import calculate_asset_xirr
from datetime import datetime, timedelta, date

router = APIRouter()


@router.get("/overview")
async def get_dashboard_overview(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive dashboard overview with all key metrics.
    Optionally filtered by portfolio_id.
    """
    # Get all active assets
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.is_active == True
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()
    
    # Calculate metrics in-memory only (no commit — avoids overwriting
    # fresh prices set by the price_updater running concurrently)
    for asset in assets:
        asset.calculate_metrics()

    # Portfolio summary
    total_invested = sum(asset.total_invested for asset in assets)
    total_current_value = sum(asset.current_value for asset in assets)
    total_profit_loss = total_current_value - total_invested
    total_profit_loss_percentage = (
        (total_profit_loss / total_invested * 100) if total_invested > 0 else 0
    )
    
    # Assets by type
    assets_by_type = {}
    value_by_type = {}
    for asset_type in AssetType:
        type_assets = [a for a in assets if a.asset_type == asset_type]
        if type_assets:
            assets_by_type[asset_type.value] = len(type_assets)
            value_by_type[asset_type.value] = sum(a.current_value for a in type_assets)
    
    # Recent transactions
    recent_txn_query = db.query(Transaction).join(Asset).filter(
        Asset.user_id == current_user.id
    )
    if portfolio_id is not None:
        recent_txn_query = recent_txn_query.filter(Asset.portfolio_id == portfolio_id)
    recent_transactions = recent_txn_query.order_by(Transaction.transaction_date.desc()).limit(10).all()
    
    # Unread alerts
    unread_alerts_count = db.query(Alert).filter(
        Alert.user_id == current_user.id,
        Alert.is_read == False,
        Alert.is_dismissed == False
    ).count()
    
    # Top performers (by profit/loss percentage)
    top_performers = sorted(
        [a for a in assets if a.profit_loss_percentage > 0],
        key=lambda x: x.profit_loss_percentage,
        reverse=True
    )[:5]
    
    # Bottom performers
    bottom_performers = sorted(
        [a for a in assets if a.profit_loss_percentage < 0],
        key=lambda x: x.profit_loss_percentage
    )[:5]
    
    # Monthly investment trend (last 6 months)
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    monthly_inv_query = db.query(
        func.date_trunc('month', Transaction.transaction_date).label('month'),
        func.sum(Transaction.total_amount).label('total')
    ).join(Asset).filter(
        Asset.user_id == current_user.id,
        Transaction.transaction_type.in_([TransactionType.BUY, TransactionType.DEPOSIT]),
        Transaction.transaction_date >= six_months_ago
    )
    if portfolio_id is not None:
        monthly_inv_query = monthly_inv_query.filter(Asset.portfolio_id == portfolio_id)
    monthly_investments = monthly_inv_query.group_by('month').order_by('month').all()
    
    # Calculate portfolio XIRR as investment-weighted average of per-asset XIRRs
    # (same approach as Assets Overview page)
    _DEFAULT_RATES_SUMMARY = {
        AssetType.SSY: 8.2,
        AssetType.PF: 8.25,
        AssetType.PPF: 7.1,
    }

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
            if asset.xirr is None and asset.asset_type in _DEFAULT_RATES_SUMMARY:
                asset.xirr = _DEFAULT_RATES_SUMMARY[asset.asset_type]

    xirr_weighted_sum = 0.0
    xirr_weight_total = 0.0
    for asset in assets:
        if asset.xirr is not None:
            weight = (asset.total_invested if (asset.total_invested or 0) > 0
                      else (asset.current_value if (asset.current_value or 0) > 0 else 0))
            if weight > 0:
                xirr_weighted_sum += asset.xirr * weight
                xirr_weight_total += weight
    portfolio_xirr = round(xirr_weighted_sum / xirr_weight_total, 2) if xirr_weight_total > 0 else None

    return {
        "portfolio_summary": {
            "total_assets": len(assets),
            "total_invested": round(total_invested, 2),
            "total_current_value": round(total_current_value, 2),
            "total_profit_loss": round(total_profit_loss, 2),
            "total_profit_loss_percentage": round(total_profit_loss_percentage, 2),
            "portfolio_xirr": portfolio_xirr,
        },
        "assets_by_type": assets_by_type,
        "value_by_type": {k: round(v, 2) for k, v in value_by_type.items()},
        "recent_transactions": [
            {
                "id": t.id,
                "asset_id": t.asset_id,
                "type": t.transaction_type.value,
                "amount": t.total_amount,
                "date": t.transaction_date.isoformat()
            }
            for t in recent_transactions
        ],
        "unread_alerts": unread_alerts_count,
        "top_performers": [
            {
                "id": a.id,
                "name": a.name,
                "type": a.asset_type.value,
                "profit_loss_percentage": round(a.profit_loss_percentage, 2),
                "current_value": round(a.current_value, 2)
            }
            for a in top_performers
        ],
        "bottom_performers": [
            {
                "id": a.id,
                "name": a.name,
                "type": a.asset_type.value,
                "profit_loss_percentage": round(a.profit_loss_percentage, 2),
                "current_value": round(a.current_value, 2)
            }
            for a in bottom_performers
        ],
        "monthly_investment_trend": [
            {
                "month": m.month.isoformat() if m.month else None,
                "total": round(float(m.total), 2) if m.total else 0
            }
            for m in monthly_investments
        ]
    }


@router.get("/asset-allocation")
async def get_asset_allocation(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get asset allocation breakdown by type.
    Optionally filtered by portfolio_id.
    """
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.is_active == True
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()
    
    for asset in assets:
        asset.calculate_metrics()

    total_value = sum(asset.current_value for asset in assets)
    
    allocation = {}
    for asset_type in AssetType:
        type_assets = [a for a in assets if a.asset_type == asset_type]
        if type_assets:
            type_value = sum(a.current_value for a in type_assets)
            allocation[asset_type.value] = {
                "value": round(type_value, 2),
                "percentage": round((type_value / total_value * 100) if total_value > 0 else 0, 2),
                "count": len(type_assets)
            }
    
    return {
        "total_value": round(total_value, 2),
        "allocation": allocation
    }

# Made with Bob



@router.get("/portfolio-performance")
async def get_portfolio_performance(
    days: int = Query(default=30, ge=1, le=365),
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get portfolio performance history over time.
    Returns daily snapshots for the specified number of days.
    When portfolio_id is provided, computes from asset-level snapshots.
    """
    start_date = date.today() - timedelta(days=days)

    if portfolio_id is not None:
        # Compute from AssetSnapshot joined to Asset filtered by portfolio_id
        rows = (
            db.query(
                AssetSnapshot.snapshot_date,
                func.sum(AssetSnapshot.total_invested).label("total_invested"),
                func.sum(AssetSnapshot.current_value).label("total_current_value"),
                func.sum(AssetSnapshot.profit_loss).label("total_profit_loss"),
                func.count(AssetSnapshot.id).label("total_assets_count"),
            )
            .outerjoin(Asset, AssetSnapshot.asset_id == Asset.id)
            .outerjoin(BankAccount, AssetSnapshot.bank_account_id == BankAccount.id)
            .outerjoin(DematAccount, AssetSnapshot.demat_account_id == DematAccount.id)
            .outerjoin(CryptoAccount, AssetSnapshot.crypto_account_id == CryptoAccount.id)
            .filter(
                AssetSnapshot.snapshot_date >= start_date,
                or_(
                    (Asset.user_id == current_user.id) & (Asset.portfolio_id == portfolio_id),
                    (BankAccount.user_id == current_user.id) & (BankAccount.portfolio_id == portfolio_id),
                    (DematAccount.user_id == current_user.id) & (DematAccount.portfolio_id == portfolio_id),
                    (CryptoAccount.user_id == current_user.id) & (CryptoAccount.portfolio_id == portfolio_id),
                ),
            )
            .group_by(AssetSnapshot.snapshot_date)
            .order_by(AssetSnapshot.snapshot_date)
            .all()
        )
        snapshots_data = []
        for row in rows:
            invested = row.total_invested or 0
            current_val = row.total_current_value or 0
            pl = row.total_profit_loss or 0
            pl_pct = (pl / invested * 100) if invested else 0
            snapshots_data.append({
                "date": row.snapshot_date.isoformat(),
                "total_invested": round(invested, 2),
                "total_current_value": round(current_val, 2),
                "total_profit_loss": round(pl, 2),
                "total_profit_loss_percentage": round(pl_pct, 2),
                "total_assets_count": row.total_assets_count,
            })
        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": date.today().isoformat(),
            "snapshots": snapshots_data,
        }

    # No portfolio filter — use user-level PortfolioSnapshot
    snapshots = db.query(PortfolioSnapshot).filter(
        PortfolioSnapshot.user_id == current_user.id,
        PortfolioSnapshot.snapshot_date >= start_date
    ).order_by(PortfolioSnapshot.snapshot_date).all()

    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": date.today().isoformat(),
        "snapshots": [
            {
                "date": s.snapshot_date.isoformat(),
                "total_invested": round(s.total_invested or 0, 2),
                "total_current_value": round(s.total_current_value or 0, 2),
                "total_profit_loss": round(s.total_profit_loss or 0, 2),
                "total_profit_loss_percentage": round(s.total_profit_loss_percentage or 0, 2),
                "total_assets_count": s.total_assets_count or 0
            }
            for s in snapshots
        ]
    }


@router.get("/asset-performance/{asset_id}")
async def get_asset_performance(
    asset_id: int,
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get performance history for a specific asset.
    Returns daily snapshots for the specified number of days.
    """
    # Verify asset belongs to user
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    start_date = date.today() - timedelta(days=days)
    
    asset_snapshots = db.query(AssetSnapshot).filter(
        AssetSnapshot.asset_id == asset_id,
        AssetSnapshot.snapshot_date >= start_date
    ).order_by(AssetSnapshot.snapshot_date).all()
    
    return {
        "asset_id": asset_id,
        "asset_name": asset.name,
        "asset_type": asset.asset_type.value,
        "asset_symbol": asset.symbol,
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": date.today().isoformat(),
        "snapshots": [
            {
                "date": s.snapshot_date.isoformat(),
                "quantity": s.quantity or 0,
                "current_price": round(s.current_price or 0, 2),
                "total_invested": round(s.total_invested or 0, 2),
                "current_value": round(s.current_value or 0, 2),
                "profit_loss": round(s.profit_loss or 0, 2),
                "profit_loss_percentage": round(s.profit_loss_percentage or 0, 2)
            }
            for s in asset_snapshots
        ]
    }


@router.get("/assets-list")
async def get_assets_list(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a list of all active assets for the user.
    Used for asset selection in performance charts.
    Optionally filtered by portfolio_id.
    """
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.is_active == True
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.order_by(Asset.name).all()

    for asset in assets:
        asset.calculate_metrics()

    return {
        "assets": [
            {
                "id": a.id,
                "name": a.name,
                "symbol": a.symbol,
                "type": a.asset_type.value,
                "current_value": round(a.current_value, 2)
            }
            for a in assets
        ]
    }


@router.get("/asset-type-xirr")
async def get_asset_type_xirr(
    asset_type: AssetType,
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Calculate aggregate XIRR for all active assets of a specific asset type.
    Uses investment-weighted average of per-asset XIRR values (stored in assets.xirr).
    Only assets with a non-null xirr and positive total_invested are included.
    """
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == asset_type,
        Asset.is_active == True
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()

    if not assets:
        return {"asset_type": asset_type.value, "xirr": None,
                "asset_count": 0, "total_invested": 0, "total_current_value": 0}

    # Known default interest rates for fixed-rate asset types
    _DEFAULT_RATES = {
        AssetType.SSY: 8.2,
        AssetType.PF: 8.25,
        AssetType.PPF: 7.1,
    }

    for asset in assets:
        asset.calculate_metrics()
        if asset.xirr is None and not asset.xirr_manual:
            asset.xirr = asset.fallback_xirr()
            # For fixed-rate asset types, fall back to default rate
            if asset.xirr is None and asset_type in _DEFAULT_RATES:
                asset.xirr = _DEFAULT_RATES[asset_type]
    db.commit()

    total_invested = sum(a.total_invested or 0 for a in assets)
    total_current_value = sum(a.current_value or 0 for a in assets)

    # Use per-asset XIRR values (investment-weighted average).
    # Fall back to current_value as weight when total_invested is 0
    # (common for SSY, insurance, and other non-market assets).
    weighted_sum = 0.0
    weight_total = 0.0
    for asset in assets:
        if asset.xirr is not None:
            weight = (asset.total_invested if asset.total_invested and asset.total_invested > 0
                      else (asset.current_value if asset.current_value and asset.current_value > 0
                            else 0))
            if weight > 0:
                weighted_sum += asset.xirr * weight
                weight_total += weight

    xirr_value = round(weighted_sum / weight_total, 2) if weight_total > 0 else None

    return {
        "asset_type": asset_type.value,
        "xirr": xirr_value,
        "asset_count": len(assets),
        "total_invested": round(total_invested, 2),
        "total_current_value": round(total_current_value, 2),
    }


@router.post("/take-snapshot")
async def take_manual_snapshot(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger a portfolio snapshot for the current user.
    Useful for testing or capturing snapshots on-demand.
    """
    from app.services.eod_snapshot_service import EODSnapshotService
    from datetime import date
    
    try:
        snapshot = EODSnapshotService.capture_snapshot(db, current_user.id, date.today())
        
        return {
            "success": True,
            "message": "Snapshot captured successfully",
            "snapshot": {
                "date": snapshot.snapshot_date.isoformat(),
                "total_invested": round(snapshot.total_invested, 2),
                "total_current_value": round(snapshot.total_current_value, 2),
                "total_profit_loss": round(snapshot.total_profit_loss, 2),
                "total_profit_loss_percentage": round(snapshot.total_profit_loss_percentage, 2),
                "total_assets_count": snapshot.total_assets_count
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to capture snapshot: {str(e)}"
        }

# Made with Bob
