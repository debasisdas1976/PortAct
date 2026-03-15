"""
Background scheduler for periodic tasks (price updates, EOD snapshots).
"""
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from typing import Optional
from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.price_updater import update_all_prices
from app.services.eod_snapshot_service import EODSnapshotService
from app.services.monthly_contribution_service import MonthlyContributionService
from app.services.forex_refresh_service import refresh_foreign_currency_values
from app.services.macro_data_service import refresh_macro_data, refresh_rbi_rate_only
from app.services.mmi_service import refresh_mmi, refresh_btc_fng, refresh_us_fng
from app.services.reference_rates_service import refresh_bank_fd_rates, refresh_govt_scheme_rates
from app.services.financial_events_service import refresh_news_cache
from app.services.nse_holidays_service import ensure_holidays
from app.services.mf_systematic_plan_service import process_due_plans
from app.services.ai_models_service import refresh_ai_models_cache

# Use a larger thread pool so that multiple I/O-bound jobs (HTTP scrapes, price
# updates, EOD snapshots) can run concurrently without exhausting workers.
scheduler = BackgroundScheduler(
    executors={"default": ThreadPoolExecutor(max_workers=20)},
    job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 300},
)


def _get_setting(db: Optional[Session], key: str, default):
    """Read a single value from app_settings, falling back to *default*."""
    if db is None:
        return default
    try:
        from app.models.app_settings import AppSettings
        row = db.query(AppSettings).filter(AppSettings.key == key).first()
        if row and row.value is not None:
            if row.value_type == "int":
                return int(row.value)
            if row.value_type == "float":
                return float(row.value)
            return row.value
    except Exception as exc:
        logger.warning(f"Could not read app_settings.{key}: {exc}")
    return default


def _eod_with_forex_refresh():
    """Run forex refresh immediately before EOD snapshot for fresh INR values."""
    try:
        refresh_foreign_currency_values()
    except Exception as exc:
        logger.error(f"Forex refresh failed before EOD snapshot (snapshot will still run): {exc}")
    EODSnapshotService.capture_all_users_snapshots()


def _macro_data_refresh():
    """Daily fetch of US CPI, US Unemployment (BLS) and India CPI (World Bank)."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        refresh_macro_data(db)
    except Exception as exc:
        logger.error(f"Macro data refresh failed: {exc}")
    finally:
        db.close()


def _rbi_rate_refresh():
    """Bimonthly scrape of RBI repo rate from BankBazaar (runs on MPC meeting months)."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        refresh_rbi_rate_only(db)
    except Exception as exc:
        logger.error(f"RBI rate refresh failed: {exc}")
    finally:
        db.close()


def _bank_fd_refresh():
    """Monthly scrape of bank FD rates from BankBazaar."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        refresh_bank_fd_rates(db)
    except Exception as exc:
        logger.error(f"Bank FD rates refresh failed: {exc}")
    finally:
        db.close()


def _govt_scheme_refresh():
    """Monthly scrape of government savings scheme rates from BankBazaar."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        refresh_govt_scheme_rates(db)
    except Exception as exc:
        logger.error(f"Govt scheme rates refresh failed: {exc}")
    finally:
        db.close()


def _news_cache_refresh():
    """Refresh the financial news cache every 30 minutes."""
    try:
        refresh_news_cache()
    except Exception as exc:
        logger.error(f"News cache refresh failed: {exc}")


def _nse_holidays_refresh():
    """Annual refresh of NSE trading holidays (Dec 1 — seeds next year's data)."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        ensure_holidays(db)
    except Exception as exc:
        logger.error(f"NSE holidays refresh failed: {exc}")
    finally:
        db.close()


def _mmi_refresh():
    """Daily scrape of India MMI from Tickertape and upsert into DB."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        refresh_mmi(db)
    except Exception as exc:
        logger.error(f"MMI refresh failed: {exc}")
    finally:
        db.close()


def _btc_fng_refresh():
    """Daily fetch of Bitcoin Fear & Greed Index from Alternative.me and upsert into DB."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        refresh_btc_fng(db)
    except Exception as exc:
        logger.error(f"BTC F&G refresh failed: {exc}")
    finally:
        db.close()


def _us_fng_refresh():
    """Daily fetch of US Fear & Greed Index from CNN and upsert into DB."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        refresh_us_fng(db)
    except Exception as exc:
        logger.error(f"US F&G refresh failed: {exc}")
    finally:
        db.close()


def _liquidity_refresh():
    """Weekly refresh of global M2 (FRED) + asset price history (Yahoo Finance)."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        from app.services.liquidity_service import refresh_liquidity_data
        refresh_liquidity_data(db)
    except Exception as exc:
        logger.error(f"Liquidity data refresh failed: {exc}")
    finally:
        db.close()


def _liquidity_startup_refresh():
    """Refresh liquidity cache at startup only if stale (avoids redundant fetches)."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        from app.services.liquidity_service import (
            _is_cache_fresh, _cache_version_ok, refresh_liquidity_data,
        )
        if not _is_cache_fresh(db) or not _cache_version_ok(db):
            refresh_liquidity_data(db)
    except Exception as exc:
        logger.error(f"Startup liquidity refresh failed: {exc}")
    finally:
        db.close()


def _read_all_schedule_settings(db: Optional[Session]) -> dict:
    """Read all scheduler settings from DB, falling back to defaults."""
    gs = lambda key, default: _get_setting(db, key, default)
    return {
        "price_interval": gs("price_update_interval_minutes", settings.PRICE_UPDATE_INTERVAL_MINUTES),
        "eod_hour": gs("eod_snapshot_hour", settings.EOD_SNAPSHOT_HOUR),
        "eod_minute": gs("eod_snapshot_minute", settings.EOD_SNAPSHOT_MINUTE),
        "mc_day": gs("monthly_contribution_day", settings.MONTHLY_CONTRIBUTION_DAY),
        "mc_hour": gs("monthly_contribution_hour", settings.MONTHLY_CONTRIBUTION_HOUR),
        "mc_minute": gs("monthly_contribution_minute", settings.MONTHLY_CONTRIBUTION_MINUTE),
        "forex_hour": gs("forex_refresh_hour", 9),
        "forex_minute": gs("forex_refresh_minute", 0),
        "macro_day": gs("macro_data_refresh_day", 1),
        "macro_hour": gs("macro_data_refresh_hour", 6),
        "rbi_day": gs("rbi_rate_refresh_day", 10),
        "rbi_hour": gs("rbi_rate_refresh_hour", 9),
        "bank_fd_day": gs("bank_fd_refresh_day", 1),
        "bank_fd_hour": gs("bank_fd_refresh_hour", 7),
        "govt_day": gs("govt_scheme_refresh_day", 1),
        "govt_hour": gs("govt_scheme_refresh_hour", 7),
        "govt_minute": gs("govt_scheme_refresh_minute", 30),
        "news_cache_minutes": gs("news_cache_refresh_minutes", 30),
        "nse_month": gs("nse_holidays_refresh_month", 12),
        "nse_day": gs("nse_holidays_refresh_day", 1),
        "mmi_am_hour": gs("mmi_morning_hour", 3),
        "mmi_am_minute": gs("mmi_morning_minute", 45),
        "mmi_pm_hour": gs("mmi_afternoon_hour", 10),
        "mmi_pm_minute": gs("mmi_afternoon_minute", 0),
        "btc_fng_hour": gs("btc_fng_hour", 0),
        "btc_fng_minute": gs("btc_fng_minute", 30),
        "us_fng_open_hour": gs("us_fng_open_hour", 14),
        "us_fng_open_minute": gs("us_fng_open_minute", 45),
        "us_fng_close_hour": gs("us_fng_close_hour", 21),
        "us_fng_close_minute": gs("us_fng_close_minute", 0),
        "liquidity_dow": gs("liquidity_refresh_day_of_week", "mon"),
        "liquidity_hour": gs("liquidity_refresh_hour", 2),
        "mf_plan_hour": gs("mf_systematic_plan_hour", 4),
        "mf_plan_minute": gs("mf_systematic_plan_minute", 0),
        "ai_models_hour": gs("ai_models_refresh_hour", 1),
        "ai_models_minute": gs("ai_models_refresh_minute", 0),
    }


def _schedule_all_jobs(s: dict):
    """Add or reschedule all jobs using the settings dict from _read_all_schedule_settings."""
    scheduler.add_job(
        func=update_all_prices,
        trigger=IntervalTrigger(minutes=s["price_interval"]),
        id="price_update_job",
        name="Update asset prices",
        replace_existing=True,
    )
    scheduler.add_job(
        func=_eod_with_forex_refresh,
        trigger=CronTrigger(hour=s["eod_hour"], minute=s["eod_minute"], timezone="UTC"),
        id="eod_snapshot_job",
        name="End of Day Portfolio Snapshot (with Forex Refresh)",
        replace_existing=True,
    )
    scheduler.add_job(
        func=MonthlyContributionService.process_all_users,
        trigger=CronTrigger(day=s["mc_day"], hour=s["mc_hour"], minute=s["mc_minute"], timezone="UTC"),
        id="monthly_contribution_job",
        name="Monthly PF Contribution & Gratuity Update",
        replace_existing=True,
    )
    scheduler.add_job(
        func=refresh_foreign_currency_values,
        trigger=CronTrigger(hour=s["forex_hour"], minute=s["forex_minute"], timezone="UTC"),
        id="forex_refresh_job",
        name="Daily Foreign Currency Value Refresh",
        replace_existing=True,
    )
    scheduler.add_job(
        func=_macro_data_refresh,
        trigger=CronTrigger(day=s["macro_day"], hour=s["macro_hour"], minute=0, timezone="UTC"),
        id="macro_data_refresh_job",
        name="Monthly Macro-Economic Data Refresh",
        replace_existing=True,
    )
    scheduler.add_job(
        func=_rbi_rate_refresh,
        trigger=CronTrigger(month="2,4,6,8,10,12", day=s["rbi_day"], hour=s["rbi_hour"], minute=0, timezone="UTC"),
        id="rbi_rate_refresh_job",
        name="Bimonthly RBI Repo Rate Scrape",
        replace_existing=True,
    )
    scheduler.add_job(
        func=_bank_fd_refresh,
        trigger=CronTrigger(day=s["bank_fd_day"], hour=s["bank_fd_hour"], minute=0, timezone="UTC"),
        id="bank_fd_refresh_job",
        name="Monthly Bank FD Rate Scrape",
        replace_existing=True,
    )
    scheduler.add_job(
        func=_govt_scheme_refresh,
        trigger=CronTrigger(day=s["govt_day"], hour=s["govt_hour"], minute=s["govt_minute"], timezone="UTC"),
        id="govt_scheme_refresh_job",
        name="Monthly Govt Savings Scheme Rate Scrape",
        replace_existing=True,
    )
    scheduler.add_job(
        func=_news_cache_refresh,
        trigger=IntervalTrigger(minutes=s["news_cache_minutes"]),
        id="news_cache_refresh_job",
        name="Financial News Cache Refresh",
        replace_existing=True,
    )
    scheduler.add_job(
        func=_nse_holidays_refresh,
        trigger=CronTrigger(month=s["nse_month"], day=s["nse_day"], hour=1, minute=0, timezone="UTC"),
        id="nse_holidays_refresh_job",
        name="Annual NSE Trading Holidays Refresh",
        replace_existing=True,
    )
    scheduler.add_job(
        func=_mmi_refresh,
        trigger=CronTrigger(hour=s["mmi_am_hour"], minute=s["mmi_am_minute"], timezone="UTC"),
        id="mmi_refresh_job_morning",
        name="Daily India MMI Refresh (morning)",
        replace_existing=True,
    )
    scheduler.add_job(
        func=_mmi_refresh,
        trigger=CronTrigger(hour=s["mmi_pm_hour"], minute=s["mmi_pm_minute"], timezone="UTC"),
        id="mmi_refresh_job_afternoon",
        name="Daily India MMI Refresh (afternoon)",
        replace_existing=True,
    )
    scheduler.add_job(
        func=_btc_fng_refresh,
        trigger=CronTrigger(hour=s["btc_fng_hour"], minute=s["btc_fng_minute"], timezone="UTC"),
        id="btc_fng_refresh_job",
        name="Daily Bitcoin Fear & Greed Index Refresh",
        replace_existing=True,
    )
    scheduler.add_job(
        func=_us_fng_refresh,
        trigger=CronTrigger(hour=s["us_fng_open_hour"], minute=s["us_fng_open_minute"], timezone="UTC"),
        id="us_fng_refresh_job_open",
        name="Daily US Fear & Greed Refresh (market open)",
        replace_existing=True,
    )
    scheduler.add_job(
        func=_us_fng_refresh,
        trigger=CronTrigger(hour=s["us_fng_close_hour"], minute=s["us_fng_close_minute"], timezone="UTC"),
        id="us_fng_refresh_job_close",
        name="Daily US Fear & Greed Refresh (market close)",
        replace_existing=True,
    )
    scheduler.add_job(
        func=_liquidity_refresh,
        trigger=CronTrigger(day_of_week=s["liquidity_dow"], hour=s["liquidity_hour"], minute=0, timezone="UTC"),
        id="liquidity_refresh_job",
        name="Weekly Global Liquidity Data Refresh (FRED + Yahoo Finance)",
        replace_existing=True,
    )
    scheduler.add_job(
        func=process_due_plans,
        trigger=CronTrigger(hour=s["mf_plan_hour"], minute=s["mf_plan_minute"], timezone="UTC"),
        id="mf_systematic_plan_job",
        name="Daily MF Systematic Plan Execution (SIP/STP/SWP)",
        replace_existing=True,
    )
    scheduler.add_job(
        func=refresh_ai_models_cache,
        trigger=CronTrigger(hour=s["ai_models_hour"], minute=s["ai_models_minute"], timezone="UTC"),
        id="ai_models_refresh_job",
        name="Daily AI Provider Models Cache Refresh",
        replace_existing=True,
    )


def start_scheduler(db: Optional[Session] = None):
    """Start the background scheduler with all periodic tasks."""
    if scheduler.running:
        logger.info("Background scheduler is already running.")
        return

    s = _read_all_schedule_settings(db)
    _schedule_all_jobs(s)

    scheduler.start()
    logger.info(
        f"Background scheduler started — all schedules read from DB/defaults. "
        f"Price updates every {s['price_interval']} min, "
        f"EOD at {s['eod_hour']:02d}:{s['eod_minute']:02d} UTC, "
        f"Forex at {s['forex_hour']:02d}:{s['forex_minute']:02d} UTC."
    )

    # Run missed-snapshot and missed-contribution catch-up in background threads
    # so they never block the async event loop during startup (which would make
    # the API unresponsive until they complete).
    def _catchup():
        logger.info("Checking for missed EOD snapshots…")
        try:
            EODSnapshotService.check_and_run_missed_snapshots()
        except Exception as exc:
            logger.error(f"Error checking missed snapshots: {exc}")
        logger.info("Checking for missed monthly contributions…")
        try:
            MonthlyContributionService.check_and_run_missed_contributions()
        except Exception as exc:
            logger.error(f"Error checking missed contributions: {exc}")

    threading.Thread(target=_catchup, daemon=True, name="startup-catchup").start()

    # Ensure NSE holidays are in DB for the current year (and next year if >= November).
    # Runs in a background thread so it never blocks startup.
    threading.Thread(target=_nse_holidays_refresh, daemon=True, name="nse-holidays-startup").start()

    # Warm the news cache immediately at startup so first page load doesn't wait
    threading.Thread(target=_news_cache_refresh, daemon=True, name="news-cache-startup").start()

    # Refresh liquidity cache at startup if stale (weekly data, low-cost check)
    threading.Thread(target=_liquidity_startup_refresh, daemon=True, name="liquidity-startup").start()


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped.")


def run_price_update_now():
    """Manually trigger a price update immediately."""
    logger.info("Manually triggering price update…")
    update_all_prices()


def apply_schedule_settings(db: Session) -> None:
    """Re-read scheduler settings from the DB and reschedule all running jobs."""
    if not scheduler.running:
        logger.warning("Scheduler not running; skipping reschedule.")
        return

    s = _read_all_schedule_settings(db)
    _schedule_all_jobs(s)

    logger.info("Scheduler rescheduled — all jobs updated from DB settings.")
