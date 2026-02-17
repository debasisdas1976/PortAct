"""
Background scheduler for periodic tasks
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.services.price_updater import update_all_prices
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
        
        scheduler.start()
        logger.info("Background scheduler started. Price updates will run every 30 minutes.")
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
