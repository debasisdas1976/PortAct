from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.asset import Asset
from app.models.transaction import Transaction, TransactionType
from app.schemas.transaction import (
    Transaction as TransactionSchema,
    TransactionCreate,
    TransactionUpdate,
    TransactionWithAsset
)

router = APIRouter()


@router.get("/", response_model=List[TransactionSchema])
async def get_transactions(
    asset_id: Optional[int] = None,
    transaction_type: Optional[TransactionType] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all transactions for the current user with optional filtering
    """
    # Build query with joins to ensure user owns the assets
    query = db.query(Transaction).join(Asset).filter(
        Asset.user_id == current_user.id
    )
    
    if asset_id:
        query = query.filter(Transaction.asset_id == asset_id)
    
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    
    if start_date:
        query = query.filter(Transaction.transaction_date >= start_date)
    
    if end_date:
        query = query.filter(Transaction.transaction_date <= end_date)
    
    transactions = query.order_by(
        Transaction.transaction_date.desc()
    ).offset(skip).limit(limit).all()
    
    return transactions


@router.get("/{transaction_id}", response_model=TransactionSchema)
async def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific transaction by ID
    """
    transaction = db.query(Transaction).join(Asset).filter(
        Transaction.id == transaction_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    return transaction


@router.post("/", response_model=TransactionSchema, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction_data: TransactionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new transaction
    """
    # Verify asset belongs to user
    asset = db.query(Asset).filter(
        Asset.id == transaction_data.asset_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Create transaction
    new_transaction = Transaction(
        **transaction_data.model_dump()
    )
    
    db.add(new_transaction)
    
    # Update asset based on transaction
    _update_asset_from_transaction(asset, new_transaction)
    
    db.commit()
    db.refresh(new_transaction)
    
    return new_transaction


@router.put("/{transaction_id}", response_model=TransactionSchema)
async def update_transaction(
    transaction_id: int,
    transaction_update: TransactionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing transaction
    """
    transaction = db.query(Transaction).join(Asset).filter(
        Transaction.id == transaction_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Update fields
    update_data = transaction_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transaction, field, value)
    
    # Recalculate asset metrics
    asset = transaction.asset
    _recalculate_asset_from_transactions(asset, db)
    
    db.commit()
    db.refresh(transaction)
    
    return transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a transaction
    """
    transaction = db.query(Transaction).join(Asset).filter(
        Transaction.id == transaction_id,
        Asset.user_id == current_user.id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    asset = transaction.asset
    db.delete(transaction)
    
    # Recalculate asset metrics
    _recalculate_asset_from_transactions(asset, db)
    
    db.commit()
    
    return None


def _update_asset_from_transaction(asset: Asset, transaction: Transaction):
    """Helper function to update asset based on transaction"""
    if transaction.transaction_type == TransactionType.BUY:
        asset.quantity += transaction.quantity
        asset.total_invested += transaction.total_amount + transaction.fees + transaction.taxes
        if asset.quantity > 0:
            asset.purchase_price = asset.total_invested / asset.quantity
    elif transaction.transaction_type == TransactionType.SELL:
        asset.quantity -= transaction.quantity
        # Reduce total invested proportionally
        if asset.quantity >= 0:
            sold_ratio = transaction.quantity / (asset.quantity + transaction.quantity)
            asset.total_invested *= (1 - sold_ratio)
    elif transaction.transaction_type == TransactionType.DIVIDEND:
        # Dividend doesn't change quantity but adds to returns
        pass
    
    asset.calculate_metrics()


def _recalculate_asset_from_transactions(asset: Asset, db: Session):
    """Recalculate asset metrics from all transactions"""
    transactions = db.query(Transaction).filter(
        Transaction.asset_id == asset.id
    ).order_by(Transaction.transaction_date).all()
    
    asset.quantity = 0
    asset.total_invested = 0
    
    for transaction in transactions:
        _update_asset_from_transaction(asset, transaction)
    
    asset.calculate_metrics()

# Made with Bob
