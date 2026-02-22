from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.crypto_exchange import CryptoExchangeMaster
from app.models.crypto_account import CryptoAccount
from app.schemas.crypto_exchange import (
    CryptoExchangeResponse,
    CryptoExchangeCreate,
    CryptoExchangeUpdate,
)

router = APIRouter()


@router.get("/", response_model=List[CryptoExchangeResponse])
async def get_crypto_exchanges(
    is_active: Optional[bool] = None,
    exchange_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    query = db.query(CryptoExchangeMaster)
    if is_active is not None:
        query = query.filter(CryptoExchangeMaster.is_active == is_active)
    if exchange_type:
        query = query.filter(CryptoExchangeMaster.exchange_type == exchange_type)
    return query.order_by(CryptoExchangeMaster.sort_order, CryptoExchangeMaster.display_label).all()


@router.get("/{exchange_id}", response_model=CryptoExchangeResponse)
async def get_crypto_exchange(
    exchange_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    exchange = db.query(CryptoExchangeMaster).filter(CryptoExchangeMaster.id == exchange_id).first()
    if not exchange:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exchange not found")
    return exchange


@router.post("/", response_model=CryptoExchangeResponse, status_code=status.HTTP_201_CREATED)
async def create_crypto_exchange(
    data: CryptoExchangeCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    name = data.name.strip().lower().replace(" ", "_")
    existing = db.query(CryptoExchangeMaster).filter(CryptoExchangeMaster.name == name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exchange '{name}' already exists",
        )
    exchange = CryptoExchangeMaster(
        name=name,
        display_label=data.display_label.strip(),
        exchange_type=data.exchange_type,
        website=data.website,
        is_active=data.is_active,
        sort_order=data.sort_order,
    )
    db.add(exchange)
    db.commit()
    db.refresh(exchange)
    return exchange


@router.put("/{exchange_id}", response_model=CryptoExchangeResponse)
async def update_crypto_exchange(
    exchange_id: int,
    data: CryptoExchangeUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    exchange = db.query(CryptoExchangeMaster).filter(CryptoExchangeMaster.id == exchange_id).first()
    if not exchange:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exchange not found")

    update_data = data.model_dump(exclude_unset=True)

    if "name" in update_data:
        new_name = update_data["name"].strip().lower().replace(" ", "_")
        dup = db.query(CryptoExchangeMaster).filter(
            CryptoExchangeMaster.name == new_name,
            CryptoExchangeMaster.id != exchange_id,
        ).first()
        if dup:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exchange '{new_name}' already exists",
            )
        # Also rename in crypto_accounts that reference the old name
        old_name = exchange.name
        db.query(CryptoAccount).filter(CryptoAccount.exchange_name == old_name).update(
            {"exchange_name": new_name}, synchronize_session=False
        )
        update_data["name"] = new_name

    for field, value in update_data.items():
        setattr(exchange, field, value)

    db.commit()
    db.refresh(exchange)
    return exchange


@router.delete("/{exchange_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_crypto_exchange(
    exchange_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    exchange = db.query(CryptoExchangeMaster).filter(CryptoExchangeMaster.id == exchange_id).first()
    if not exchange:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exchange not found")

    account_count = db.query(CryptoAccount).filter(CryptoAccount.exchange_name == exchange.name).count()
    if account_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete: {account_count} crypto account(s) use this exchange. Deactivate it instead.",
        )

    db.delete(exchange)
    db.commit()
    return None
