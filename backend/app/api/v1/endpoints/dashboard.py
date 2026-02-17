from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, List
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction, TransactionType
from app.models.alert import Alert
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/overview")
async def get_dashboard_overview(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive dashboard overview with all key metrics
    """
    # Get all active assets
    assets = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.is_active == True
    ).all()
    
    # Calculate metrics
    for asset in assets:
        asset.calculate_metrics()
    db.commit()
    
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
    recent_transactions = db.query(Transaction).join(Asset).filter(
        Asset.user_id == current_user.id
    ).order_by(Transaction.transaction_date.desc()).limit(10).all()
    
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
    monthly_investments = db.query(
        func.date_trunc('month', Transaction.transaction_date).label('month'),
        func.sum(Transaction.total_amount).label('total')
    ).join(Asset).filter(
        Asset.user_id == current_user.id,
        Transaction.transaction_type.in_([TransactionType.BUY, TransactionType.DEPOSIT]),
        Transaction.transaction_date >= six_months_ago
    ).group_by('month').order_by('month').all()
    
    return {
        "portfolio_summary": {
            "total_assets": len(assets),
            "total_invested": round(total_invested, 2),
            "total_current_value": round(total_current_value, 2),
            "total_profit_loss": round(total_profit_loss, 2),
            "total_profit_loss_percentage": round(total_profit_loss_percentage, 2)
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
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get asset allocation breakdown by type
    """
    assets = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.is_active == True
    ).all()
    
    for asset in assets:
        asset.calculate_metrics()
    db.commit()
    
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
