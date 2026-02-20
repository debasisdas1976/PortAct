from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger
import traceback

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.api.v1.api import api_router
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.news_scheduler import news_scheduler
import app.models.app_settings as _app_settings_model  # noqa: F401 – register for create_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    # --- Startup ---
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")

    # Ensure tables exist (idempotent)
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified.")
    except SQLAlchemyError as exc:
        logger.error(f"Failed to initialise database tables: {exc}")
        raise

    # Seed default app settings and pass DB session so schedulers read from DB
    _startup_db = SessionLocal()
    try:
        from app.models.app_settings import AppSettings, DEFAULT_APP_SETTINGS
        existing_keys = {r.key for r in _startup_db.query(AppSettings.key).all()}
        new_items = [item for item in DEFAULT_APP_SETTINGS if item["key"] not in existing_keys]
        if new_items:
            for item in new_items:
                _startup_db.add(AppSettings(**item))
            _startup_db.commit()
            logger.info(f"Seeded {len(new_items)} new app_settings rows.")
        start_scheduler(_startup_db)
    finally:
        _startup_db.close()
    news_scheduler.start()

    yield

    # --- Shutdown ---
    logger.info("Shutting down schedulers…")
    stop_scheduler()
    news_scheduler.stop()
    logger.info("Shutdown complete.")


# Expose API docs only in non-production environments
_docs_url = "/docs" if settings.DEBUG or settings.ENVIRONMENT != "production" else None
_redoc_url = "/redoc" if settings.DEBUG or settings.ENVIRONMENT != "production" else None

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Personal Finance Portfolio Tracker API",
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    lifespan=lifespan,
)

# Configure CORS from environment settings.
# Strip trailing slashes: Pydantic's AnyHttpUrl serialises to "http://host:port/"
# but browsers send Origin headers without the trailing slash.
_cors_origins = [str(o).rstrip("/") for o in settings.BACKEND_CORS_ORIGINS]
if not _cors_origins:
    logger.warning(
        "BACKEND_CORS_ORIGINS is empty. No cross-origin requests will be allowed. "
        "Set it via the BACKEND_CORS_ORIGINS environment variable."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error(f"Database error on {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": "A database error occurred. Please try again later."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        f"Unhandled exception on {request.method} {request.url}: {exc}\n"
        + traceback.format_exc()
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "version": settings.APP_VERSION,
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Verifies database connectivity so load-balancers / orchestrators can use it.
    """
    db_status = "ok"
    try:
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
    except Exception as exc:
        logger.warning(f"Health check DB ping failed: {exc}")
        db_status = "unavailable"

    status = "healthy" if db_status == "ok" else "degraded"
    return {
        "status": status,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
