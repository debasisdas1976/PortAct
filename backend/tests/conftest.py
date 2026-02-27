"""Shared fixtures for the PortAct backend test suite.

Environment variables are set BEFORE any app imports so that
``app.core.config.Settings`` picks up test-safe defaults.

The real ``app.core.database`` module creates an engine at import time
with pool_size/max_overflow args that are incompatible with SQLite.
We set DATABASE_URL to a dummy PG URL so that import succeeds (the real
engine is never used — we override ``get_db``), then create a separate
SQLite test engine for actual test queries.
"""
import os

# ── Set test environment BEFORE any app imports ──────────────────────────
# Use a dummy PG URL so database.py's create_engine (with pool_size etc.)
# doesn't fail.  The engine won't connect until a query is made, and we
# never use it — every test overrides get_db with the test session.
os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get("TEST_DATABASE_URL", "postgresql://localhost/portact_test_dummy"),
)
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
from app.core.security import create_access_token, get_password_hash  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.portfolio import Portfolio  # noqa: E402
from app.models.asset import Asset, AssetType  # noqa: E402
from app.models.asset_type_master import AssetTypeMaster  # noqa: E402

# ── Test DB engine (always SQLite in-memory for local, PG in CI) ─────────
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite:///")

if TEST_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── No-op lifespan to bypass PG-specific startup queries on SQLite ──────
@asynccontextmanager
async def _noop_lifespan(app):
    yield


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once and seed asset_types master data.

    The asset_types table must be populated before any test creates an
    Asset row, because assets.asset_type has a FK to asset_types.name.
    SQLite ignores FK constraints by default (so local tests pass), but
    PostgreSQL enforces them (causing CI failures without this seed).
    """
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Seed asset_types master table (session-scoped, committed once)
    session = TestingSessionLocal()
    try:
        if session.query(AssetTypeMaster).count() == 0:
            for i, at in enumerate(AssetType, start=1):
                session.add(AssetTypeMaster(
                    name=at.value,
                    display_label=at.value.replace("_", " ").title(),
                    category="General",
                    sort_order=i,
                ))
            session.commit()
    finally:
        session.close()

    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Yield a fresh DB session; rollback after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    """FastAPI TestClient with DB override and no-op lifespan."""
    from app.main import app

    # Replace the real lifespan with a no-op for SQLite
    app.router.lifespan_context = _noop_lifespan

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db) -> User:
    """Create and return a test user with a default portfolio."""
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=get_password_hash("TestPass123!"),
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.flush()

    portfolio = Portfolio(
        user_id=user.id,
        name="Default",
        is_default=True,
    )
    db.add(portfolio)
    db.flush()

    return user


@pytest.fixture
def auth_headers(test_user) -> dict:
    """Return Authorization headers for the test user."""
    token = create_access_token(
        data={"sub": test_user.username, "user_id": test_user.id}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_client(client, db, test_user, auth_headers):
    """TestClient that is already authenticated."""
    client.headers.update(auth_headers)
    return client


def make_asset(db, user, portfolio_id, **overrides):
    """Factory helper for creating test assets."""
    defaults = dict(
        user_id=user.id,
        portfolio_id=portfolio_id,
        asset_type=AssetType.STOCK,
        name="Test Stock",
        symbol="TST",
        quantity=10.0,
        purchase_price=100.0,
        current_price=110.0,
        total_invested=1000.0,
        current_value=1100.0,
        is_active=True,
    )
    defaults.update(overrides)
    asset = Asset(**defaults)
    db.add(asset)
    db.flush()
    return asset
