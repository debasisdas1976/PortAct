"""
Background scheduler for periodic tasks
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from app.services.price_updater import update_all_prices
from app.services.eod_snapshot_service import EODSnapshotService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def start_scheduler():
    """
    Start the background scheduler with all periodic tasks
    """
    if not scheduler.running:
        # Add price update job - runs every 30 minutes
        scheduler.add_job(
            func=update_all_prices,
            trigger=IntervalTrigger(minutes=30),
            id='price_update_job',
            name='Update asset prices',
            replace_existing=True
        )
        
        # Add EOD snapshot job - runs daily at 7 PM IST (1:30 PM UTC)
        scheduler.add_job(
            func=EODSnapshotService.capture_all_users_snapshots,
            trigger=CronTrigger(hour=13, minute=30),  # 7 PM IST = 1:30 PM UTC
            id='eod_snapshot_job',
            name='End of Day Portfolio Snapshot',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Background scheduler started.")
        logger.info("- Price updates will run every 30 minutes")
        logger.info("- EOD snapshots will run daily at 7 PM IST")
        
        # Check for missed snapshots on startup
        logger.info("Checking for missed EOD snapshots...")
        try:
            EODSnapshotService.check_and_run_missed_snapshots()
        except Exception as e:
            logger.error(f"Error checking missed snapshots: {str(e)}")
    else:
        logger.info("Scheduler is already running.")


def stop_scheduler():
    """
    Stop the background scheduler
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped.")


def run_price_update_now():
    """
    Manually trigger price update immediately
    """
    logger.info("Manually triggering price update...")
    update_all_prices()

# Made with Bob
