from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.api.dependencies import get_current_active_user, get_default_portfolio_id
from app.services.currency_converter import get_usd_to_inr_rate
from app.models.user import User
from app.models.demat_account import DematAccount, AccountMarket
from app.models.asset import Asset, AssetType
from app.models.alert import Alert
from app.models.portfolio_snapshot import AssetSnapshot
from app.models.mutual_fund_holding import MutualFundHolding
from app.models.transaction import Transaction
from app.schemas.demat_account import (
    DematAccount as DematAccountSchema,
    DematAccountCreate,
    DematAccountUpdate,
    DematAccountWithAssets,
    DematAccountSummary
)

router = APIRouter()


@router.get("/", response_model=List[DematAccountWithAssets])
async def get_demat_accounts(
    broker_name: Optional[str] = None,
    is_active: Optional[bool] = None,
    portfolio_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all demat accounts for the current user with optional filtering and asset statistics
    """
    query = db.query(DematAccount).filter(DematAccount.user_id == current_user.id)

    if portfolio_id is not None:
        query = query.filter(DematAccount.portfolio_id == portfolio_id)

    if broker_name:
        query = query.filter(DematAccount.broker_name == broker_name)

    if is_active is not None:
        query = query.filter(DematAccount.is_active == is_active)

    accounts = query.offset(skip).limit(limit).all()

    if not accounts:
        return []

    # Batch-load asset statistics for all accounts in a single query
    account_ids = [account.id for account in accounts]
    asset_stats = db.query(
        Asset.demat_account_id,
        func.count(Asset.id).label("asset_count"),
        func.coalesce(func.sum(Asset.total_invested), 0.0).label("total_invested"),
        func.coalesce(func.sum(Asset.current_value), 0.0).label("current_value"),
    ).filter(
        Asset.demat_account_id.in_(account_ids),
        Asset.is_active == True
    ).group_by(Asset.demat_account_id).all()

    # Build a lookup dict keyed by demat_account_id
    stats_map = {
        row.demat_account_id: {
            "asset_count": row.asset_count,
            "total_invested": float(row.total_invested),
            "current_value": float(row.current_value),
            "total_profit_loss": float(row.current_value) - float(row.total_invested),
        }
        for row in asset_stats
    }

    default_stats = {
        "asset_count": 0,
        "total_invested": 0.0,
        "current_value": 0.0,
        "total_profit_loss": 0.0,
    }

    result = []
    for account in accounts:
        stats = stats_map.get(account.id, default_stats)
        account_dict = {
            **account.__dict__,
            **stats,
        }
        result.append(DematAccountWithAssets(**account_dict))

    return result


@router.get("/summary", response_model=DematAccountSummary)
async def get_demat_accounts_summary(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get summary of all demat accounts with portfolio statistics
    """
    query = db.query(DematAccount).filter(
        DematAccount.user_id == current_user.id,
        DematAccount.is_active == True
    )
    if portfolio_id is not None:
        query = query.filter(DematAccount.portfolio_id == portfolio_id)
    accounts = query.all()

    total_cash_balance = sum(acc.cash_balance for acc in accounts)

    # Get asset statistics for all demat accounts in a single query
    account_ids = [acc.id for acc in accounts]
    if account_ids:
        totals = db.query(
            func.coalesce(func.sum(Asset.total_invested), 0.0).label("total_invested"),
            func.coalesce(func.sum(Asset.current_value), 0.0).label("current_value"),
        ).filter(
            Asset.demat_account_id.in_(account_ids),
            Asset.is_active == True
        ).first()
        total_invested = float(totals.total_invested)
        total_current_value = float(totals.current_value)
    else:
        total_invested = 0.0
        total_current_value = 0.0

    total_profit_loss = total_current_value - total_invested
    
    accounts_by_broker = {}
    for account in accounts:
        broker_key = account.broker_name
        accounts_by_broker[broker_key] = accounts_by_broker.get(broker_key, 0) + 1
    
    return DematAccountSummary(
        total_accounts=len(accounts),
        total_cash_balance=total_cash_balance,
        total_invested=total_invested,
        total_current_value=total_current_value,
        total_profit_loss=total_profit_loss,
        accounts_by_broker=accounts_by_broker
    )


@router.get("/{account_id}", response_model=DematAccountWithAssets)
async def get_demat_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific demat account by ID with asset statistics
    """
    account = db.query(DematAccount).filter(
        DematAccount.id == account_id,
        DematAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demat account not found"
        )
    
    # Get asset statistics
    asset_count = db.query(func.count(Asset.id)).filter(
        Asset.demat_account_id == account_id,
        Asset.is_active == True
    ).scalar()
    
    assets = db.query(Asset).filter(
        Asset.demat_account_id == account_id,
        Asset.is_active == True
    ).all()
    
    total_invested = sum(asset.total_invested for asset in assets)
    current_value = sum(asset.current_value for asset in assets)
    total_profit_loss = current_value - total_invested
    
    # Convert to dict and add statistics
    account_dict = {
        **account.__dict__,
        "asset_count": asset_count,
        "total_invested": total_invested,
        "current_value": current_value,
        "total_profit_loss": total_profit_loss
    }
    
    return DematAccountWithAssets(**account_dict)


@router.post("/", response_model=DematAccountSchema, status_code=status.HTTP_201_CREATED)
async def create_demat_account(
    account_data: DematAccountCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new demat account
    """
    # Resolve portfolio_id early so we can use it in the uniqueness check
    portfolio_id = account_data.portfolio_id or get_default_portfolio_id(current_user.id, db)

    # Check if account already exists in this portfolio
    existing = db.query(DematAccount).filter(
        DematAccount.user_id == current_user.id,
        DematAccount.account_id == account_data.account_id,
        DematAccount.broker_name == account_data.broker_name,
        DematAccount.portfolio_id == portfolio_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Demat account with this account ID already exists for this broker in this portfolio"
        )
    
    # If this is set as primary, unset other primary accounts
    if account_data.is_primary:
        db.query(DematAccount).filter(
            DematAccount.user_id == current_user.id,
            DematAccount.is_primary == True
        ).update({"is_primary": False})
    
    account_dict = account_data.model_dump()
    
    # Handle USD to INR conversion for international accounts
    if account_data.account_market == AccountMarket.INTERNATIONAL:
        account_dict['currency'] = 'USD'
        if account_data.cash_balance_usd is not None:
            # User provided USD amount, convert to INR
            usd_to_inr = get_usd_to_inr_rate()
            account_dict['cash_balance'] = account_data.cash_balance_usd * usd_to_inr
        elif account_data.cash_balance > 0:
            # User provided INR amount, calculate USD equivalent
            usd_to_inr = get_usd_to_inr_rate()
            account_dict['cash_balance_usd'] = account_data.cash_balance / usd_to_inr
    else:
        account_dict['currency'] = 'INR'
    
    # Use the already-resolved portfolio_id
    account_dict['portfolio_id'] = portfolio_id

    account = DematAccount(
        **account_dict,
        user_id=current_user.id
    )

    db.add(account)
    db.commit()
    db.refresh(account)

    return account


@router.put("/{account_id}", response_model=DematAccountSchema)
async def update_demat_account(
    account_id: int,
    account_data: DematAccountUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update a demat account
    """
    account = db.query(DematAccount).filter(
        DematAccount.id == account_id,
        DematAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demat account not found"
        )
    
    # If setting as primary, unset other primary accounts
    if account_data.is_primary and not account.is_primary:
        db.query(DematAccount).filter(
            DematAccount.user_id == current_user.id,
            DematAccount.is_primary == True
        ).update({"is_primary": False})
    
    # Update fields
    update_data = account_data.model_dump(exclude_unset=True)
    
    # Handle USD to INR conversion for international accounts
    effective_market = update_data.get('account_market', account.account_market)
    if effective_market == AccountMarket.INTERNATIONAL or (isinstance(effective_market, str) and effective_market == 'INTERNATIONAL'):
        if 'cash_balance_usd' in update_data and update_data['cash_balance_usd'] is not None:
            # User updated USD amount, convert to INR
            usd_to_inr = get_usd_to_inr_rate()
            update_data['cash_balance'] = update_data['cash_balance_usd'] * usd_to_inr
        elif 'cash_balance' in update_data and update_data['cash_balance'] is not None:
            # User updated INR amount, calculate USD
            usd_to_inr = get_usd_to_inr_rate()
            update_data['cash_balance_usd'] = update_data['cash_balance'] / usd_to_inr
    
    for field, value in update_data.items():
        setattr(account, field, value)
    
    db.commit()
    db.refresh(account)
    
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_demat_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a demat account (will also delete all associated assets)
    """
    account = db.query(DematAccount).filter(
        DematAccount.id == account_id,
        DematAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demat account not found"
        )

    # Get all asset IDs linked to this demat account
    asset_ids = [a.id for a in db.query(Asset.id).filter(
        Asset.demat_account_id == account.id
    ).all()]

    if asset_ids:
        # Clear FK references that lack ON DELETE CASCADE
        db.query(Alert).filter(Alert.asset_id.in_(asset_ids)).update(
            {Alert.asset_id: None}, synchronize_session=False
        )
        db.query(AssetSnapshot).filter(AssetSnapshot.asset_id.in_(asset_ids)).update(
            {AssetSnapshot.asset_id: None}, synchronize_session=False
        )
        db.query(MutualFundHolding).filter(MutualFundHolding.asset_id.in_(asset_ids)).delete(
            synchronize_session=False
        )
        # Delete transactions referencing the assets
        db.query(Transaction).filter(Transaction.asset_id.in_(asset_ids)).delete(
            synchronize_session=False
        )
        # Delete the assets themselves
        db.query(Asset).filter(Asset.demat_account_id == account.id).delete(
            synchronize_session=False
        )

    db.delete(account)
    db.commit()

    return None

# Made with Bob