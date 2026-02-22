from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.bank import BankMaster
from app.models.bank_account import BankAccount
from app.schemas.bank import (
    BankResponse,
    BankCreate,
    BankUpdate,
)

router = APIRouter()


@router.get("/", response_model=List[BankResponse])
async def get_banks(
    is_active: Optional[bool] = None,
    bank_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    query = db.query(BankMaster)
    if is_active is not None:
        query = query.filter(BankMaster.is_active == is_active)
    if bank_type:
        query = query.filter(BankMaster.bank_type == bank_type)
    return query.order_by(BankMaster.sort_order, BankMaster.display_label).all()


@router.get("/{bank_id}", response_model=BankResponse)
async def get_bank(
    bank_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    bank = db.query(BankMaster).filter(BankMaster.id == bank_id).first()
    if not bank:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank not found")
    return bank


@router.post("/", response_model=BankResponse, status_code=status.HTTP_201_CREATED)
async def create_bank(
    data: BankCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    name = data.name.strip().lower().replace(" ", "_")
    existing = db.query(BankMaster).filter(BankMaster.name == name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bank '{name}' already exists",
        )
    bank = BankMaster(
        name=name,
        display_label=data.display_label.strip(),
        bank_type=data.bank_type,
        website=data.website,
        is_active=data.is_active,
        sort_order=data.sort_order,
    )
    db.add(bank)
    db.commit()
    db.refresh(bank)
    return bank


@router.put("/{bank_id}", response_model=BankResponse)
async def update_bank(
    bank_id: int,
    data: BankUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    bank = db.query(BankMaster).filter(BankMaster.id == bank_id).first()
    if not bank:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank not found")

    update_data = data.model_dump(exclude_unset=True)

    if "name" in update_data:
        new_name = update_data["name"].strip().lower().replace(" ", "_")
        dup = db.query(BankMaster).filter(
            BankMaster.name == new_name,
            BankMaster.id != bank_id,
        ).first()
        if dup:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bank '{new_name}' already exists",
            )
        # Cascade rename in bank_accounts that reference the old name
        old_name = bank.name
        db.query(BankAccount).filter(BankAccount.bank_name == old_name).update(
            {"bank_name": new_name}, synchronize_session=False
        )
        update_data["name"] = new_name

    for field, value in update_data.items():
        setattr(bank, field, value)

    db.commit()
    db.refresh(bank)
    return bank


@router.delete("/{bank_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bank(
    bank_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    bank = db.query(BankMaster).filter(BankMaster.id == bank_id).first()
    if not bank:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank not found")

    account_count = db.query(BankAccount).filter(BankAccount.bank_name == bank.name).count()
    if account_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete: {account_count} bank account(s) use this bank. Deactivate it instead.",
        )

    db.delete(bank)
    db.commit()
    return None
