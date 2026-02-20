from typing import List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger

from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.asset import Asset, AssetType
from app.models.alert import Alert, AlertType, AlertSeverity
from app.schemas.alert import (
    Alert as AlertSchema,
    AlertCreate,
    AlertUpdate,
)
from app.schemas.news_progress import NewsProgress
from app.services.ai_news_service import ai_news_service
from app.services.news_progress_tracker import progress_tracker

router = APIRouter()


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[AlertSchema])
async def get_alerts(
    is_read: bool = Query(None),
    is_dismissed: bool = Query(None),
    severity: AlertSeverity = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all alerts for the current user with optional filtering."""
    query = db.query(Alert).filter(Alert.user_id == current_user.id)

    if is_read is not None:
        query = query.filter(Alert.is_read == is_read)
    if is_dismissed is not None:
        query = query.filter(Alert.is_dismissed == is_dismissed)
    if severity is not None:
        query = query.filter(Alert.severity == severity)

    return query.order_by(Alert.alert_date.desc()).offset(skip).limit(limit).all()


@router.get("/stats", response_model=dict)
async def get_alert_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get alert statistics for the current user."""
    total = db.query(Alert).filter(Alert.user_id == current_user.id).count()
    unread = db.query(Alert).filter(
        Alert.user_id == current_user.id,
        Alert.is_read == False,
    ).count()
    critical = db.query(Alert).filter(
        Alert.user_id == current_user.id,
        Alert.severity == AlertSeverity.CRITICAL,
        Alert.is_dismissed == False,
    ).count()

    return {"total": total, "unread": unread, "critical": critical}


@router.get("/{alert_id}", response_model=AlertSchema)
async def get_alert(
    alert_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a specific alert by ID."""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == current_user.id,
    ).first()

    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    return alert


@router.post("/", response_model=AlertSchema, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new alert."""
    try:
        new_alert = Alert(user_id=current_user.id, **alert_data.model_dump())
        db.add(new_alert)
        db.commit()
        db.refresh(new_alert)
        return new_alert
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(f"DB error creating alert for user {current_user.id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to create alert. Please try again.",
        )


@router.patch("/{alert_id}", response_model=AlertSchema)
async def update_alert(
    alert_id: int,
    alert_update: AlertUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update an alert (mark as read / dismissed)."""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == current_user.id,
    ).first()

    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    try:
        now = datetime.now(timezone.utc)

        if alert_update.is_read is not None:
            alert.is_read = alert_update.is_read
            if alert_update.is_read and not alert.read_at:
                alert.read_at = now

        if alert_update.is_dismissed is not None:
            alert.is_dismissed = alert_update.is_dismissed
            if alert_update.is_dismissed and not alert.dismissed_at:
                alert.dismissed_at = now

        db.commit()
        db.refresh(alert)
        return alert
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(f"DB error updating alert {alert_id} for user {current_user.id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to update alert. Please try again.",
        )


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete an alert."""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == current_user.id,
    ).first()

    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    try:
        db.delete(alert)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(f"DB error deleting alert {alert_id} for user {current_user.id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to delete alert. Please try again.",
        )


# ---------------------------------------------------------------------------
# AI news fetch endpoints
# ---------------------------------------------------------------------------

@router.post("/fetch-news", status_code=status.HTTP_202_ACCEPTED)
async def fetch_portfolio_news(
    background_tasks: BackgroundTasks,
    limit: int = Query(10, ge=1, le=50, description="Max number of assets to process"),
    include_generic: bool = Query(True, description="Include generic India investment news"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Trigger AI-powered news fetching for the user's portfolio assets.

    Processes Stocks, US Stocks, and Crypto assets ordered by descending value.
    Optionally appends generic India investment news (PPF, EPF, Gold, Silver, Crypto).

    The job runs in the background. Poll ``/alerts/progress/{session_id}`` to
    track progress.
    """
    assets = (
        db.query(Asset)
        .filter(
            Asset.user_id == current_user.id,
            Asset.is_active == True,
            Asset.asset_type.in_([
                AssetType.STOCK,
                AssetType.US_STOCK,
                AssetType.CRYPTO,
            ]),
        )
        .order_by(Asset.current_value.desc())
        .limit(limit)
        .all()
    )

    session_id = progress_tracker.create_session(current_user.id, assets)

    async def _process_news():
        try:
            assets_processed, alerts_created, _ = await ai_news_service.process_user_portfolio(
                db=db,
                user_id=current_user.id,
                limit=limit,
                session_id=session_id,
            )

            generic_alerts = 0
            if include_generic:
                generic_alerts = await ai_news_service.process_generic_india_news(
                    db=db,
                    user_id=current_user.id,
                )

            logger.info(
                f"News fetch complete for user {current_user.id}: "
                f"{assets_processed} assets, {alerts_created} asset alerts, "
                f"{generic_alerts} generic alerts."
            )
        except Exception as exc:
            logger.error(f"Error in background news fetch for user {current_user.id}: {exc}")
            progress_tracker.fail_session(session_id)

    background_tasks.add_task(_process_news)

    return {
        "message": "News fetching started in background",
        "status": "processing",
        "max_assets": limit,
        "include_generic": include_generic,
        "session_id": session_id,
    }


@router.get("/progress/{session_id}", response_model=NewsProgress)
async def get_news_progress(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get the progress of a news fetching session."""
    progress = progress_tracker.get_progress(session_id)

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if progress.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to view this session",
        )

    return progress


@router.post("/cancel/{session_id}", status_code=status.HTTP_200_OK)
async def cancel_news_fetch(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Cancel an ongoing news fetching session."""
    progress = progress_tracker.get_progress(session_id)

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if progress.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to cancel this session",
        )

    if progress.status in {"completed", "failed", "cancelled"}:
        return {"message": f"Session already {progress.status}", "status": progress.status}

    progress_tracker.cancel_session(session_id)
    return {"message": "News fetching cancelled", "status": "cancelled", "session_id": session_id}
