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
from app.services.ai_models_service import get_cached_models, refresh_ai_models_cache

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
    "forex_refresh_hour",
    "forex_refresh_minute",
    "macro_data_refresh_day",
    "macro_data_refresh_hour",
    "rbi_rate_refresh_day",
    "rbi_rate_refresh_hour",
    "bank_fd_refresh_day",
    "bank_fd_refresh_hour",
    "govt_scheme_refresh_day",
    "govt_scheme_refresh_hour",
    "govt_scheme_refresh_minute",
    "news_cache_refresh_minutes",
    "nse_holidays_refresh_month",
    "nse_holidays_refresh_day",
    "mmi_morning_hour",
    "mmi_morning_minute",
    "mmi_afternoon_hour",
    "mmi_afternoon_minute",
    "btc_fng_hour",
    "btc_fng_minute",
    "us_fng_open_hour",
    "us_fng_open_minute",
    "us_fng_close_hour",
    "us_fng_close_minute",
    "liquidity_refresh_day_of_week",
    "liquidity_refresh_hour",
    "mf_systematic_plan_hour",
    "mf_systematic_plan_minute",
    "ai_models_refresh_hour",
    "ai_models_refresh_minute",
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


@router.get("/secret/{key}")
async def get_secret_value(
    key: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> Dict[str, str]:
    """Return the unmasked value of a single secret setting (for edit dialogs)."""
    _seed_defaults_if_empty(db)
    _ensure_new_defaults(db)
    setting = db.query(AppSettings).filter(AppSettings.key == key).first()
    if not setting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Setting '{key}' not found")
    if setting.value_type != "secret":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a secret setting")
    return {"key": key, "value": setting.value or ""}


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


@router.get("/api-keys-status")
async def api_keys_status(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> Dict[str, bool]:
    """Return which API keys (category='api_keys') are configured (non-empty)."""
    _seed_defaults_if_empty(db)
    _ensure_new_defaults(db)
    rows = db.query(AppSettings).filter(AppSettings.category == "api_keys").all()
    return {row.key: bool(row.value and row.value.strip()) for row in rows}


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

    forex_h = _get_setting_value(db, "forex_refresh_hour", "9")
    forex_m = _get_setting_value(db, "forex_refresh_minute", "0")
    system_automations.append({
        "name": "Daily Forex Refresh",
        "category": "scheduler",
        "description": "Updates foreign currency asset values with latest exchange rates",
        "enabled": True,
        "schedule": f"Daily at {forex_h}:{forex_m.zfill(2)} UTC",
    })

    macro_day = _get_setting_value(db, "macro_data_refresh_day", "1")
    macro_h = _get_setting_value(db, "macro_data_refresh_hour", "6")
    system_automations.append({
        "name": "Macro Data Refresh",
        "category": "market_insight",
        "description": "Monthly fetch of US CPI, unemployment, India CPI, VIX, Nifty PE, FII/DII flows, SIP inflows",
        "enabled": True,
        "schedule": f"Monthly on day {macro_day} at {macro_h}:00 UTC",
    })

    rbi_day = _get_setting_value(db, "rbi_rate_refresh_day", "10")
    rbi_h = _get_setting_value(db, "rbi_rate_refresh_hour", "9")
    system_automations.append({
        "name": "RBI Repo Rate Scrape",
        "category": "market_insight",
        "description": "Bimonthly scrape of RBI repo rate (Feb, Apr, Jun, Aug, Oct, Dec — MPC meeting months)",
        "enabled": True,
        "schedule": f"Bimonthly on day {rbi_day} at {rbi_h}:00 UTC",
    })

    fd_day = _get_setting_value(db, "bank_fd_refresh_day", "1")
    fd_h = _get_setting_value(db, "bank_fd_refresh_hour", "7")
    system_automations.append({
        "name": "Bank FD Rate Scrape",
        "category": "market_insight",
        "description": "Monthly scrape of bank fixed deposit interest rates",
        "enabled": True,
        "schedule": f"Monthly on day {fd_day} at {fd_h}:00 UTC",
    })

    govt_day = _get_setting_value(db, "govt_scheme_refresh_day", "1")
    govt_h = _get_setting_value(db, "govt_scheme_refresh_hour", "7")
    govt_m = _get_setting_value(db, "govt_scheme_refresh_minute", "30")
    system_automations.append({
        "name": "Govt Scheme Rate Scrape",
        "category": "market_insight",
        "description": "Monthly scrape of government savings scheme rates (PPF, SSY, NSC, etc.)",
        "enabled": True,
        "schedule": f"Monthly on day {govt_day} at {govt_h}:{govt_m.zfill(2)} UTC",
    })

    news_cache_min = _get_setting_value(db, "news_cache_refresh_minutes", "30")
    system_automations.append({
        "name": "Financial News Cache",
        "category": "market_insight",
        "description": "Refreshes upcoming financial events and global news headlines",
        "enabled": True,
        "schedule": f"Every {news_cache_min} minutes",
    })

    nse_month = _get_setting_value(db, "nse_holidays_refresh_month", "12")
    nse_day = _get_setting_value(db, "nse_holidays_refresh_day", "1")
    system_automations.append({
        "name": "NSE Holidays Refresh",
        "category": "market_insight",
        "description": "Annual refresh of NSE trading holidays (seeds next year's holiday list)",
        "enabled": True,
        "schedule": f"Annual on month {nse_month} day {nse_day} at 01:00 UTC",
    })

    mmi_am_h = _get_setting_value(db, "mmi_morning_hour", "3")
    mmi_am_m = _get_setting_value(db, "mmi_morning_minute", "45")
    mmi_pm_h = _get_setting_value(db, "mmi_afternoon_hour", "10")
    mmi_pm_m = _get_setting_value(db, "mmi_afternoon_minute", "0")
    system_automations.append({
        "name": "India Market Mood Index",
        "category": "market_insight",
        "description": "Daily scrape of India MMI from Tickertape (morning + afternoon)",
        "enabled": True,
        "schedule": f"Daily at {mmi_am_h}:{mmi_am_m.zfill(2)} & {mmi_pm_h}:{mmi_pm_m.zfill(2)} UTC",
    })

    btc_h = _get_setting_value(db, "btc_fng_hour", "0")
    btc_m = _get_setting_value(db, "btc_fng_minute", "30")
    system_automations.append({
        "name": "Bitcoin Fear & Greed Index",
        "category": "market_insight",
        "description": "Daily fetch of Bitcoin Fear & Greed Index from Alternative.me",
        "enabled": True,
        "schedule": f"Daily at {btc_h}:{btc_m.zfill(2)} UTC",
    })

    us_open_h = _get_setting_value(db, "us_fng_open_hour", "14")
    us_open_m = _get_setting_value(db, "us_fng_open_minute", "45")
    us_close_h = _get_setting_value(db, "us_fng_close_hour", "21")
    us_close_m = _get_setting_value(db, "us_fng_close_minute", "0")
    system_automations.append({
        "name": "US Fear & Greed Index",
        "category": "market_insight",
        "description": "Fetches US Fear & Greed Index from CNN at market open and close",
        "enabled": True,
        "schedule": f"Daily at {us_open_h}:{us_open_m.zfill(2)} & {us_close_h}:{us_close_m.zfill(2)} UTC",
    })

    liq_dow = _get_setting_value(db, "liquidity_refresh_day_of_week", "mon")
    liq_h = _get_setting_value(db, "liquidity_refresh_hour", "2")
    system_automations.append({
        "name": "Global Liquidity Data",
        "category": "market_insight",
        "description": "Weekly fetch of M2 money supply (FRED) and asset price history (Yahoo Finance)",
        "enabled": True,
        "schedule": f"Every {liq_dow.capitalize()} at {liq_h}:00 UTC",
    })

    mf_h = _get_setting_value(db, "mf_systematic_plan_hour", "4")
    mf_m = _get_setting_value(db, "mf_systematic_plan_minute", "0")
    system_automations.append({
        "name": "MF Systematic Plans (SIP/STP/SWP)",
        "category": "scheduler",
        "description": "Daily execution of mutual fund systematic investment/transfer/withdrawal plans",
        "enabled": True,
        "schedule": f"Daily at {mf_h}:{mf_m.zfill(2)} UTC",
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


# ───────────────────────── AI Models Cache ─────────────────────────


@router.get("/ai-models")
def get_ai_models(
    refresh: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Return cached AI provider models.
    Pass ?refresh=true to force a live refresh from all providers.
    """
    if refresh:
        refresh_ai_models_cache()
        # Re-read from DB after refresh
    return get_cached_models(db)
