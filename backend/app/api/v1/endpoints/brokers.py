from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.broker import BrokerMaster
from app.models.demat_account import DematAccount
from app.schemas.broker import (
    BrokerResponse,
    BrokerCreate,
    BrokerUpdate,
)

router = APIRouter()


@router.get("/", response_model=List[BrokerResponse])
async def get_brokers(
    is_active: Optional[bool] = None,
    broker_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    query = db.query(BrokerMaster)
    if is_active is not None:
        query = query.filter(BrokerMaster.is_active == is_active)
    if broker_type:
        query = query.filter(BrokerMaster.broker_type == broker_type)
    return query.order_by(BrokerMaster.sort_order, BrokerMaster.display_label).all()


@router.get("/{broker_id}", response_model=BrokerResponse)
async def get_broker(
    broker_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    broker = db.query(BrokerMaster).filter(BrokerMaster.id == broker_id).first()
    if not broker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Broker not found")
    return broker


@router.post("/", response_model=BrokerResponse, status_code=status.HTTP_201_CREATED)
async def create_broker(
    data: BrokerCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    name = data.name.strip().lower().replace(" ", "_")
    existing = db.query(BrokerMaster).filter(BrokerMaster.name == name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Broker '{name}' already exists",
        )
    broker = BrokerMaster(
        name=name,
        display_label=data.display_label.strip(),
        broker_type=data.broker_type,
        supported_markets=data.supported_markets,
        website=data.website,
        is_active=data.is_active,
        sort_order=data.sort_order,
    )
    db.add(broker)
    db.commit()
    db.refresh(broker)
    return broker


@router.put("/{broker_id}", response_model=BrokerResponse)
async def update_broker(
    broker_id: int,
    data: BrokerUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    broker = db.query(BrokerMaster).filter(BrokerMaster.id == broker_id).first()
    if not broker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Broker not found")

    update_data = data.model_dump(exclude_unset=True)

    if "name" in update_data:
        new_name = update_data["name"].strip().lower().replace(" ", "_")
        dup = db.query(BrokerMaster).filter(
            BrokerMaster.name == new_name,
            BrokerMaster.id != broker_id,
        ).first()
        if dup:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Broker '{new_name}' already exists",
            )
        # Cascade rename in demat_accounts that reference the old name
        old_name = broker.name
        db.query(DematAccount).filter(DematAccount.broker_name == old_name).update(
            {"broker_name": new_name}, synchronize_session=False
        )
        update_data["name"] = new_name

    for field, value in update_data.items():
        setattr(broker, field, value)

    db.commit()
    db.refresh(broker)
    return broker


@router.delete("/{broker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_broker(
    broker_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    broker = db.query(BrokerMaster).filter(BrokerMaster.id == broker_id).first()
    if not broker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Broker not found")

    account_count = db.query(DematAccount).filter(DematAccount.broker_name == broker.name).count()
    if account_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete: {account_count} demat account(s) use this broker. Deactivate it instead.",
        )

    db.delete(broker)
    db.commit()
    return None
