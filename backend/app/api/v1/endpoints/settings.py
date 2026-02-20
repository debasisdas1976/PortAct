"""
Application settings CRUD endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.app_settings import AppSettings, DEFAULT_APP_SETTINGS
from app.schemas.app_settings import (
    AppSettingResponse,
    AppSettingsBulkUpdate,
)

router = APIRouter()

SCHEDULER_KEYS = {
    "price_update_interval_minutes",
    "eod_snapshot_hour",
    "eod_snapshot_minute",
    "news_morning_hour",
    "news_evening_hour",
    "news_limit_per_user",
    "monthly_contribution_day",
    "monthly_contribution_hour",
    "monthly_contribution_minute",
}


def _seed_defaults_if_empty(db: Session) -> None:
    """Insert default rows when the table is empty (first run)."""
    if db.query(AppSettings).count() > 0:
        return
    for item in DEFAULT_APP_SETTINGS:
        db.add(AppSettings(**item))
    db.commit()
    logger.info("Seeded default app_settings rows.")


@router.get("/", response_model=List[AppSettingResponse])
async def list_settings(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
):
    """Return all application settings."""
    _seed_defaults_if_empty(db)
    return db.query(AppSettings).order_by(AppSettings.category, AppSettings.key).all()


@router.put("/", response_model=List[AppSettingResponse])
async def bulk_update_settings(
    payload: AppSettingsBulkUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
):
    """
    Update one or more settings at once.
    If any scheduler-related key is changed the background schedulers are
    rescheduled automatically.
    """
    _seed_defaults_if_empty(db)

    changed_keys: list[str] = []
    for item in payload.settings:
        setting = db.query(AppSettings).filter(AppSettings.key == item.key).first()
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting '{item.key}' not found",
            )
        if setting.value != item.value:
            setting.value = item.value
            changed_keys.append(item.key)

    db.commit()
    logger.info(f"App settings updated: {changed_keys}")

    # Reschedule if any scheduler key was touched
    if changed_keys and SCHEDULER_KEYS & set(changed_keys):
        try:
            from app.services.scheduler import apply_schedule_settings
            apply_schedule_settings(db)
        except Exception as exc:
            logger.error(f"Failed to reschedule background jobs: {exc}")

    # Reschedule news jobs if news keys changed
    news_keys = {"news_morning_hour", "news_evening_hour", "news_limit_per_user"}
    if changed_keys and news_keys & set(changed_keys):
        try:
            from app.services.news_scheduler import news_scheduler
            news_scheduler.reschedule_news_jobs(db)
        except Exception as exc:
            logger.error(f"Failed to reschedule news jobs: {exc}")

    return db.query(AppSettings).order_by(AppSettings.category, AppSettings.key).all()


@router.post("/reset", response_model=List[AppSettingResponse])
async def reset_settings(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
):
    """Reset all settings to their defaults."""
    for item in DEFAULT_APP_SETTINGS:
        setting = db.query(AppSettings).filter(AppSettings.key == item["key"]).first()
        if setting:
            setting.value = item["value"]
        else:
            db.add(AppSettings(**item))
    db.commit()
    logger.info("App settings reset to defaults.")

    # Reschedule everything
    try:
        from app.services.scheduler import apply_schedule_settings
        apply_schedule_settings(db)
    except Exception as exc:
        logger.error(f"Failed to reschedule after reset: {exc}")

    try:
        from app.services.news_scheduler import news_scheduler
        news_scheduler.reschedule_news_jobs(db)
    except Exception as exc:
        logger.error(f"Failed to reschedule news after reset: {exc}")

    return db.query(AppSettings).order_by(AppSettings.category, AppSettings.key).all()
