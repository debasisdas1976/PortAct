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

MASK_PLACEHOLDER = "***"


def _mask_secret(value: str | None) -> str:
    """Mask a secret value, showing only a short prefix and suffix."""
    if not value:
        return ""
    if len(value) <= 8:
        return MASK_PLACEHOLDER
    return f"{value[:4]}{MASK_PLACEHOLDER}...{value[-4:]}"


def _is_masked(value: str) -> bool:
    """Check if a value looks like our mask pattern (user didn't change it)."""
    return MASK_PLACEHOLDER in value


def _seed_defaults_if_empty(db: Session) -> None:
    """Insert default rows when the table is empty (first run)."""
    if db.query(AppSettings).count() > 0:
        return
    for item in DEFAULT_APP_SETTINGS:
        db.add(AppSettings(**item))
    db.commit()
    logger.info("Seeded default app_settings rows.")


def _ensure_new_defaults(db: Session) -> None:
    """Insert any new default settings that don't yet exist (for upgrades)."""
    existing_keys = {row.key for row in db.query(AppSettings.key).all()}
    new_rows = [s for s in DEFAULT_APP_SETTINGS if s["key"] not in existing_keys]
    if new_rows:
        for item in new_rows:
            db.add(AppSettings(**item))
        db.commit()
        logger.info(f"Seeded {len(new_rows)} new default app_settings rows.")


def _apply_masking(rows: list) -> List[AppSettingResponse]:
    """Build response list with secret values masked."""
    result = []
    for row in rows:
        data = AppSettingResponse.model_validate(row)
        if row.value_type == "secret" and row.value:
            data.value = _mask_secret(row.value)
        result.append(data)
    return result


@router.get("/", response_model=List[AppSettingResponse])
async def list_settings(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
):
    """Return all application settings."""
    _seed_defaults_if_empty(db)
    _ensure_new_defaults(db)
    rows = db.query(AppSettings).order_by(AppSettings.category, AppSettings.key).all()
    return _apply_masking(rows)


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
    Secret values that still contain the mask placeholder are skipped.
    """
    _seed_defaults_if_empty(db)
    _ensure_new_defaults(db)

    changed_keys: list[str] = []
    for item in payload.settings:
        setting = db.query(AppSettings).filter(AppSettings.key == item.key).first()
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting '{item.key}' not found",
            )
        # Skip secret fields whose value still contains the mask (user didn't change them)
        if setting.value_type == "secret" and _is_masked(item.value):
            continue
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

    rows = db.query(AppSettings).order_by(AppSettings.category, AppSettings.key).all()
    return _apply_masking(rows)


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

    rows = db.query(AppSettings).order_by(AppSettings.category, AppSettings.key).all()
    return _apply_masking(rows)
