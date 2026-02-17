from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "PortAct"
    APP_VERSION: str = "1.0.0"
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
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    UPLOAD_DIR: str = "./uploads"
    ALLOWED_EXTENSIONS: str = ".pdf,.csv,.xlsx,.xls,.doc,.docx"
    
    # External APIs
    OPENAI_API_KEY: Optional[str] = None
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    
    # API Endpoints
    COINGECKO_API_BASE: str = "https://api.coingecko.com/api/v3"
    NSE_API_BASE: str = "https://www.nseindia.com/api"
    AMFI_NAV_URL: str = "https://www.amfiindia.com/spages/NAVAll.txt"
    GOLD_PRICE_API: str = "https://api.metals.live/v1/spot/gold"
    EXCHANGE_RATE_API: str = "https://api.exchangerate-api.com/v4/latest/USD"
    EXCHANGE_RATE_FALLBACK_API: str = "https://open.er-api.com/v6/latest/USD"
    YAHOO_FINANCE_API: str = "https://query1.finance.yahoo.com/v8/finance/chart"
    FMP_API_BASE: str = "https://financialmodelingprep.com/api/v3"
    FMP_API_KEY: str = "demo"
    
    # API Timeouts (in seconds)
    API_TIMEOUT: int = 10
    API_TIMEOUT_SHORT: int = 5
    
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
    
    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "portact-statements"
    MINIO_SECURE: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Made with Bob
