from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.institution import InstitutionMaster
from app.schemas.institution import (
    InstitutionResponse,
    InstitutionCreate,
    InstitutionUpdate,
)

router = APIRouter()


@router.get("/", response_model=List[InstitutionResponse])
async def get_institutions(
    is_active: Optional[bool] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    query = db.query(InstitutionMaster)
    if is_active is not None:
        query = query.filter(InstitutionMaster.is_active == is_active)
    if category:
        query = query.filter(InstitutionMaster.category == category)
    return query.order_by(InstitutionMaster.sort_order, InstitutionMaster.display_label).all()


@router.get("/{institution_id}", response_model=InstitutionResponse)
async def get_institution(
    institution_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    inst = db.query(InstitutionMaster).filter(InstitutionMaster.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")
    return inst


@router.post("/", response_model=InstitutionResponse, status_code=status.HTTP_201_CREATED)
async def create_institution(
    data: InstitutionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    name = data.name.strip().lower().replace(" ", "_")
    existing = db.query(InstitutionMaster).filter(
        InstitutionMaster.name == name,
        InstitutionMaster.category == data.category,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Institution '{name}' already exists in category '{data.category}'",
        )
    inst = InstitutionMaster(
        name=name,
        display_label=data.display_label.strip(),
        category=data.category,
        website=data.website,
        is_active=data.is_active,
        sort_order=data.sort_order,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


@router.put("/{institution_id}", response_model=InstitutionResponse)
async def update_institution(
    institution_id: int,
    data: InstitutionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    inst = db.query(InstitutionMaster).filter(InstitutionMaster.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")

    update_data = data.model_dump(exclude_unset=True)

    if "name" in update_data:
        new_name = update_data["name"].strip().lower().replace(" ", "_")
        dup = db.query(InstitutionMaster).filter(
            InstitutionMaster.name == new_name,
            InstitutionMaster.category == inst.category,
            InstitutionMaster.id != institution_id,
        ).first()
        if dup:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Institution '{new_name}' already exists in category '{inst.category}'",
            )
        update_data["name"] = new_name

    for field, value in update_data.items():
        setattr(inst, field, value)

    db.commit()
    db.refresh(inst)
    return inst


@router.delete("/{institution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_institution(
    institution_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    inst = db.query(InstitutionMaster).filter(InstitutionMaster.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")

    db.delete(inst)
    db.commit()
    return None
