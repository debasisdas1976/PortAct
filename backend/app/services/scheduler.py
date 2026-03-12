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


def start_scheduler(db: Optional[Session] = None):
    """Start the background scheduler with all periodic tasks."""
    if scheduler.running:
        logger.info("Background scheduler is already running.")
        return

    price_interval = _get_setting(db, "price_update_interval_minutes", settings.PRICE_UPDATE_INTERVAL_MINUTES)
    eod_hour = _get_setting(db, "eod_snapshot_hour", settings.EOD_SNAPSHOT_HOUR)
    eod_minute = _get_setting(db, "eod_snapshot_minute", settings.EOD_SNAPSHOT_MINUTE)
    mc_day = _get_setting(db, "monthly_contribution_day", settings.MONTHLY_CONTRIBUTION_DAY)
    mc_hour = _get_setting(db, "monthly_contribution_hour", settings.MONTHLY_CONTRIBUTION_HOUR)
    mc_minute = _get_setting(db, "monthly_contribution_minute", settings.MONTHLY_CONTRIBUTION_MINUTE)

    # Price update job
    scheduler.add_job(
        func=update_all_prices,
        trigger=IntervalTrigger(minutes=price_interval),
        id="price_update_job",
        name="Update asset prices",
        replace_existing=True,
    )

    # EOD snapshot job (runs forex refresh first to ensure fresh INR values)
    scheduler.add_job(
        func=_eod_with_forex_refresh,
        trigger=CronTrigger(hour=eod_hour, minute=eod_minute, timezone="UTC"),
        id="eod_snapshot_job",
        name="End of Day Portfolio Snapshot (with Forex Refresh)",
        replace_existing=True,
    )

    # Monthly PF contribution & Gratuity update job
    scheduler.add_job(
        func=MonthlyContributionService.process_all_users,
        trigger=CronTrigger(day=mc_day, hour=mc_hour, minute=mc_minute, timezone="UTC"),
        id="monthly_contribution_job",
        name="Monthly PF Contribution & Gratuity Update",
        replace_existing=True,
    )

    # Daily forex refresh for all non-INR assets (9 AM UTC = 2:30 PM IST)
    scheduler.add_job(
        func=refresh_foreign_currency_values,
        trigger=CronTrigger(hour=9, minute=0, timezone="UTC"),
        id="forex_refresh_job",
        name="Daily Foreign Currency Value Refresh",
        replace_existing=True,
    )

    # Monthly macro data refresh — runs on 1st of each month at 06:00 UTC
    # Picks up newly published CPI, GDP, VIX, PE, FII/DII, SIP figures
    scheduler.add_job(
        func=_macro_data_refresh,
        trigger=CronTrigger(day=1, hour=6, minute=0, timezone="UTC"),
        id="macro_data_refresh_job",
        name="Monthly Macro-Economic Data Refresh",
        replace_existing=True,
    )

    # Bimonthly RBI repo rate scrape — runs on the 10th of each MPC meeting month
    # MPC meetings: Feb, Apr, Jun, Aug, Oct, Dec (results typically on 6th-8th)
    scheduler.add_job(
        func=_rbi_rate_refresh,
        trigger=CronTrigger(month="2,4,6,8,10,12", day=10, hour=9, minute=0, timezone="UTC"),
        id="rbi_rate_refresh_job",
        name="Bimonthly RBI Repo Rate Scrape",
        replace_existing=True,
    )

    # Monthly bank FD rate scrape — 1st of every month at 07:00 UTC
    scheduler.add_job(
        func=_bank_fd_refresh,
        trigger=CronTrigger(day=1, hour=7, minute=0, timezone="UTC"),
        id="bank_fd_refresh_job",
        name="Monthly Bank FD Rate Scrape",
        replace_existing=True,
    )

    # Monthly govt scheme rate scrape — 1st of every month at 07:30 UTC
    # Rates can change monthly (declared quarterly, but checking monthly ensures we catch it)
    scheduler.add_job(
        func=_govt_scheme_refresh,
        trigger=CronTrigger(day=1, hour=7, minute=30, timezone="UTC"),
        id="govt_scheme_refresh_job",
        name="Monthly Govt Savings Scheme Rate Scrape",
        replace_existing=True,
    )

    # Financial news cache refresh — every 30 minutes
    scheduler.add_job(
        func=_news_cache_refresh,
        trigger=IntervalTrigger(minutes=30),
        id="news_cache_refresh_job",
        name="Financial News Cache Refresh (30 min)",
        replace_existing=True,
    )

    # Annual NSE holiday refresh — Dec 1 at 01:00 UTC (seeds next year's holiday list)
    scheduler.add_job(
        func=_nse_holidays_refresh,
        trigger=CronTrigger(month=12, day=1, hour=1, minute=0, timezone="UTC"),
        id="nse_holidays_refresh_job",
        name="Annual NSE Trading Holidays Refresh",
        replace_existing=True,
    )

    # Daily MMI refresh — 3:45 AM UTC (9:15 AM IST, just after NSE market open)
    # A second run at 10:00 AM UTC (3:30 PM IST) catches intraday updates.
    scheduler.add_job(
        func=_mmi_refresh,
        trigger=CronTrigger(hour=3, minute=45, timezone="UTC"),
        id="mmi_refresh_job_morning",
        name="Daily India MMI Refresh (morning)",
        replace_existing=True,
    )
    scheduler.add_job(
        func=_mmi_refresh,
        trigger=CronTrigger(hour=10, minute=0, timezone="UTC"),
        id="mmi_refresh_job_afternoon",
        name="Daily India MMI Refresh (afternoon)",
        replace_existing=True,
    )

    # BTC Fear & Greed — Alternative.me updates once daily (midnight UTC)
    scheduler.add_job(
        func=_btc_fng_refresh,
        trigger=CronTrigger(hour=0, minute=30, timezone="UTC"),
        id="btc_fng_refresh_job",
        name="Daily Bitcoin Fear & Greed Index Refresh",
        replace_existing=True,
    )

    # US Fear & Greed (CNN) — updates throughout the trading day; refresh at market open + close
    scheduler.add_job(
        func=_us_fng_refresh,
        trigger=CronTrigger(hour=14, minute=45, timezone="UTC"),  # ~9:45 AM ET (market open)
        id="us_fng_refresh_job_open",
        name="Daily US Fear & Greed Refresh (market open)",
        replace_existing=True,
    )
    scheduler.add_job(
        func=_us_fng_refresh,
        trigger=CronTrigger(hour=21, minute=0, timezone="UTC"),   # ~4:00 PM ET (market close)
        id="us_fng_refresh_job_close",
        name="Daily US Fear & Greed Refresh (market close)",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"Background scheduler started. "
        f"Price updates every {price_interval} min. "
        f"EOD snapshots at {eod_hour:02d}:{eod_minute:02d} UTC. "
        f"Monthly contributions on day {mc_day} at {mc_hour:02d}:{mc_minute:02d} UTC. "
        f"Forex refresh daily at 09:00 UTC + before EOD. "
        f"Macro data (BLS+WB) daily at 06:00 UTC. "
        f"RBI rate on 10th of Feb/Apr/Jun/Aug/Oct/Dec at 09:00 UTC."
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
    """Re-read scheduler settings from the DB and reschedule running jobs."""
    if not scheduler.running:
        logger.warning("Scheduler not running; skipping reschedule.")
        return

    price_interval = _get_setting(db, "price_update_interval_minutes", settings.PRICE_UPDATE_INTERVAL_MINUTES)
    eod_hour = _get_setting(db, "eod_snapshot_hour", settings.EOD_SNAPSHOT_HOUR)
    eod_minute = _get_setting(db, "eod_snapshot_minute", settings.EOD_SNAPSHOT_MINUTE)
    mc_day = _get_setting(db, "monthly_contribution_day", settings.MONTHLY_CONTRIBUTION_DAY)
    mc_hour = _get_setting(db, "monthly_contribution_hour", settings.MONTHLY_CONTRIBUTION_HOUR)
    mc_minute = _get_setting(db, "monthly_contribution_minute", settings.MONTHLY_CONTRIBUTION_MINUTE)

    scheduler.reschedule_job("price_update_job", trigger=IntervalTrigger(minutes=price_interval))
    scheduler.reschedule_job("eod_snapshot_job", trigger=CronTrigger(hour=eod_hour, minute=eod_minute, timezone="UTC"))
    scheduler.reschedule_job("monthly_contribution_job", trigger=CronTrigger(day=mc_day, hour=mc_hour, minute=mc_minute, timezone="UTC"))

    logger.info(
        f"Scheduler rescheduled — prices every {price_interval} min, "
        f"EOD at {eod_hour:02d}:{eod_minute:02d} UTC, "
        f"monthly contributions on day {mc_day} at {mc_hour:02d}:{mc_minute:02d} UTC."
    )
