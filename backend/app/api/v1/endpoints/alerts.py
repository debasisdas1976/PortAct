from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.alert import Alert, AlertType, AlertSeverity
from app.schemas.alert import (
    Alert as AlertSchema,
    AlertCreate,
    AlertUpdate
)

router = APIRouter()


@router.get("/", response_model=List[AlertSchema])
async def get_alerts(
    is_read: bool = Query(None),
    is_dismissed: bool = Query(None),
    severity: AlertSeverity = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all alerts for the current user with optional filtering
    """
    query = db.query(Alert).filter(Alert.user_id == current_user.id)
    
    if is_read is not None:
        query = query.filter(Alert.is_read == is_read)
    
    if is_dismissed is not None:
        query = query.filter(Alert.is_dismissed == is_dismissed)
    
    if severity:
        query = query.filter(Alert.severity == severity)
    
    alerts = query.order_by(
        Alert.alert_date.desc()
    ).offset(skip).limit(limit).all()
    
    return alerts


@router.get("/{alert_id}", response_model=AlertSchema)
async def get_alert(
    alert_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific alert by ID
    """
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == current_user.id
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    return alert


@router.post("/", response_model=AlertSchema, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new alert (typically used by system/admin)
    """
    new_alert = Alert(
        user_id=current_user.id,
        **alert_data.model_dump()
    )
    
    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)
    
    return new_alert


@router.patch("/{alert_id}", response_model=AlertSchema)
async def update_alert(
    alert_id: int,
    alert_update: AlertUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an alert (mark as read/dismissed)
    """
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == current_user.id
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    from datetime import datetime
    
    # Update fields
    if alert_update.is_read is not None:
        alert.is_read = alert_update.is_read
        if alert_update.is_read and not alert.read_at:
            alert.read_at = datetime.utcnow()
    
    if alert_update.is_dismissed is not None:
        alert.is_dismissed = alert_update.is_dismissed
        if alert_update.is_dismissed and not alert.dismissed_at:
            alert.dismissed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(alert)
    
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete an alert
    """
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == current_user.id
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    db.delete(alert)
    db.commit()
    
    return None

# Made with Bob
