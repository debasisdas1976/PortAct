from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.asset import Asset
from app.models.asset_attribute import AssetAttribute, AssetAttributeValue, AssetAttributeAssignment
from app.schemas.asset_attribute import (
    AssetAttributeCreate, AssetAttributeUpdate, AssetAttributeResponse,
    AssetAttributeValueCreate, AssetAttributeValueUpdate, AssetAttributeValueResponse,
    AssetAttributeAssignmentResponse, BulkAssignmentUpdate,
)

router = APIRouter()


# ─── Helpers ────────────────────────────────────────────────────────────────

def _slugify(label: str) -> str:
    return label.strip().lower().replace(" ", "_").replace("-", "_")


def _get_user_attribute(db: Session, attribute_id: int, user_id: int) -> AssetAttribute:
    attr = (
        db.query(AssetAttribute)
        .filter(AssetAttribute.id == attribute_id, AssetAttribute.user_id == user_id)
        .first()
    )
    if not attr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attribute not found")
    return attr


def _enrich_assignment(a: AssetAttributeAssignment) -> dict:
    return {
        "id": a.id,
        "asset_id": a.asset_id,
        "attribute_id": a.attribute_id,
        "attribute_value_id": a.attribute_value_id,
        "created_at": a.created_at,
        "attribute_name": a.attribute.name if a.attribute else None,
        "attribute_display_label": a.attribute.display_label if a.attribute else None,
        "value_label": a.attribute_value.label if a.attribute_value else None,
        "value_color": a.attribute_value.color if a.attribute_value else None,
    }


# ─── Attribute CRUD ─────────────────────────────────────────────────────────

@router.get("/", response_model=List[AssetAttributeResponse])
async def get_attributes(
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(AssetAttribute)
        .options(joinedload(AssetAttribute.values))
        .filter(AssetAttribute.user_id == current_user.id)
    )
    if is_active is not None:
        query = query.filter(AssetAttribute.is_active == is_active)
    return query.order_by(AssetAttribute.sort_order, AssetAttribute.display_label).all()


@router.get("/{attribute_id}", response_model=AssetAttributeResponse)
async def get_attribute(
    attribute_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    attr = (
        db.query(AssetAttribute)
        .options(joinedload(AssetAttribute.values))
        .filter(AssetAttribute.id == attribute_id, AssetAttribute.user_id == current_user.id)
        .first()
    )
    if not attr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attribute not found")
    return attr


@router.post("/", response_model=AssetAttributeResponse, status_code=status.HTTP_201_CREATED)
async def create_attribute(
    data: AssetAttributeCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    name = _slugify(data.name) if data.name else _slugify(data.display_label)

    existing = db.query(AssetAttribute).filter(
        AssetAttribute.user_id == current_user.id,
        AssetAttribute.name == name,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Attribute '{name}' already exists",
        )

    attr = AssetAttribute(
        user_id=current_user.id,
        name=name,
        display_label=data.display_label.strip(),
        description=data.description,
        icon=data.icon,
        sort_order=data.sort_order,
        is_active=data.is_active,
    )
    db.add(attr)
    db.flush()

    if data.values:
        for i, v in enumerate(data.values):
            val = AssetAttributeValue(
                attribute_id=attr.id,
                label=v.label.strip(),
                color=v.color,
                sort_order=v.sort_order if v.sort_order else i,
                is_active=v.is_active,
            )
            db.add(val)

    db.commit()
    db.refresh(attr)
    return attr


@router.put("/{attribute_id}", response_model=AssetAttributeResponse)
async def update_attribute(
    attribute_id: int,
    data: AssetAttributeUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    attr = _get_user_attribute(db, attribute_id, current_user.id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "display_label" and value:
            value = value.strip()
        setattr(attr, field, value)
    db.commit()
    db.refresh(attr)
    return attr


@router.delete("/{attribute_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attribute(
    attribute_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    attr = _get_user_attribute(db, attribute_id, current_user.id)
    db.delete(attr)
    db.commit()


# ─── Attribute Value CRUD ───────────────────────────────────────────────────

@router.post("/{attribute_id}/values", response_model=AssetAttributeValueResponse, status_code=status.HTTP_201_CREATED)
async def add_value(
    attribute_id: int,
    data: AssetAttributeValueCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    attr = _get_user_attribute(db, attribute_id, current_user.id)

    existing = db.query(AssetAttributeValue).filter(
        AssetAttributeValue.attribute_id == attr.id,
        AssetAttributeValue.label == data.label.strip(),
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Value '{data.label}' already exists for this attribute",
        )

    val = AssetAttributeValue(
        attribute_id=attr.id,
        label=data.label.strip(),
        color=data.color,
        sort_order=data.sort_order,
        is_active=data.is_active,
    )
    db.add(val)
    db.commit()
    db.refresh(val)
    return val


@router.put("/{attribute_id}/values/{value_id}", response_model=AssetAttributeValueResponse)
async def update_value(
    attribute_id: int,
    value_id: int,
    data: AssetAttributeValueUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _get_user_attribute(db, attribute_id, current_user.id)

    val = db.query(AssetAttributeValue).filter(
        AssetAttributeValue.id == value_id,
        AssetAttributeValue.attribute_id == attribute_id,
    ).first()
    if not val:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Value not found")

    update_data = data.model_dump(exclude_unset=True)
    if "label" in update_data and update_data["label"]:
        update_data["label"] = update_data["label"].strip()
        # Check uniqueness
        dup = db.query(AssetAttributeValue).filter(
            AssetAttributeValue.attribute_id == attribute_id,
            AssetAttributeValue.label == update_data["label"],
            AssetAttributeValue.id != value_id,
        ).first()
        if dup:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Value '{update_data['label']}' already exists for this attribute",
            )

    for field, value in update_data.items():
        setattr(val, field, value)
    db.commit()
    db.refresh(val)
    return val


@router.delete("/{attribute_id}/values/{value_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_value(
    attribute_id: int,
    value_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _get_user_attribute(db, attribute_id, current_user.id)

    val = db.query(AssetAttributeValue).filter(
        AssetAttributeValue.id == value_id,
        AssetAttributeValue.attribute_id == attribute_id,
    ).first()
    if not val:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Value not found")

    db.delete(val)
    db.commit()


# ─── Assignments ────────────────────────────────────────────────────────────

@router.get("/assignments/{asset_id}", response_model=List[AssetAttributeAssignmentResponse])
async def get_assignments(
    asset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.user_id == current_user.id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    assignments = (
        db.query(AssetAttributeAssignment)
        .options(
            joinedload(AssetAttributeAssignment.attribute),
            joinedload(AssetAttributeAssignment.attribute_value),
        )
        .filter(AssetAttributeAssignment.asset_id == asset_id)
        .all()
    )
    return [_enrich_assignment(a) for a in assignments]


@router.get("/assignments/bulk/by-ids", response_model=dict)
async def get_bulk_assignments(
    asset_ids: str = Query(..., description="Comma-separated asset IDs"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    ids = [int(x.strip()) for x in asset_ids.split(",") if x.strip().isdigit()]
    if not ids:
        return {}

    # Verify all assets belong to user
    user_asset_ids = {
        r[0] for r in db.query(Asset.id).filter(Asset.id.in_(ids), Asset.user_id == current_user.id).all()
    }

    assignments = (
        db.query(AssetAttributeAssignment)
        .options(
            joinedload(AssetAttributeAssignment.attribute),
            joinedload(AssetAttributeAssignment.attribute_value),
        )
        .filter(AssetAttributeAssignment.asset_id.in_(user_asset_ids))
        .all()
    )

    result: dict = {}
    for a in assignments:
        aid = str(a.asset_id)
        if aid not in result:
            result[aid] = []
        result[aid].append(_enrich_assignment(a))
    return result


@router.put("/assignments/{asset_id}", response_model=List[AssetAttributeAssignmentResponse])
async def set_assignments(
    asset_id: int,
    data: BulkAssignmentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.user_id == current_user.id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    # Delete existing assignments
    db.query(AssetAttributeAssignment).filter(AssetAttributeAssignment.asset_id == asset_id).delete()

    # Insert new assignments
    for item in data.assignments:
        # Verify attribute belongs to user
        attr = db.query(AssetAttribute).filter(
            AssetAttribute.id == item.attribute_id,
            AssetAttribute.user_id == current_user.id,
        ).first()
        if not attr:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Attribute {item.attribute_id} not found",
            )
        # Verify value belongs to attribute
        val = db.query(AssetAttributeValue).filter(
            AssetAttributeValue.id == item.attribute_value_id,
            AssetAttributeValue.attribute_id == item.attribute_id,
        ).first()
        if not val:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Value {item.attribute_value_id} not valid for attribute {item.attribute_id}",
            )

        assignment = AssetAttributeAssignment(
            asset_id=asset_id,
            attribute_id=item.attribute_id,
            attribute_value_id=item.attribute_value_id,
        )
        db.add(assignment)

    db.commit()

    # Return enriched assignments
    assignments = (
        db.query(AssetAttributeAssignment)
        .options(
            joinedload(AssetAttributeAssignment.attribute),
            joinedload(AssetAttributeAssignment.attribute_value),
        )
        .filter(AssetAttributeAssignment.asset_id == asset_id)
        .all()
    )
    return [_enrich_assignment(a) for a in assignments]


@router.delete("/assignments/{asset_id}/{attribute_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_assignment(
    asset_id: int,
    attribute_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.user_id == current_user.id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    assignment = db.query(AssetAttributeAssignment).filter(
        AssetAttributeAssignment.asset_id == asset_id,
        AssetAttributeAssignment.attribute_id == attribute_id,
    ).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    db.delete(assignment)
    db.commit()
