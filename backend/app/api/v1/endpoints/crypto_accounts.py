from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.crypto_account import CryptoAccount
from app.models.crypto_exchange import CryptoExchangeMaster
from app.models.asset import Asset, AssetType
from app.schemas.crypto_account import (
    CryptoAccount as CryptoAccountSchema,
    CryptoAccountCreate,
    CryptoAccountUpdate,
    CryptoAccountWithAssets,
    CryptoAccountSummary
)

router = APIRouter()


@router.get("/", response_model=List[CryptoAccountWithAssets])
async def get_crypto_accounts(
    exchange_name: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all crypto accounts for the current user with optional filtering and asset statistics
    """
    query = db.query(CryptoAccount).filter(CryptoAccount.user_id == current_user.id)
    
    if exchange_name:
        query = query.filter(CryptoAccount.exchange_name == exchange_name)
    
    if is_active is not None:
        query = query.filter(CryptoAccount.is_active == is_active)
    
    accounts = query.offset(skip).limit(limit).all()
    
    # Add asset statistics to each account
    result = []
    for account in accounts:
        assets = db.query(Asset).filter(
            Asset.crypto_account_id == account.id,
            Asset.asset_type == AssetType.CRYPTO,
            Asset.is_active == True
        ).all()
        
        asset_count = len(assets)
        total_invested_usd = sum(asset.total_invested for asset in assets)
        current_value_usd = sum(asset.current_value for asset in assets)
        total_profit_loss_usd = current_value_usd - total_invested_usd
        
        account_dict = {
            **account.__dict__,
            "asset_count": asset_count,
            "total_invested_usd": total_invested_usd,
            "current_value_usd": current_value_usd,
            "total_profit_loss_usd": total_profit_loss_usd
        }
        result.append(CryptoAccountWithAssets(**account_dict))
    
    return result


@router.get("/summary", response_model=CryptoAccountSummary)
async def get_crypto_accounts_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get summary of all crypto accounts with portfolio statistics
    """
    accounts = db.query(CryptoAccount).filter(
        CryptoAccount.user_id == current_user.id,
        CryptoAccount.is_active == True
    ).all()
    
    total_cash_balance_usd = sum(acc.cash_balance_usd for acc in accounts)
    
    # Get asset statistics for all crypto accounts
    total_invested_usd = 0.0
    total_current_value_usd = 0.0
    
    for account in accounts:
        assets = db.query(Asset).filter(
            Asset.crypto_account_id == account.id,
            Asset.asset_type == AssetType.CRYPTO,
            Asset.is_active == True
        ).all()
        
        for asset in assets:
            total_invested_usd += asset.total_invested
            total_current_value_usd += asset.current_value
    
    total_profit_loss_usd = total_current_value_usd - total_invested_usd
    
    accounts_by_exchange = {}
    for account in accounts:
        exchange_key = account.exchange_name
        accounts_by_exchange[exchange_key] = accounts_by_exchange.get(exchange_key, 0) + 1
    
    return CryptoAccountSummary(
        total_accounts=len(accounts),
        total_cash_balance_usd=total_cash_balance_usd,
        total_invested_usd=total_invested_usd,
        total_current_value_usd=total_current_value_usd,
        total_profit_loss_usd=total_profit_loss_usd,
        accounts_by_exchange=accounts_by_exchange
    )


@router.get("/{account_id}", response_model=CryptoAccountWithAssets)
async def get_crypto_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific crypto account by ID with asset statistics
    """
    account = db.query(CryptoAccount).filter(
        CryptoAccount.id == account_id,
        CryptoAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crypto account not found"
        )
    
    # Get asset statistics
    asset_count = db.query(func.count(Asset.id)).filter(
        Asset.crypto_account_id == account_id,
        Asset.asset_type == AssetType.CRYPTO,
        Asset.is_active == True
    ).scalar()
    
    assets = db.query(Asset).filter(
        Asset.crypto_account_id == account_id,
        Asset.asset_type == AssetType.CRYPTO,
        Asset.is_active == True
    ).all()
    
    total_invested_usd = sum(asset.total_invested for asset in assets)
    current_value_usd = sum(asset.current_value for asset in assets)
    total_profit_loss_usd = current_value_usd - total_invested_usd
    
    # Convert to dict and add statistics
    account_dict = {
        **account.__dict__,
        "asset_count": asset_count,
        "total_invested_usd": total_invested_usd,
        "current_value_usd": current_value_usd,
        "total_profit_loss_usd": total_profit_loss_usd
    }
    
    return CryptoAccountWithAssets(**account_dict)


@router.post("/", response_model=CryptoAccountSchema, status_code=status.HTTP_201_CREATED)
async def create_crypto_account(
    account_data: CryptoAccountCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new crypto account
    """
    # Validate exchange exists in master table
    exchange = db.query(CryptoExchangeMaster).filter(
        CryptoExchangeMaster.name == account_data.exchange_name,
        CryptoExchangeMaster.is_active == True
    ).first()
    if not exchange:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown or inactive exchange: {account_data.exchange_name}"
        )

    # Check if account already exists
    existing = db.query(CryptoAccount).filter(
        CryptoAccount.user_id == current_user.id,
        CryptoAccount.account_id == account_data.account_id,
        CryptoAccount.exchange_name == account_data.exchange_name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Crypto account with this account ID already exists for this exchange"
        )
    
    # If this is set as primary, unset other primary accounts
    if account_data.is_primary:
        db.query(CryptoAccount).filter(
            CryptoAccount.user_id == current_user.id,
            CryptoAccount.is_primary == True
        ).update({"is_primary": False})
    
    account = CryptoAccount(
        **account_data.model_dump(),
        user_id=current_user.id
    )
    
    db.add(account)
    db.commit()
    db.refresh(account)
    
    return account


@router.put("/{account_id}", response_model=CryptoAccountSchema)
async def update_crypto_account(
    account_id: int,
    account_data: CryptoAccountUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update a crypto account
    """
    account = db.query(CryptoAccount).filter(
        CryptoAccount.id == account_id,
        CryptoAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crypto account not found"
        )
    
    # If setting as primary, unset other primary accounts
    if account_data.is_primary and not account.is_primary:
        db.query(CryptoAccount).filter(
            CryptoAccount.user_id == current_user.id,
            CryptoAccount.is_primary == True
        ).update({"is_primary": False})
    
    # Update fields
    update_data = account_data.model_dump(exclude_unset=True)

    # Validate exchange if being changed
    if "exchange_name" in update_data and update_data["exchange_name"]:
        exchange = db.query(CryptoExchangeMaster).filter(
            CryptoExchangeMaster.name == update_data["exchange_name"],
            CryptoExchangeMaster.is_active == True
        ).first()
        if not exchange:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown or inactive exchange: {update_data['exchange_name']}"
            )

    for field, value in update_data.items():
        setattr(account, field, value)
    
    db.commit()
    db.refresh(account)
    
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_crypto_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a crypto account (will also delete all associated assets)
    """
    account = db.query(CryptoAccount).filter(
        CryptoAccount.id == account_id,
        CryptoAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crypto account not found"
        )
    
    db.delete(account)
    db.commit()
    
    return None

# Made with Bob