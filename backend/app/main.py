from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from loguru import logger
import traceback

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.api.v1.api import api_router
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.news_scheduler import news_scheduler
import app.models.app_settings as _app_settings_model  # noqa: F401 – register for create_all
import app.models.crypto_exchange as _crypto_exchange_model  # noqa: F401 – register for create_all
import app.models.institution as _institution_model  # noqa: F401 – register for create_all
import app.models.expense_category as _expense_category_model  # noqa: F401 – register for create_all
import app.models.broker as _broker_model  # noqa: F401 – register for create_all
import app.models.bank as _bank_model  # noqa: F401 – register for create_all
import app.models.asset_type_master as _asset_type_model  # noqa: F401 – register for create_all


def _fix_null_portfolio_ids(db):
    """
    One-time data fix: assign every asset, demat account, bank account,
    and expense that has portfolio_id=NULL to its owner's default portfolio.
    Runs on every startup but is a fast no-op once all records are fixed.
    """
    from app.models.asset import Asset
    from app.models.demat_account import DematAccount
    from app.models.bank_account import BankAccount
    from app.models.expense import Expense
    from app.models.portfolio import Portfolio
    from app.models.user import User

    users_with_orphans = set()

    # Collect user IDs that have orphaned records
    for Model in (Asset, DematAccount, BankAccount, Expense):
        if not hasattr(Model, 'portfolio_id'):
            continue
        user_ids = (
            db.query(Model.user_id)
            .filter(Model.portfolio_id == None)
            .distinct()
            .all()
        )
        for (uid,) in user_ids:
            users_with_orphans.add(uid)

    if not users_with_orphans:
        return

    total_fixed = 0
    for uid in users_with_orphans:
        default = db.query(Portfolio).filter(
            Portfolio.user_id == uid,
            Portfolio.is_default == True,
        ).first()
        if not default:
            default = db.query(Portfolio).filter(
                Portfolio.user_id == uid,
                Portfolio.is_active == True,
            ).first()
        if not default:
            logger.warning(f"User {uid} has no portfolio — skipping orphan fix")
            continue

        for Model in (Asset, DematAccount, BankAccount, Expense):
            if not hasattr(Model, 'portfolio_id'):
                continue
            count = (
                db.query(Model)
                .filter(Model.user_id == uid, Model.portfolio_id == None)
                .update({Model.portfolio_id: default.id}, synchronize_session=False)
            )
            total_fixed += count

    if total_fixed:
        db.commit()
        logger.info(f"Fixed {total_fixed} records with NULL portfolio_id across {len(users_with_orphans)} user(s).")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    # --- Startup ---
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")

    # In production (Docker), Alembic manages the schema — skip create_all to
    # avoid conflicts with migrations.  In development, create_all is a
    # convenient way to bootstrap tables without running migrations manually.
    if settings.ENVIRONMENT != "production":
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables verified.")
        except SQLAlchemyError as exc:
            logger.error(f"Failed to initialise database tables: {exc}")
            raise
    else:
        logger.info("Production mode — skipping create_all (Alembic manages schema).")

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
        # ── Seed master data from seed_data.json (auto-synced by seed_sync) ──
        from app.services.seed_sync import load_seed_data
        from app.models.crypto_exchange import CryptoExchangeMaster
        from app.models.institution import InstitutionMaster
        from app.models.bank import BankMaster
        from app.models.broker import BrokerMaster
        from app.models.asset_category_master import AssetCategoryMaster
        from app.models.asset_type_master import AssetTypeMaster
        from app.models.expense_category import ExpenseCategory

        seed = load_seed_data()

        def _upsert_master(model, defaults, key_fn, extra_fields=None):
            """Insert missing rows, update existing rows to match seed data."""
            existing = {key_fn(r): r for r in _startup_db.query(model).all()}
            inserted = updated = 0
            for item in defaults:
                key = key_fn(item)
                row = existing.get(key)
                if row is None:
                    _startup_db.add(model(**{**item, **(extra_fields or {})}))
                    inserted += 1
                else:
                    changed = False
                    for col, val in item.items():
                        if getattr(row, col, None) != val:
                            setattr(row, col, val)
                            changed = True
                    if changed:
                        updated += 1
            if inserted or updated:
                _startup_db.commit()
            label = model.__tablename__
            if inserted:
                logger.info(f"Seeded {inserted} new {label} rows.")
            if updated:
                logger.info(f"Updated {updated} existing {label} rows to match seed data.")

        _name_key = lambda r: r["name"] if isinstance(r, dict) else r.name

        _upsert_master(CryptoExchangeMaster, seed.get("crypto_exchanges", []), _name_key)
        _upsert_master(InstitutionMaster, seed.get("institutions", []),
                        lambda r: (r["name"], r["category"]) if isinstance(r, dict) else (r.name, r.category))
        _upsert_master(BankMaster, seed.get("banks", []), _name_key)
        _upsert_master(BrokerMaster, seed.get("brokers", []), _name_key)
        # Categories must be seeded before asset_types (FK dependency)
        _upsert_master(AssetCategoryMaster, seed.get("asset_categories", []), _name_key)
        _upsert_master(AssetTypeMaster, seed.get("asset_types", []), _name_key)

        # Validate that every Python AssetType enum member has a corresponding
        # row in the asset_types master table (now that seed sync has run).
        from app.models.asset import AssetType
        import sqlalchemy
        rows = _startup_db.execute(
            sqlalchemy.text("SELECT name FROM asset_types")
        ).fetchall()
        db_names = {row[0] for row in rows}
        missing = [member.value for member in AssetType if member.value not in db_names]
        if missing:
            raise RuntimeError(
                f"asset_types table is missing values: {missing}. "
                f"Run seed_data.json sync or add them manually."
            )
        logger.info("AssetType enum validation passed.")

        # Expense categories: system-level only
        existing_sys_cats = {
            r.name: r for r in _startup_db.query(ExpenseCategory).filter(
                ExpenseCategory.is_system == True
            ).all()
        }
        cat_inserted = cat_updated = 0
        for item in seed.get("expense_categories", []):
            row = existing_sys_cats.get(item["name"])
            if row is None:
                _startup_db.add(ExpenseCategory(**item, is_system=True, is_active=True, user_id=None))
                cat_inserted += 1
            else:
                changed = False
                for col, val in item.items():
                    if getattr(row, col, None) != val:
                        setattr(row, col, val)
                        changed = True
                if changed:
                    cat_updated += 1
        if cat_inserted or cat_updated:
            _startup_db.commit()
        if cat_inserted:
            logger.info(f"Seeded {cat_inserted} new system expense categories.")
        if cat_updated:
            logger.info(f"Updated {cat_updated} existing system expense categories to match seed data.")

        # Fix any records with NULL portfolio_id by assigning to user's default portfolio
        _fix_null_portfolio_ids(_startup_db)

        start_scheduler(_startup_db)
    finally:
        _startup_db.close()
    try:
        news_scheduler.start()
    except Exception as exc:
        logger.error(f"Failed to start news scheduler: {exc}")

    yield

    # --- Shutdown ---
    logger.info("Shutting down schedulers…")
    try:
        stop_scheduler()
    except Exception as exc:
        logger.error(f"Error stopping scheduler: {exc}")
    try:
        news_scheduler.stop()
    except Exception as exc:
        logger.error(f"Error stopping news scheduler: {exc}")
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

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Convert Pydantic validation errors into human-readable messages."""
    friendly_errors = []
    for err in exc.errors():
        loc = err.get("loc", ())
        field_parts = [str(part) for part in loc if part not in ("body", "query", "path")]
        field_name = " -> ".join(field_parts) if field_parts else "input"
        field_name = field_name.replace("_", " ")
        msg = err.get("msg", "is invalid")
        friendly_errors.append(f"{field_name}: {msg}")
    logger.warning(f"Validation error on {request.method} {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": "; ".join(friendly_errors) if friendly_errors else "Invalid input. Please check your data."},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error(f"Database error on {request.method} {request.url}: {exc}")
    if isinstance(exc, IntegrityError):
        error_msg = str(exc.orig).lower() if exc.orig else str(exc).lower()
        if "unique constraint" in error_msg or "duplicate" in error_msg:
            detail = "This record already exists. Please check for duplicates."
        elif "foreign key" in error_msg:
            detail = "This operation references data that does not exist or has been removed."
        elif "not null" in error_msg or "notnull" in error_msg:
            detail = "A required field is missing. Please fill in all required fields."
        else:
            detail = "This operation conflicts with existing data."
        return JSONResponse(status_code=409, content={"detail": detail})
    return JSONResponse(
        status_code=503,
        content={"detail": "A database error occurred. Please try again later."},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Return ValueError messages as 400 responses (these are business-logic validations)."""
    logger.warning(f"Validation error on {request.method} {request.url}: {exc}")
    message = str(exc)
    if len(message) > 200 or "traceback" in message.lower():
        message = "Invalid input. Please check your data and try again."
    return JSONResponse(
        status_code=400,
        content={"detail": message},
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
