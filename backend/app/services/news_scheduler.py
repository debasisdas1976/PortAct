"""
Scheduler service for periodic AI news fetching.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from loguru import logger
from typing import Optional

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
from app.services.ai_news_service import ai_news_service


class NewsScheduler:
    """Scheduler for periodic AI-powered news fetching."""

    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False

    def start(self):
        """Start the news scheduler."""
        if self.is_running:
            logger.warning("News scheduler is already running.")
            return

        self.scheduler = AsyncIOScheduler()

        # Morning run (IST)
        self.scheduler.add_job(
            self._fetch_news_for_all_users,
            CronTrigger(
                hour=settings.NEWS_MORNING_HOUR,
                minute=0,
                timezone="Asia/Kolkata",
            ),
            id="morning_news_fetch",
            name="Morning News Fetch",
            replace_existing=True,
        )

        # Evening run (IST)
        self.scheduler.add_job(
            self._fetch_news_for_all_users,
            CronTrigger(
                hour=settings.NEWS_EVENING_HOUR,
                minute=0,
                timezone="Asia/Kolkata",
            ),
            id="evening_news_fetch",
            name="Evening News Fetch",
            replace_existing=True,
        )

        self.scheduler.start()
        self.is_running = True
        logger.info(
            f"News scheduler started. "
            f"Runs at {settings.NEWS_MORNING_HOUR:02d}:00 and "
            f"{settings.NEWS_EVENING_HOUR:02d}:00 IST."
        )

    def stop(self):
        """Stop the news scheduler."""
        if self.scheduler and self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("News scheduler stopped.")

    async def _fetch_news_for_all_users(self):
        """Scheduled job: fetch AI news for all active users."""
        db: Session = SessionLocal()
        try:
            users = db.query(User).filter(User.is_active == True).all()
            logger.info(f"Starting scheduled news fetch for {len(users)} user(s).")

            total_assets = 0
            total_alerts = 0

            for user in users:
                try:
                    assets_processed, alerts_created, _ = await ai_news_service.process_user_portfolio(
                        db=db,
                        user_id=user.id,
                    )
                    total_assets += assets_processed
                    total_alerts += alerts_created
                except Exception as exc:
                    logger.error(f"Error processing news for user {user.id}: {exc}")
                    continue

            logger.info(
                f"Scheduled news fetch complete: "
                f"{total_assets} assets processed, "
                f"{total_alerts} alerts created across {len(users)} user(s)."
            )

        except Exception as exc:
            logger.error(f"Fatal error in scheduled news fetch: {exc}")
        finally:
            db.close()

    def reschedule_news_jobs(self, db=None) -> None:
        """Re-read news schedule settings from the DB and reschedule jobs."""
        if not self.is_running or self.scheduler is None:
            logger.warning("News scheduler not running; skipping reschedule.")
            return

        from app.services.scheduler import _get_setting

        morning = _get_setting(db, "news_morning_hour", settings.NEWS_MORNING_HOUR)
        evening = _get_setting(db, "news_evening_hour", settings.NEWS_EVENING_HOUR)

        self.scheduler.reschedule_job(
            "morning_news_fetch",
            trigger=CronTrigger(hour=morning, minute=0, timezone="Asia/Kolkata"),
        )
        self.scheduler.reschedule_job(
            "evening_news_fetch",
            trigger=CronTrigger(hour=evening, minute=0, timezone="Asia/Kolkata"),
        )
        logger.info(f"News scheduler rescheduled — morning {morning:02d}:00, evening {evening:02d}:00 IST.")

    async def fetch_news_for_user(self, user_id: int, limit: Optional[int] = None):
        """Manually trigger news fetch for a specific user."""
        db: Session = SessionLocal()
        try:
            assets_processed, alerts_created, _ = await ai_news_service.process_user_portfolio(
                db=db,
                user_id=user_id,
            )
            logger.info(
                f"Manual news fetch for user {user_id}: "
                f"{assets_processed} assets processed, {alerts_created} alerts created."
            )
            return assets_processed, alerts_created
        except Exception as exc:
            logger.error(f"Error in manual news fetch for user {user_id}: {exc}")
            return 0, 0
        finally:
            db.close()


# Singleton instance
news_scheduler = NewsScheduler()
