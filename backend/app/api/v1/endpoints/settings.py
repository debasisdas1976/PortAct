"""
Application settings CRUD endpoints.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.asset import Asset, AssetType
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


def _mask_secret(value: Optional[str]) -> str:
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


# ── helpers for automations endpoint ──

def _get_setting_value(db: Session, key: str, default: str = "") -> str:
    """Helper to fetch a single setting value."""
    row = db.query(AppSettings).filter(AppSettings.key == key).first()
    return row.value if row and row.value else default


@router.get("/automations")
async def list_automations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Return a consolidated view of all automations the user has opted for.
    Includes system-level scheduled tasks and per-asset automations.
    """
    _seed_defaults_if_empty(db)
    _ensure_new_defaults(db)

    # ── System automations (from app_settings) ──
    system_automations = []

    price_interval = _get_setting_value(db, "price_update_interval_minutes", "30")
    system_automations.append({
        "name": "Price Updates",
        "category": "scheduler",
        "description": "Auto-fetches latest prices for stocks, mutual funds, crypto, and commodities",
        "enabled": True,
        "schedule": f"Every {price_interval} minutes",
    })

    eod_h = _get_setting_value(db, "eod_snapshot_hour", "13")
    eod_m = _get_setting_value(db, "eod_snapshot_minute", "30")
    system_automations.append({
        "name": "EOD Portfolio Snapshot",
        "category": "scheduler",
        "description": "Captures daily portfolio value for historical tracking and performance charts",
        "enabled": True,
        "schedule": f"Daily at {eod_h}:{eod_m.zfill(2)} UTC",
    })

    news_morning = _get_setting_value(db, "news_morning_hour", "9")
    system_automations.append({
        "name": "Morning News Alerts",
        "category": "scheduler",
        "description": "AI-generated news alerts for portfolio holdings",
        "enabled": True,
        "schedule": f"Daily at {news_morning}:00 IST",
    })

    news_evening = _get_setting_value(db, "news_evening_hour", "18")
    system_automations.append({
        "name": "Evening News Alerts",
        "category": "scheduler",
        "description": "AI-generated news alerts for portfolio holdings",
        "enabled": True,
        "schedule": f"Daily at {news_evening}:00 IST",
    })

    system_automations.append({
        "name": "Daily Forex Refresh",
        "category": "scheduler",
        "description": "Updates foreign currency asset values with latest exchange rates",
        "enabled": True,
        "schedule": "Daily at 9:00 UTC (2:30 PM IST)",
    })

    # ── Employment-based automations ──
    is_employed = getattr(current_user, "is_employed", False) or False
    has_salary = (getattr(current_user, "basic_salary", 0) or 0) > 0

    contrib_day = _get_setting_value(db, "monthly_contribution_day", "1")
    contrib_h = _get_setting_value(db, "monthly_contribution_hour", "0")
    contrib_m = _get_setting_value(db, "monthly_contribution_minute", "30")

    system_automations.append({
        "name": "Monthly PF Contributions",
        "category": "employment",
        "description": "Automatically adds Employee and Employer PF contributions on the 1st of each month",
        "enabled": bool(is_employed and has_salary),
        "schedule": f"Monthly on day {contrib_day} at {contrib_h}:{contrib_m.zfill(2)} UTC",
        "prerequisite": "Requires employment details and salary configuration",
    })

    system_automations.append({
        "name": "Gratuity Revaluation",
        "category": "employment",
        "description": "Recomputes gratuity amount based on years of service and current basic salary",
        "enabled": bool(is_employed and has_salary),
        "schedule": f"Monthly on day {contrib_day} at {contrib_h}:{contrib_m.zfill(2)} UTC",
        "prerequisite": "Requires 5+ years of service for eligibility",
    })

    # ── Per-asset automations (FD / RD with auto_update) ──
    asset_automations = []

    fd_assets = (
        db.query(Asset)
        .filter(
            Asset.user_id == current_user.id,
            Asset.asset_type == AssetType.FIXED_DEPOSIT.value,
        )
        .all()
    )
    for fd in fd_assets:
        d = fd.details or {}
        asset_automations.append({
            "asset_id": fd.id,
            "asset_name": fd.name,
            "asset_type": "Fixed Deposit",
            "automation": "Auto-generate interest transactions",
            "enabled": d.get("auto_update", False),
            "details": {
                "bank_name": d.get("bank_name", ""),
                "interest_rate": d.get("interest_rate", 0),
                "interest_type": d.get("interest_type", "simple"),
            },
        })

    rd_assets = (
        db.query(Asset)
        .filter(
            Asset.user_id == current_user.id,
            Asset.asset_type == AssetType.RECURRING_DEPOSIT.value,
        )
        .all()
    )
    for rd in rd_assets:
        d = rd.details or {}
        asset_automations.append({
            "asset_id": rd.id,
            "asset_name": rd.name,
            "asset_type": "Recurring Deposit",
            "automation": "Auto-generate installment and interest transactions",
            "enabled": d.get("auto_update", False),
            "details": {
                "bank_name": d.get("bank_name", ""),
                "interest_rate": d.get("interest_rate", 0),
                "monthly_installment": d.get("monthly_installment", 0),
            },
        })

    return {
        "system_automations": system_automations,
        "asset_automations": asset_automations,
    }
