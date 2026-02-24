from pathlib import Path
from typing import List, Optional, Union
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator


def _read_version() -> str:
    """Read version from the VERSION file at the project root.
    Falls back to '0.0.0' if the file is missing."""
    for candidate in [
        Path(__file__).resolve().parents[3] / "VERSION",
        Path("/app/VERSION"),
    ]:
        if candidate.is_file():
            return candidate.read_text().strip()
    return "0.0.0"


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "PortAct"
    APP_VERSION: str = _read_version()
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str
    DB_ECHO: bool = False

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_set(cls, v: str, info: object) -> str:
        insecure_defaults = {
            "your-secret-key-change-this-in-production",
            "secret",
            "changeme",
            "",
        }
        # Access other values via info.data when available
        env = getattr(info, "data", {}).get("ENVIRONMENT", "production")
        if env == "production" and v in insecure_defaults:
            raise ValueError(
                "SECRET_KEY must be changed from the default value in production. "
                "Generate one with: openssl rand -hex 32"
            )
        return v

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # File Upload
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    UPLOAD_DIR: str = "./uploads"
    ALLOWED_EXTENSIONS: str = ".pdf,.csv,.xlsx,.xls,.doc,.docx"

    # External APIs - keys
    OPENAI_API_KEY: Optional[str] = None
    GROK_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    AI_NEWS_PROVIDER: str = "openai"
    ALPHA_VANTAGE_API_KEY: Optional[str] = None

    # External API endpoints (overridable for proxies / staging mirrors)
    OPENAI_API_ENDPOINT: str = "https://api.openai.com/v1/chat/completions"
    GROK_API_ENDPOINT: str = "https://api.x.ai/v1/chat/completions"
    GEMINI_API_ENDPOINT: str = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    ANTHROPIC_API_ENDPOINT: str = "https://api.anthropic.com/v1/messages"
    DEEPSEEK_API_ENDPOINT: str = "https://api.deepseek.com/chat/completions"
    MISTRAL_API_ENDPOINT: str = "https://api.mistral.ai/v1/chat/completions"
    COINGECKO_API_BASE: str = "https://api.coingecko.com/api/v3"
    NSE_API_BASE: str = "https://www.nseindia.com/api"
    AMFI_NAV_URL: str = "https://www.amfiindia.com/spages/NAVAll.txt"
    GOLD_PRICE_API: str = "https://api.metals.live/v1/spot/gold"
    EXCHANGE_RATE_API: str = "https://api.exchangerate-api.com/v4/latest/USD"
    EXCHANGE_RATE_FALLBACK_API: str = "https://open.er-api.com/v6/latest/USD"
    YAHOO_FINANCE_API: str = "https://query1.finance.yahoo.com/v8/finance/chart"
    FMP_API_BASE: str = "https://financialmodelingprep.com/api/v3"
    FMP_API_KEY: str = "demo"

    # AI model selection (overridable without changing code)
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    GROK_MODEL: str = "grok-beta"
    GEMINI_MODEL: str = "gemini-2.0-flash"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    MISTRAL_MODEL: str = "mistral-small-latest"

    # AI request tuning
    AI_REQUEST_DELAY: float = 2.0       # seconds between successive AI requests
    AI_REQUEST_TIMEOUT: int = 30        # HTTP timeout for each AI call
    AI_MAX_RETRIES: int = 3
    AI_RETRY_DELAY: float = 5.0         # base delay before retry (multiplied by attempt)
    AI_MAX_TOKENS: int = 800
    AI_TEMPERATURE: float = 0.3

    # API Timeouts (in seconds)
    API_TIMEOUT: int = 10
    API_TIMEOUT_SHORT: int = 5

    # Scheduler settings
    PRICE_UPDATE_INTERVAL_MINUTES: int = 30
    EOD_SNAPSHOT_HOUR: int = 13         # UTC hour for EOD snapshot (13:30 UTC = 7 PM IST)
    EOD_SNAPSHOT_MINUTE: int = 30
    NEWS_MORNING_HOUR: int = 9          # IST hour for morning news fetch
    NEWS_EVENING_HOUR: int = 18         # IST hour for evening news fetch
    NEWS_LIMIT_PER_USER: int = 0        # 0 = no limit; process all assets per user per run
    MONTHLY_CONTRIBUTION_DAY: int = 1   # Day of month for PF/Gratuity job
    MONTHLY_CONTRIBUTION_HOUR: int = 0  # UTC hour (0 UTC = 5:30 AM IST)
    MONTHLY_CONTRIBUTION_MINUTE: int = 30

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Email
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # Frontend (used for building in-app reset URLs)
    FRONTEND_URL: str = "http://localhost:3000"
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # MinIO / S3-compatible storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "portact-statements"
    MINIO_SECURE: bool = False

    # AWS S3 (used when deploying to AWS; MinIO SDK can talk to S3 directly)
    AWS_S3_BUCKET: Optional[str] = None
    AWS_S3_REGION: str = "ap-south-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
