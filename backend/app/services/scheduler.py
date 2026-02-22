"""
Background scheduler for periodic tasks (price updates, EOD snapshots).
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from typing import Optional
from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.price_updater import update_all_prices
from app.services.eod_snapshot_service import EODSnapshotService
from app.services.monthly_contribution_service import MonthlyContributionService

scheduler = BackgroundScheduler()


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

    # EOD snapshot job
    scheduler.add_job(
        func=EODSnapshotService.capture_all_users_snapshots,
        trigger=CronTrigger(hour=eod_hour, minute=eod_minute),
        id="eod_snapshot_job",
        name="End of Day Portfolio Snapshot",
        replace_existing=True,
    )

    # Monthly PF contribution & Gratuity update job
    scheduler.add_job(
        func=MonthlyContributionService.process_all_users,
        trigger=CronTrigger(day=mc_day, hour=mc_hour, minute=mc_minute),
        id="monthly_contribution_job",
        name="Monthly PF Contribution & Gratuity Update",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"Background scheduler started. "
        f"Price updates every {price_interval} min. "
        f"EOD snapshots at {eod_hour:02d}:{eod_minute:02d} UTC. "
        f"Monthly contributions on day {mc_day} at {mc_hour:02d}:{mc_minute:02d} UTC."
    )

    # Catch up on any missed snapshots from previous downtime
    logger.info("Checking for missed EOD snapshots…")
    try:
        EODSnapshotService.check_and_run_missed_snapshots()
    except Exception as exc:
        logger.error(f"Error checking missed snapshots: {exc}")

    # Catch up on any missed monthly contributions
    logger.info("Checking for missed monthly contributions…")
    try:
        MonthlyContributionService.check_and_run_missed_contributions()
    except Exception as exc:
        logger.error(f"Error checking missed contributions: {exc}")


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
    scheduler.reschedule_job("eod_snapshot_job", trigger=CronTrigger(hour=eod_hour, minute=eod_minute))
    scheduler.reschedule_job("monthly_contribution_job", trigger=CronTrigger(day=mc_day, hour=mc_hour, minute=mc_minute))

    logger.info(
        f"Scheduler rescheduled — prices every {price_interval} min, "
        f"EOD at {eod_hour:02d}:{eod_minute:02d} UTC, "
        f"monthly contributions on day {mc_day} at {mc_hour:02d}:{mc_minute:02d} UTC."
    )
