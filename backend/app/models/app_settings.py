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
        "description": "Which AI provider to use: openai, grok, gemini, anthropic, deepseek, mistral.",
    },
    # ── AI API Keys (empty = fall back to .env) ──
    {
        "key": "ai_openai_api_key",
        "value": "",
        "value_type": "secret",
        "category": "ai",
        "label": "OpenAI API Key",
        "description": "API key for OpenAI. Leave blank to use the .env value.",
    },
    {
        "key": "ai_grok_api_key",
        "value": "",
        "value_type": "secret",
        "category": "ai",
        "label": "Grok API Key",
        "description": "API key for Grok (xAI). Leave blank to use the .env value.",
    },
    {
        "key": "ai_gemini_api_key",
        "value": "",
        "value_type": "secret",
        "category": "ai",
        "label": "Google Gemini API Key",
        "description": "API key for Google Gemini.",
    },
    {
        "key": "ai_anthropic_api_key",
        "value": "",
        "value_type": "secret",
        "category": "ai",
        "label": "Anthropic Claude API Key",
        "description": "API key for Anthropic Claude.",
    },
    {
        "key": "ai_deepseek_api_key",
        "value": "",
        "value_type": "secret",
        "category": "ai",
        "label": "DeepSeek API Key",
        "description": "API key for DeepSeek.",
    },
    {
        "key": "ai_mistral_api_key",
        "value": "",
        "value_type": "secret",
        "category": "ai",
        "label": "Mistral API Key",
        "description": "API key for Mistral AI.",
    },
    # ── AI API Endpoints ──
    {
        "key": "ai_openai_endpoint",
        "value": "https://api.openai.com/v1/chat/completions",
        "value_type": "string",
        "category": "ai",
        "label": "OpenAI Endpoint",
        "description": "OpenAI API endpoint URL.",
    },
    {
        "key": "ai_grok_endpoint",
        "value": "https://api.x.ai/v1/chat/completions",
        "value_type": "string",
        "category": "ai",
        "label": "Grok Endpoint",
        "description": "Grok API endpoint URL.",
    },
    {
        "key": "ai_gemini_endpoint",
        "value": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "value_type": "string",
        "category": "ai",
        "label": "Gemini Endpoint",
        "description": "Gemini OpenAI-compatible endpoint URL.",
    },
    {
        "key": "ai_anthropic_endpoint",
        "value": "https://api.anthropic.com/v1/messages",
        "value_type": "string",
        "category": "ai",
        "label": "Anthropic Endpoint",
        "description": "Anthropic Messages API endpoint URL.",
    },
    {
        "key": "ai_deepseek_endpoint",
        "value": "https://api.deepseek.com/chat/completions",
        "value_type": "string",
        "category": "ai",
        "label": "DeepSeek Endpoint",
        "description": "DeepSeek API endpoint URL.",
    },
    {
        "key": "ai_mistral_endpoint",
        "value": "https://api.mistral.ai/v1/chat/completions",
        "value_type": "string",
        "category": "ai",
        "label": "Mistral Endpoint",
        "description": "Mistral API endpoint URL.",
    },
    # ── AI Model Names ──
    {
        "key": "ai_openai_model",
        "value": "gpt-3.5-turbo",
        "value_type": "string",
        "category": "ai",
        "label": "OpenAI Model",
        "description": "OpenAI model name.",
    },
    {
        "key": "ai_grok_model",
        "value": "grok-beta",
        "value_type": "string",
        "category": "ai",
        "label": "Grok Model",
        "description": "Grok model name.",
    },
    {
        "key": "ai_gemini_model",
        "value": "gemini-2.0-flash",
        "value_type": "string",
        "category": "ai",
        "label": "Gemini Model",
        "description": "Gemini model name.",
    },
    {
        "key": "ai_anthropic_model",
        "value": "claude-sonnet-4-20250514",
        "value_type": "string",
        "category": "ai",
        "label": "Anthropic Model",
        "description": "Anthropic Claude model name.",
    },
    {
        "key": "ai_deepseek_model",
        "value": "deepseek-chat",
        "value_type": "string",
        "category": "ai",
        "label": "DeepSeek Model",
        "description": "DeepSeek model name.",
    },
    {
        "key": "ai_mistral_model",
        "value": "mistral-small-latest",
        "value_type": "string",
        "category": "ai",
        "label": "Mistral Model",
        "description": "Mistral model name.",
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
