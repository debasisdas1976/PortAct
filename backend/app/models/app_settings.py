from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class AppSettings(Base):
    """Key-value store for application-wide settings (scheduler, AI, preferences)."""
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(20), default="string")  # string, int, float, bool
    category = Column(String(50), nullable=True)        # scheduler, ai, general
    label = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# Default settings seeded on first startup
DEFAULT_APP_SETTINGS = [
    {
        "key": "price_update_interval_minutes",
        "value": "30",
        "value_type": "int",
        "category": "scheduler",
        "label": "Price Update Interval (minutes)",
        "description": "How often asset prices are refreshed from market APIs.",
    },
    {
        "key": "eod_snapshot_hour",
        "value": "13",
        "value_type": "int",
        "category": "scheduler",
        "label": "EOD Snapshot Hour (UTC)",
        "description": "Hour (UTC, 0-23) when the daily portfolio snapshot is captured. 13 UTC = 6:30 PM IST.",
    },
    {
        "key": "eod_snapshot_minute",
        "value": "30",
        "value_type": "int",
        "category": "scheduler",
        "label": "EOD Snapshot Minute",
        "description": "Minute (0-59) for the daily portfolio snapshot.",
    },
    {
        "key": "news_morning_hour",
        "value": "9",
        "value_type": "int",
        "category": "scheduler",
        "label": "Morning News Hour (IST)",
        "description": "IST hour (0-23) for the morning AI news alert run.",
    },
    {
        "key": "news_evening_hour",
        "value": "18",
        "value_type": "int",
        "category": "scheduler",
        "label": "Evening News Hour (IST)",
        "description": "IST hour (0-23) for the evening AI news alert run.",
    },
    {
        "key": "news_limit_per_user",
        "value": "10",
        "value_type": "int",
        "category": "scheduler",
        "label": "News Assets per Run",
        "description": "Maximum number of portfolio assets analysed per user in each scheduled news run.",
    },
    {
        "key": "ai_news_provider",
        "value": "openai",
        "value_type": "string",
        "category": "ai",
        "label": "AI News Provider",
        "description": "Which AI provider to use for generating portfolio news alerts (openai or grok).",
    },
    {
        "key": "session_timeout_minutes",
        "value": "30",
        "value_type": "int",
        "category": "general",
        "label": "Session Timeout (minutes)",
        "description": "Idle time before the user session expires and requires re-login.",
    },
    {
        "key": "monthly_contribution_day",
        "value": "1",
        "value_type": "int",
        "category": "scheduler",
        "label": "Monthly Contribution Day",
        "description": "Day of the month (1-28) when automatic PF contributions and Gratuity updates run.",
    },
    {
        "key": "monthly_contribution_hour",
        "value": "0",
        "value_type": "int",
        "category": "scheduler",
        "label": "Monthly Contribution Hour (UTC)",
        "description": "UTC hour (0-23) for the monthly PF/Gratuity job. 0 UTC = 5:30 AM IST.",
    },
    {
        "key": "monthly_contribution_minute",
        "value": "30",
        "value_type": "int",
        "category": "scheduler",
        "label": "Monthly Contribution Minute",
        "description": "Minute (0-59) for the monthly PF/Gratuity job.",
    },
]
