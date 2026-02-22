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
        # Seed default crypto exchanges
        from app.models.crypto_exchange import CryptoExchangeMaster
        existing_exchanges = {r.name for r in _startup_db.query(CryptoExchangeMaster.name).all()}
        DEFAULT_CRYPTO_EXCHANGES = [
            {"name": "binance", "display_label": "Binance", "exchange_type": "exchange", "sort_order": 1},
            {"name": "coinbase", "display_label": "Coinbase", "exchange_type": "exchange", "sort_order": 2},
            {"name": "kraken", "display_label": "Kraken", "exchange_type": "exchange", "sort_order": 3},
            {"name": "wazirx", "display_label": "WazirX", "exchange_type": "exchange", "sort_order": 4},
            {"name": "coindcx", "display_label": "CoinDCX", "exchange_type": "exchange", "sort_order": 5},
            {"name": "zebpay", "display_label": "ZebPay", "exchange_type": "exchange", "sort_order": 6},
            {"name": "coinswitch", "display_label": "CoinSwitch", "exchange_type": "exchange", "sort_order": 7},
            {"name": "kucoin", "display_label": "KuCoin", "exchange_type": "exchange", "sort_order": 8},
            {"name": "bybit", "display_label": "Bybit", "exchange_type": "exchange", "sort_order": 9},
            {"name": "okx", "display_label": "OKX", "exchange_type": "exchange", "sort_order": 10},
            {"name": "metamask", "display_label": "MetaMask", "exchange_type": "wallet", "sort_order": 11},
            {"name": "trust_wallet", "display_label": "Trust Wallet", "exchange_type": "wallet", "sort_order": 12},
            {"name": "ledger", "display_label": "Ledger", "exchange_type": "wallet", "sort_order": 13},
            {"name": "trezor", "display_label": "Trezor", "exchange_type": "wallet", "sort_order": 14},
            {"name": "tangem", "display_label": "Tangem", "exchange_type": "wallet", "sort_order": 15},
            {"name": "getbit", "display_label": "Getbit", "exchange_type": "exchange", "sort_order": 16},
            {"name": "other", "display_label": "Other", "exchange_type": "exchange", "sort_order": 99},
        ]
        new_exchanges = [e for e in DEFAULT_CRYPTO_EXCHANGES if e["name"] not in existing_exchanges]
        if new_exchanges:
            for ex in new_exchanges:
                _startup_db.add(CryptoExchangeMaster(**ex))
            _startup_db.commit()
            logger.info(f"Seeded {len(new_exchanges)} new crypto exchanges.")

        # Seed default institutions (NPS fund managers, NPS CRAs, insurance providers)
        from app.models.institution import InstitutionMaster
        existing_institutions = {
            (r.name, r.category)
            for r in _startup_db.query(InstitutionMaster.name, InstitutionMaster.category).all()
        }
        DEFAULT_INSTITUTIONS = [
            # NPS Fund Managers
            {"name": "sbi_pension_funds", "display_label": "SBI Pension Funds", "category": "nps_fund_manager", "sort_order": 1},
            {"name": "lic_pension_fund", "display_label": "LIC Pension Fund", "category": "nps_fund_manager", "sort_order": 2},
            {"name": "uti_retirement", "display_label": "UTI Retirement Solutions", "category": "nps_fund_manager", "sort_order": 3},
            {"name": "icici_prudential_pension", "display_label": "ICICI Prudential Pension Fund", "category": "nps_fund_manager", "sort_order": 4},
            {"name": "hdfc_pension", "display_label": "HDFC Pension Management", "category": "nps_fund_manager", "sort_order": 5},
            {"name": "kotak_pension", "display_label": "Kotak Mahindra Pension Fund", "category": "nps_fund_manager", "sort_order": 6},
            {"name": "aditya_birla_pension", "display_label": "Aditya Birla Sun Life Pension", "category": "nps_fund_manager", "sort_order": 7},
            {"name": "tata_pension", "display_label": "Tata Pension Management", "category": "nps_fund_manager", "sort_order": 8},
            {"name": "axis_pension", "display_label": "Axis Pension Fund Management", "category": "nps_fund_manager", "sort_order": 9},
            {"name": "dsp_pension", "display_label": "DSP Pension Fund Managers", "category": "nps_fund_manager", "sort_order": 10},
            # NPS CRAs
            {"name": "protean_cra", "display_label": "Protean CRA (formerly NSDL CRA)", "category": "nps_cra", "sort_order": 1},
            {"name": "kfintech_cra", "display_label": "KFintech CRA (formerly Karvy CRA)", "category": "nps_cra", "sort_order": 2},
            # Insurance Providers
            {"name": "lic", "display_label": "LIC", "category": "insurance_provider", "sort_order": 1},
            {"name": "sbi_life", "display_label": "SBI Life", "category": "insurance_provider", "sort_order": 2},
            {"name": "hdfc_life", "display_label": "HDFC Life", "category": "insurance_provider", "sort_order": 3},
            {"name": "icici_prudential", "display_label": "ICICI Prudential", "category": "insurance_provider", "sort_order": 4},
            {"name": "max_life", "display_label": "Max Life", "category": "insurance_provider", "sort_order": 5},
            {"name": "bajaj_allianz", "display_label": "Bajaj Allianz", "category": "insurance_provider", "sort_order": 6},
            {"name": "tata_aia", "display_label": "Tata AIA", "category": "insurance_provider", "sort_order": 7},
            {"name": "kotak_life", "display_label": "Kotak Life", "category": "insurance_provider", "sort_order": 8},
            {"name": "star_health", "display_label": "Star Health", "category": "insurance_provider", "sort_order": 9},
            {"name": "niva_bupa", "display_label": "Niva Bupa", "category": "insurance_provider", "sort_order": 10},
            {"name": "care_health", "display_label": "Care Health", "category": "insurance_provider", "sort_order": 11},
            {"name": "aditya_birla_health", "display_label": "Aditya Birla Health", "category": "insurance_provider", "sort_order": 12},
        ]
        new_institutions = [
            inst for inst in DEFAULT_INSTITUTIONS
            if (inst["name"], inst["category"]) not in existing_institutions
        ]
        if new_institutions:
            for inst in new_institutions:
                _startup_db.add(InstitutionMaster(**inst))
            _startup_db.commit()
            logger.info(f"Seeded {len(new_institutions)} new institutions.")

        # Seed default system expense categories
        from app.models.expense_category import ExpenseCategory
        existing_system_cats = {
            r.name for r in _startup_db.query(ExpenseCategory.name).filter(
                ExpenseCategory.is_system == True
            ).all()
        }
        DEFAULT_EXPENSE_CATEGORIES = [
            {"name": "Groceries", "description": "Food and household items", "icon": "🛒", "color": "#4CAF50", "is_income": False,
             "keywords": "grocery,supermarket,walmart,target,costco,whole foods,trader joe,safeway,kroger,food,vegetables,fruits,meat,dairy"},
            {"name": "Dining & Restaurants", "description": "Eating out, restaurants, cafes", "icon": "🍽️", "color": "#FF9800", "is_income": False,
             "keywords": "restaurant,cafe,coffee,starbucks,mcdonald,burger,pizza,food delivery,uber eats,doordash,grubhub,zomato,swiggy,dining,eatery"},
            {"name": "Transportation", "description": "Fuel, public transport, ride-sharing", "icon": "🚗", "color": "#2196F3", "is_income": False,
             "keywords": "uber,lyft,taxi,cab,fuel,gas,petrol,diesel,metro,bus,train,parking,toll,transport,ola"},
            {"name": "Utilities", "description": "Electricity, water, gas, internet", "icon": "💡", "color": "#FFC107", "is_income": False,
             "keywords": "electricity,water,gas,internet,broadband,wifi,phone bill,mobile,utility,power,energy"},
            {"name": "Rent & Mortgage", "description": "Housing payments", "icon": "🏠", "color": "#9C27B0", "is_income": False,
             "keywords": "rent,mortgage,housing,lease,landlord,property,apartment"},
            {"name": "Healthcare & Medical", "description": "Doctor visits, medicines, insurance", "icon": "⚕️", "color": "#F44336", "is_income": False,
             "keywords": "doctor,hospital,clinic,pharmacy,medicine,medical,health,insurance,dental,prescription,lab test"},
            {"name": "Entertainment", "description": "Movies, games, hobbies", "icon": "🎬", "color": "#E91E63", "is_income": False,
             "keywords": "movie,cinema,netflix,spotify,amazon prime,disney,gaming,xbox,playstation,entertainment,concert,theater"},
            {"name": "Shopping & Clothing", "description": "Clothes, accessories, personal items", "icon": "👕", "color": "#673AB7", "is_income": False,
             "keywords": "clothing,clothes,fashion,shoes,accessories,mall,amazon,flipkart,myntra,shopping,apparel"},
            {"name": "Education", "description": "Tuition, books, courses", "icon": "📚", "color": "#3F51B5", "is_income": False,
             "keywords": "school,college,university,tuition,books,course,education,training,udemy,coursera,learning"},
            {"name": "Fitness & Gym", "description": "Gym membership, sports, fitness", "icon": "💪", "color": "#FF5722", "is_income": False,
             "keywords": "gym,fitness,yoga,sports,workout,exercise,trainer,membership,health club"},
            {"name": "Travel & Vacation", "description": "Hotels, flights, vacation expenses", "icon": "✈️", "color": "#00BCD4", "is_income": False,
             "keywords": "hotel,flight,airline,booking,airbnb,travel,vacation,trip,tourism,resort"},
            {"name": "Insurance", "description": "Life, health, car insurance", "icon": "🛡️", "color": "#607D8B", "is_income": False,
             "keywords": "insurance,premium,policy,life insurance,health insurance,car insurance"},
            {"name": "Personal Care", "description": "Salon, spa, grooming", "icon": "💇", "color": "#E91E63", "is_income": False,
             "keywords": "salon,spa,haircut,beauty,grooming,cosmetics,skincare,barber"},
            {"name": "Subscriptions", "description": "Monthly subscriptions and memberships", "icon": "📱", "color": "#9E9E9E", "is_income": False,
             "keywords": "subscription,membership,monthly,recurring,netflix,spotify,amazon prime,youtube premium"},
            {"name": "Gifts & Donations", "description": "Gifts, charity, donations", "icon": "🎁", "color": "#FF4081", "is_income": False,
             "keywords": "gift,donation,charity,present,contribution,ngo"},
            {"name": "Pet Care", "description": "Pet food, vet, supplies", "icon": "🐾", "color": "#795548", "is_income": False,
             "keywords": "pet,dog,cat,vet,veterinary,pet food,pet supplies,grooming"},
            {"name": "Home Maintenance", "description": "Repairs, cleaning, maintenance", "icon": "🔧", "color": "#607D8B", "is_income": False,
             "keywords": "repair,maintenance,plumber,electrician,cleaning,handyman,home improvement"},
            {"name": "Taxes", "description": "Income tax, property tax", "icon": "📋", "color": "#455A64", "is_income": False,
             "keywords": "tax,income tax,property tax,tds,gst,irs"},
            {"name": "Salary & Income", "description": "Salary, wages, income", "icon": "💰", "color": "#4CAF50", "is_income": True,
             "keywords": "salary,wage,income,payment,paycheck,earnings,compensation"},
            {"name": "Investments & Returns", "description": "Investment returns, dividends, interest", "icon": "📈", "color": "#009688", "is_income": True,
             "keywords": "dividend,interest,investment,returns,profit,capital gain,mutual fund"},
        ]
        new_categories = [c for c in DEFAULT_EXPENSE_CATEGORIES if c["name"] not in existing_system_cats]
        if new_categories:
            for cat in new_categories:
                _startup_db.add(ExpenseCategory(**cat, is_system=True, is_active=True, user_id=None))
            _startup_db.commit()
            logger.info(f"Seeded {len(new_categories)} new system expense categories.")

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
