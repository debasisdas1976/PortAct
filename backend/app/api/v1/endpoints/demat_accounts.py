from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.demat_account import DematAccount, BrokerName
from app.models.asset import Asset, AssetType
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
    broker_name: Optional[BrokerName] = None,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all demat accounts for the current user with optional filtering and asset statistics
    """
    query = db.query(DematAccount).filter(DematAccount.user_id == current_user.id)
    
    if broker_name:
        query = query.filter(DematAccount.broker_name == broker_name)
    
    if is_active is not None:
        query = query.filter(DematAccount.is_active == is_active)
    
    accounts = query.offset(skip).limit(limit).all()
    
    # Add asset statistics to each account
    result = []
    for account in accounts:
        assets = db.query(Asset).filter(
            Asset.demat_account_id == account.id,
            Asset.is_active == True
        ).all()
        
        asset_count = len(assets)
        total_invested = sum(asset.total_invested for asset in assets)
        current_value = sum(asset.current_value for asset in assets)
        total_profit_loss = current_value - total_invested
        
        account_dict = {
            **account.__dict__,
            "asset_count": asset_count,
            "total_invested": total_invested,
            "current_value": current_value,
            "total_profit_loss": total_profit_loss
        }
        result.append(DematAccountWithAssets(**account_dict))
    
    return result


@router.get("/summary", response_model=DematAccountSummary)
async def get_demat_accounts_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get summary of all demat accounts with portfolio statistics
    """
    accounts = db.query(DematAccount).filter(
        DematAccount.user_id == current_user.id,
        DematAccount.is_active == True
    ).all()
    
    total_cash_balance = sum(acc.cash_balance for acc in accounts)
    
    # Get asset statistics for all demat accounts
    total_invested = 0.0
    total_current_value = 0.0
    
    for account in accounts:
        assets = db.query(Asset).filter(
            Asset.demat_account_id == account.id,
            Asset.is_active == True
        ).all()
        
        for asset in assets:
            total_invested += asset.total_invested
            total_current_value += asset.current_value
    
    total_profit_loss = total_current_value - total_invested
    
    accounts_by_broker = {}
    for account in accounts:
        broker_key = account.broker_name.value
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
    from app.services.currency_converter import get_usd_to_inr_rate
    
    # Check if account already exists
    existing = db.query(DematAccount).filter(
        DematAccount.user_id == current_user.id,
        DematAccount.account_id == account_data.account_id,
        DematAccount.broker_name == account_data.broker_name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Demat account with this account ID already exists for this broker"
        )
    
    # If this is set as primary, unset other primary accounts
    if account_data.is_primary:
        db.query(DematAccount).filter(
            DematAccount.user_id == current_user.id,
            DematAccount.is_primary == True
        ).update({"is_primary": False})
    
    account_dict = account_data.model_dump()
    
    # Handle USD to INR conversion for US brokers
    if account_data.broker_name in [BrokerName.VESTED, BrokerName.INDMONEY]:
        account_dict['currency'] = 'USD'
        if account_data.cash_balance_usd is not None:
            # User provided USD amount, convert to INR
            usd_to_inr = get_usd_to_inr_rate()
            account_dict['cash_balance'] = account_data.cash_balance_usd * usd_to_inr
        elif account_data.cash_balance > 0:
            # User provided INR amount (shouldn't happen with proper UI), treat as USD
            usd_to_inr = get_usd_to_inr_rate()
            account_dict['cash_balance_usd'] = account_data.cash_balance / usd_to_inr
    else:
        account_dict['currency'] = 'INR'
    
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
    from app.services.currency_converter import get_usd_to_inr_rate
    
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
    
    # Handle USD to INR conversion for US brokers
    if account.broker_name in [BrokerName.VESTED, BrokerName.INDMONEY]:
        if 'cash_balance_usd' in update_data and update_data['cash_balance_usd'] is not None:
            # User updated USD amount, convert to INR
            usd_to_inr = get_usd_to_inr_rate()
            update_data['cash_balance'] = update_data['cash_balance_usd'] * usd_to_inr
        elif 'cash_balance' in update_data and update_data['cash_balance'] is not None:
            # User updated INR amount (shouldn't happen with proper UI), calculate USD
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
    
    db.delete(account)
    db.commit()
    
    return None

# Made with Bob