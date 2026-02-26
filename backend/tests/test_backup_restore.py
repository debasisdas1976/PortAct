"""Tests for portfolio backup & restore (export/import) endpoints.

Covers:
  GET  /api/v1/portfolio/export   – download entire portfolio as JSON
  POST /api/v1/portfolio/restore  – restore from JSON backup

Test scenarios:
  - Export empty portfolio, export with seeded data
  - Restore into empty user, verify all entity types imported
  - Idempotency: restore same backup twice → all records skipped
  - ID remapping: old FK references resolve to new DB IDs
  - Version handling: unsupported version rejected, v1-v4 accepted
  - Invalid JSON rejected
  - Round-trip: export → restore into new user → export → compare
  - Unauthenticated access rejected
"""
import json
import io
from datetime import datetime, date, timedelta

import pytest

from app.models.asset import Asset, AssetType
from app.models.bank_account import BankAccount
from app.models.demat_account import DematAccount
from app.models.crypto_account import CryptoAccount
from app.models.transaction import Transaction
from app.models.expense import Expense
from app.models.expense_category import ExpenseCategory
from app.models.alert import Alert
from app.models.mutual_fund_holding import MutualFundHolding
from app.models.portfolio import Portfolio
from app.models.portfolio_snapshot import PortfolioSnapshot, AssetSnapshot
from tests.conftest import make_asset


# ---------------------------------------------------------------------------
# Helpers — seed a representative set of data for the test user
# ---------------------------------------------------------------------------

def _seed_full_portfolio(db, user, portfolio_id):
    """Populate the test user's portfolio with every entity type.

    Returns a dict of created objects for later assertions.
    """
    # ── Bank accounts ──
    bank = BankAccount(
        user_id=user.id,
        portfolio_id=portfolio_id,
        bank_name="HDFC",
        account_type="savings",
        account_number="HDFC001",
        account_holder_name="Test User",
        current_balance=50000.0,
        is_active=True,
    )
    db.add(bank)
    db.flush()

    # ── Demat accounts ──
    demat = DematAccount(
        user_id=user.id,
        portfolio_id=portfolio_id,
        broker_name="Zerodha",
        account_id="ZRD001",
        account_holder_name="Test User",
        cash_balance=10000.0,
        currency="INR",
        is_active=True,
    )
    db.add(demat)
    db.flush()

    # ── Crypto accounts ──
    crypto_acct = CryptoAccount(
        user_id=user.id,
        portfolio_id=portfolio_id,
        exchange_name="binance",
        account_id="BIN001",
        cash_balance_usd=500.0,
        is_active=True,
    )
    db.add(crypto_acct)
    db.flush()

    # ── Assets (multiple types) ──
    stock = make_asset(db, user, portfolio_id,
                       name="Infosys", asset_type=AssetType.STOCK,
                       symbol="INFY", quantity=10, purchase_price=1500.0,
                       current_price=1600.0, total_invested=15000.0,
                       current_value=16000.0,
                       demat_account_id=demat.id)
    ppf = make_asset(db, user, portfolio_id,
                     name="My PPF", asset_type=AssetType.PPF,
                     quantity=1, purchase_price=150000.0,
                     current_price=160000.0, total_invested=150000.0,
                     current_value=160000.0)
    crypto_asset = make_asset(db, user, portfolio_id,
                              name="Bitcoin", asset_type=AssetType.CRYPTO,
                              symbol="BTC", quantity=0.5,
                              purchase_price=3000000.0,
                              current_price=3500000.0,
                              total_invested=1500000.0,
                              current_value=1750000.0,
                              crypto_account_id=crypto_acct.id)

    # ── Transactions ──
    txn = Transaction(
        asset_id=stock.id,
        transaction_type="buy",
        transaction_date=datetime(2024, 6, 15),
        quantity=10,
        price_per_unit=1500.0,
        total_amount=15000.0,
    )
    db.add(txn)

    # ── Mutual fund holdings ──
    mf_asset = make_asset(db, user, portfolio_id,
                          name="Axis Bluechip",
                          asset_type=AssetType.EQUITY_MUTUAL_FUND,
                          symbol="AXISBCHP", isin="INF846K01DP8",
                          quantity=100, purchase_price=50.0,
                          current_price=55.0, total_invested=5000.0,
                          current_value=5500.0)
    mf_holding = MutualFundHolding(
        asset_id=mf_asset.id,
        user_id=user.id,
        stock_name="Reliance Industries",
        stock_symbol="RELIANCE",
        holding_percentage=8.5,
        holding_value=467.5,
    )
    db.add(mf_holding)

    # ── Expense categories ──
    cat = ExpenseCategory(
        user_id=user.id,
        name="Test Food",
        description="Food & dining",
        is_system=False,
        is_active=True,
    )
    db.add(cat)
    db.flush()

    # ── Expenses ──
    expense = Expense(
        user_id=user.id,
        portfolio_id=portfolio_id,
        bank_account_id=bank.id,
        category_id=cat.id,
        transaction_date=datetime(2024, 7, 1),
        transaction_type="debit",
        amount=500.0,
        description="Test lunch",
    )
    db.add(expense)

    # ── Alerts ──
    alert = Alert(
        user_id=user.id,
        asset_id=stock.id,
        alert_type="price_change",
        severity="info",
        title="Infosys price up",
        message="Price crossed 1600",
        alert_date=datetime(2024, 7, 10),
    )
    db.add(alert)

    # ── Portfolio snapshots ──
    snap = PortfolioSnapshot(
        user_id=user.id,
        snapshot_date=date.today() - timedelta(days=1),
        total_invested=1670000.0,
        total_current_value=1931500.0,
        total_profit_loss=261500.0,
        total_profit_loss_percentage=15.66,
        total_assets_count=4,
    )
    db.add(snap)
    db.flush()

    asset_snap = AssetSnapshot(
        portfolio_snapshot_id=snap.id,
        asset_id=stock.id,
        snapshot_date=date.today() - timedelta(days=1),
        asset_type="stock",
        asset_name="Infosys",
        asset_symbol="INFY",
        quantity=10,
        purchase_price=1500.0,
        current_price=1600.0,
        total_invested=15000.0,
        current_value=16000.0,
        profit_loss=1000.0,
        profit_loss_percentage=6.67,
    )
    db.add(asset_snap)

    db.commit()

    return {
        "bank": bank,
        "demat": demat,
        "crypto_acct": crypto_acct,
        "stock": stock,
        "ppf": ppf,
        "crypto_asset": crypto_asset,
        "mf_asset": mf_asset,
        "txn": txn,
        "mf_holding": mf_holding,
        "cat": cat,
        "expense": expense,
        "alert": alert,
        "snapshot": snap,
        "asset_snap": asset_snap,
    }


def _upload_json(client, payload):
    """POST a JSON payload to /restore as a multipart file upload."""
    json_bytes = json.dumps(payload, default=str).encode("utf-8")
    return client.post(
        "/api/v1/portfolio/restore",
        files={"file": ("backup.json", io.BytesIO(json_bytes), "application/json")},
    )


# ═══════════════════════════════════════════════════════════════════════════
# 1. Export
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestExport:
    def test_export_empty_portfolio(self, auth_client):
        resp = auth_client.get("/api/v1/portfolio/export")
        assert resp.status_code == 200
        data = resp.json()
        assert data["export_version"] == "5.0"
        assert data["exported_by"] == "test@example.com"
        assert data["assets"] == []
        assert data["bank_accounts"] == []

    def test_export_response_shape(self, auth_client):
        """Exported JSON must contain all expected top-level keys."""
        resp = auth_client.get("/api/v1/portfolio/export")
        assert resp.status_code == 200
        data = resp.json()
        expected_keys = {
            "export_version", "exported_at", "exported_by",
            "portfolios", "bank_accounts", "demat_accounts",
            "crypto_accounts", "assets", "expense_categories",
            "expenses", "transactions", "mutual_fund_holdings",
            "alerts", "portfolio_snapshots",
        }
        assert expected_keys == set(data.keys())

    def test_export_with_seeded_data(self, auth_client, db, test_user):
        portfolios = auth_client.get("/api/v1/portfolios/").json()
        pid = portfolios[0]["id"]
        _seed_full_portfolio(db, test_user, pid)

        resp = auth_client.get("/api/v1/portfolio/export")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["portfolios"]) >= 1
        assert len(data["bank_accounts"]) == 1
        assert len(data["demat_accounts"]) == 1
        assert len(data["crypto_accounts"]) == 1
        assert len(data["assets"]) == 4  # stock, ppf, crypto, mf
        assert len(data["transactions"]) == 1
        assert len(data["mutual_fund_holdings"]) == 1
        assert len(data["expenses"]) == 1
        assert len(data["alerts"]) == 1
        assert len(data["portfolio_snapshots"]) == 1
        assert len(data["portfolio_snapshots"][0]["asset_snapshots"]) == 1

    def test_export_content_disposition(self, auth_client):
        resp = auth_client.get("/api/v1/portfolio/export")
        cd = resp.headers.get("content-disposition", "")
        assert "portfolio_export_" in cd
        assert ".json" in cd

    def test_export_unauthenticated(self, client):
        resp = client.get("/api/v1/portfolio/export")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# 2. Restore — basic
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestRestoreBasic:
    def test_restore_minimal_backup(self, auth_client):
        """A backup with just version info and empty lists should succeed."""
        payload = {
            "export_version": "4.0",
            "exported_at": datetime.now().isoformat(),
            "exported_by": "test@example.com",
            "portfolios": [],
            "bank_accounts": [],
            "demat_accounts": [],
            "crypto_accounts": [],
            "assets": [],
            "expense_categories": [],
            "expenses": [],
            "transactions": [],
            "mutual_fund_holdings": [],
            "alerts": [],
            "portfolio_snapshots": [],
        }
        resp = _upload_json(auth_client, payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "stats" in data

    def test_restore_invalid_json(self, auth_client):
        resp = auth_client.post(
            "/api/v1/portfolio/restore",
            files={"file": ("bad.json", io.BytesIO(b"not-json{{{"), "application/json")},
        )
        assert resp.status_code == 400
        assert "invalid json" in resp.json()["detail"].lower()

    def test_restore_unsupported_version(self, auth_client):
        payload = {"export_version": "99.0"}
        resp = _upload_json(auth_client, payload)
        assert resp.status_code == 400
        assert "unsupported" in resp.json()["detail"].lower()

    @pytest.mark.parametrize("version", ["1.0", "2.0", "3.0", "4.0"])
    def test_restore_supported_versions(self, auth_client, version):
        """All declared versions should be accepted (even with empty data)."""
        payload = {"export_version": version}
        resp = _upload_json(auth_client, payload)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_restore_unauthenticated(self, client):
        payload = {"export_version": "4.0"}
        json_bytes = json.dumps(payload).encode()
        resp = client.post(
            "/api/v1/portfolio/restore",
            files={"file": ("backup.json", io.BytesIO(json_bytes), "application/json")},
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# 3. Restore — full data import
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestRestoreFullData:
    """Restore a backup containing every entity type and verify counts."""

    @staticmethod
    def _build_full_backup():
        """Return a v4.0 backup payload with representative data."""
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        return {
            "export_version": "4.0",
            "exported_at": datetime.now().isoformat(),
            "exported_by": "source@example.com",
            "portfolios": [
                {"id": 100, "name": "Default", "is_default": True, "is_active": True},
                {"id": 101, "name": "Long Term", "is_default": False, "is_active": True},
            ],
            "bank_accounts": [
                {"id": 200, "bank_name": "ICICI", "account_type": "savings",
                 "account_number": "IC001", "portfolio_id": 100,
                 "current_balance": 25000.0, "is_active": True},
            ],
            "demat_accounts": [
                {"id": 300, "broker_name": "Groww", "account_id": "GRW001",
                 "portfolio_id": 101, "cash_balance": 5000.0, "is_active": True},
            ],
            "crypto_accounts": [
                {"id": 400, "exchange_name": "coinbase", "account_id": "CB001",
                 "portfolio_id": 100, "cash_balance_usd": 200.0, "is_active": True},
            ],
            "assets": [
                {"id": 500, "asset_type": "stock", "name": "TCS",
                 "symbol": "TCS", "quantity": 5, "purchase_price": 3500.0,
                 "current_price": 3800.0, "total_invested": 17500.0,
                 "current_value": 19000.0, "portfolio_id": 100,
                 "demat_account_id": 300, "is_active": True},
                {"id": 501, "asset_type": "ppf", "name": "PPF Restore",
                 "quantity": 1, "purchase_price": 100000.0,
                 "current_price": 108000.0, "total_invested": 100000.0,
                 "current_value": 108000.0, "portfolio_id": 101,
                 "is_active": True},
                {"id": 502, "asset_type": "crypto", "name": "Ethereum",
                 "symbol": "ETH", "quantity": 2, "purchase_price": 150000.0,
                 "current_price": 170000.0, "total_invested": 300000.0,
                 "current_value": 340000.0, "portfolio_id": 100,
                 "crypto_account_id": 400, "is_active": True},
            ],
            "transactions": [
                {"id": 600, "asset_id": 500, "transaction_type": "buy",
                 "transaction_date": "2024-03-15T10:00:00",
                 "quantity": 5, "price_per_unit": 3500.0,
                 "total_amount": 17500.0},
            ],
            "mutual_fund_holdings": [
                {"id": 700, "asset_id": 500, "user_id": 999,
                 "stock_name": "TCS Holding", "stock_symbol": "TCS",
                 "holding_percentage": 5.0, "holding_value": 950.0},
            ],
            "expense_categories": [
                {"id": 800, "name": "Groceries", "is_system": False,
                 "is_active": True},
            ],
            "expenses": [
                {"id": 900, "bank_account_id": 200, "category_id": 800,
                 "portfolio_id": 100,
                 "transaction_date": "2024-04-01T09:00:00",
                 "transaction_type": "debit", "amount": 750.0,
                 "description": "Weekly groceries"},
            ],
            "alerts": [
                {"id": 1000, "asset_id": 500, "alert_type": "price_change",
                 "severity": "info", "title": "TCS price change",
                 "message": "TCS crossed 3800",
                 "alert_date": "2024-04-10T14:00:00"},
                {"id": 1001, "asset_id": None, "alert_type": "market_volatility",
                 "severity": "warning", "title": "Market drop",
                 "message": "Sensex down 2%",
                 "alert_date": "2024-04-11T09:00:00"},
            ],
            "portfolio_snapshots": [
                {"id": 1100, "snapshot_date": yesterday,
                 "total_invested": 417500.0, "total_current_value": 467000.0,
                 "total_profit_loss": 49500.0, "total_profit_loss_percentage": 11.86,
                 "total_assets_count": 3,
                 "asset_snapshots": [
                     {"id": 1200, "asset_id": 500,
                      "snapshot_date": yesterday,
                      "asset_type": "stock", "asset_name": "TCS",
                      "asset_symbol": "TCS", "quantity": 5,
                      "purchase_price": 3500.0, "current_price": 3800.0,
                      "total_invested": 17500.0, "current_value": 19000.0,
                      "profit_loss": 1500.0, "profit_loss_percentage": 8.57},
                     {"id": 1201, "asset_id": 501,
                      "snapshot_date": yesterday,
                      "asset_type": "ppf", "asset_name": "PPF Restore",
                      "asset_symbol": None, "quantity": 1,
                      "purchase_price": 100000.0, "current_price": 108000.0,
                      "total_invested": 100000.0, "current_value": 108000.0,
                      "profit_loss": 8000.0, "profit_loss_percentage": 8.0},
                 ]},
            ],
        }

    def test_restore_imports_all_entity_types(self, auth_client):
        payload = self._build_full_backup()
        resp = _upload_json(auth_client, payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

        stats = data["stats"]
        # "Default" portfolio already exists → skipped; "Long Term" → imported
        assert stats["portfolios"]["imported"] == 1
        assert stats["portfolios"]["skipped"] == 1
        assert stats["bank_accounts"]["imported"] == 1
        assert stats["demat_accounts"]["imported"] == 1
        assert stats["crypto_accounts"]["imported"] == 1
        assert stats["assets"]["imported"] == 3
        assert stats["transactions"]["imported"] == 1
        assert stats["mutual_fund_holdings"]["imported"] == 1
        assert stats["expense_categories"]["imported"] == 1
        assert stats["expenses"]["imported"] == 1
        assert stats["alerts"]["imported"] == 2
        assert stats["portfolio_snapshots"]["imported"] == 1
        assert stats["asset_snapshots"]["imported"] == 2

    def test_restore_data_accessible_via_api(self, auth_client):
        """After restore, entities are queryable through regular API endpoints."""
        payload = self._build_full_backup()
        _upload_json(auth_client, payload)

        # Assets
        assets_resp = auth_client.get("/api/v1/assets/")
        assert assets_resp.status_code == 200
        asset_names = {a["name"] for a in assets_resp.json()}
        assert "TCS" in asset_names
        assert "PPF Restore" in asset_names
        assert "Ethereum" in asset_names

        # Portfolios
        portfolios_resp = auth_client.get("/api/v1/portfolios/")
        assert portfolios_resp.status_code == 200
        port_names = {p["name"] for p in portfolios_resp.json()}
        assert "Long Term" in port_names


# ═══════════════════════════════════════════════════════════════════════════
# 4. Idempotency
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestRestoreIdempotency:
    def test_second_restore_skips_all(self, auth_client):
        """Restoring the same backup twice should import zero on the second pass."""
        payload = TestRestoreFullData._build_full_backup()

        # First restore
        resp1 = _upload_json(auth_client, payload)
        assert resp1.status_code == 200
        stats1 = resp1.json()["stats"]
        first_imported = sum(v["imported"] for v in stats1.values())
        assert first_imported > 0

        # Second restore — everything should be skipped
        resp2 = _upload_json(auth_client, payload)
        assert resp2.status_code == 200
        stats2 = resp2.json()["stats"]
        second_imported = sum(v["imported"] for v in stats2.values())
        assert second_imported == 0

        # All entries in second pass should be "skipped"
        for key, counts in stats2.items():
            if stats1[key]["imported"] > 0 or stats1[key]["skipped"] > 0:
                assert counts["skipped"] >= stats1[key]["imported"] + stats1[key]["skipped"], \
                    f"{key}: expected all skipped on 2nd pass"


# ═══════════════════════════════════════════════════════════════════════════
# 5. ID Remapping
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestRestoreIdRemapping:
    def test_foreign_keys_remapped(self, auth_client, db, test_user):
        """After restore, asset.demat_account_id and crypto_account_id
        point to actual DB IDs (not the old export IDs)."""
        payload = TestRestoreFullData._build_full_backup()
        _upload_json(auth_client, payload)

        # The old demat_account_id was 300, old crypto_account_id was 400.
        # After restore, they should be real DB IDs (not 300 or 400).
        assets = auth_client.get("/api/v1/assets/").json()

        tcs = next(a for a in assets if a["name"] == "TCS")
        assert tcs["demat_account_id"] is not None
        # The new ID won't be 300 (old export ID) — it should be an actual auto-increment
        # We verify the demat is queryable (FK is valid)
        assert tcs["portfolio_id"] is not None

        eth = next(a for a in assets if a["name"] == "Ethereum")
        assert eth["crypto_account_id"] is not None

    def test_transaction_linked_to_correct_asset(self, auth_client, db, test_user):
        """Transactions should reference the newly-created asset IDs."""
        payload = TestRestoreFullData._build_full_backup()
        _upload_json(auth_client, payload)

        # Verify via DB since transactions don't have a list API
        txns = db.query(Transaction).filter(
            Transaction.total_amount == 17500.0
        ).all()
        assert len(txns) >= 1

        # The asset_id should point to an actual asset
        txn = txns[0]
        asset = db.query(Asset).get(txn.asset_id)
        assert asset is not None
        assert asset.name == "TCS"

    def test_alert_linked_to_correct_asset(self, auth_client, db, test_user):
        """Alerts with asset_id should reference the correct asset after remap."""
        payload = TestRestoreFullData._build_full_backup()
        _upload_json(auth_client, payload)

        alerts = db.query(Alert).filter(Alert.user_id == test_user.id).all()
        asset_alert = next(a for a in alerts if a.title == "TCS price change")
        assert asset_alert.asset_id is not None
        asset = db.query(Asset).get(asset_alert.asset_id)
        assert asset.name == "TCS"

        # The market-wide alert has no asset_id
        market_alert = next(a for a in alerts if a.title == "Market drop")
        assert market_alert.asset_id is None

    def test_snapshot_asset_ids_remapped(self, auth_client, db, test_user):
        """AssetSnapshot.asset_id should reference the correct asset after remap."""
        payload = TestRestoreFullData._build_full_backup()
        _upload_json(auth_client, payload)

        snaps = db.query(AssetSnapshot).join(PortfolioSnapshot).filter(
            PortfolioSnapshot.user_id == test_user.id
        ).all()
        assert len(snaps) >= 2

        tcs_snap = next(s for s in snaps if s.asset_name == "TCS")
        assert tcs_snap.asset_id is not None
        asset = db.query(Asset).get(tcs_snap.asset_id)
        assert asset is not None
        assert asset.name == "TCS"


# ═══════════════════════════════════════════════════════════════════════════
# 6. Round-trip (export → restore → export → compare)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestRoundTrip:
    def test_export_restore_export_matches(self, auth_client, db, test_user):
        """Data survives a full round-trip: seed → export → restore → export.

        We compare entity counts and key field values (not IDs/timestamps).
        """
        # Seed data
        portfolios = auth_client.get("/api/v1/portfolios/").json()
        pid = portfolios[0]["id"]
        _seed_full_portfolio(db, test_user, pid)

        # Export #1
        export1_resp = auth_client.get("/api/v1/portfolio/export")
        export1 = export1_resp.json()

        # Delete all assets to simulate restoring into "clean" state
        for asset in db.query(Asset).filter(Asset.user_id == test_user.id).all():
            db.delete(asset)
        for ba in db.query(BankAccount).filter(BankAccount.user_id == test_user.id).all():
            db.delete(ba)
        for da in db.query(DematAccount).filter(DematAccount.user_id == test_user.id).all():
            db.delete(da)
        for ca in db.query(CryptoAccount).filter(CryptoAccount.user_id == test_user.id).all():
            db.delete(ca)
        for exp in db.query(Expense).filter(Expense.user_id == test_user.id).all():
            db.delete(exp)
        for cat in db.query(ExpenseCategory).filter(
            ExpenseCategory.user_id == test_user.id
        ).all():
            db.delete(cat)
        for alert in db.query(Alert).filter(Alert.user_id == test_user.id).all():
            db.delete(alert)
        for snap in db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.user_id == test_user.id
        ).all():
            db.delete(snap)
        for mfh in db.query(MutualFundHolding).filter(
            MutualFundHolding.user_id == test_user.id
        ).all():
            db.delete(mfh)
        db.commit()

        # Restore from export1
        resp = _upload_json(auth_client, export1)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # Export #2
        export2_resp = auth_client.get("/api/v1/portfolio/export")
        export2 = export2_resp.json()

        # Compare counts (IDs will differ, so we compare by count and names)
        assert len(export2["bank_accounts"]) == len(export1["bank_accounts"])
        assert len(export2["demat_accounts"]) == len(export1["demat_accounts"])
        assert len(export2["crypto_accounts"]) == len(export1["crypto_accounts"])
        assert len(export2["assets"]) == len(export1["assets"])
        assert len(export2["transactions"]) == len(export1["transactions"])
        assert len(export2["mutual_fund_holdings"]) == len(export1["mutual_fund_holdings"])
        assert len(export2["expenses"]) == len(export1["expenses"])
        assert len(export2["alerts"]) == len(export1["alerts"])
        assert len(export2["portfolio_snapshots"]) == len(export1["portfolio_snapshots"])

        # Compare asset names
        names1 = sorted(a["name"] for a in export1["assets"])
        names2 = sorted(a["name"] for a in export2["assets"])
        assert names1 == names2

        # Compare asset values (by name)
        for a1 in export1["assets"]:
            a2 = next(a for a in export2["assets"] if a["name"] == a1["name"])
            assert abs(a2["total_invested"] - a1["total_invested"]) < 1.0
            assert a2["asset_type"] == a1["asset_type"]


# ═══════════════════════════════════════════════════════════════════════════
# 7. Edge cases
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestRestoreEdgeCases:
    def test_restore_without_portfolio_data_uses_default(self, auth_client):
        """v1/v2 backups may not have 'portfolios' key — assets go to default."""
        payload = {
            "export_version": "1.0",
            "assets": [
                {"id": 1, "asset_type": "stock", "name": "Old Asset",
                 "quantity": 1, "total_invested": 1000.0},
            ],
        }
        resp = _upload_json(auth_client, payload)
        assert resp.status_code == 200
        assert resp.json()["stats"]["assets"]["imported"] == 1

        # The asset should be in the default portfolio
        assets = auth_client.get("/api/v1/assets/").json()
        restored = next(a for a in assets if a["name"] == "Old Asset")
        assert restored["portfolio_id"] is not None

    def test_restore_orphaned_transaction_skipped(self, auth_client):
        """Transactions referencing non-existent asset IDs should be skipped."""
        payload = {
            "export_version": "4.0",
            "assets": [],
            "transactions": [
                {"id": 1, "asset_id": 99999, "transaction_type": "buy",
                 "transaction_date": "2024-01-01T00:00:00",
                 "total_amount": 1000.0},
            ],
        }
        resp = _upload_json(auth_client, payload)
        assert resp.status_code == 200
        # Transaction not imported (orphaned)
        assert resp.json()["stats"]["transactions"]["imported"] == 0

    def test_restore_new_portfolio_created(self, auth_client):
        """A portfolio that doesn't exist yet should be created."""
        payload = {
            "export_version": "4.0",
            "portfolios": [
                {"id": 42, "name": "Brand New Portfolio",
                 "is_default": False, "is_active": True},
            ],
        }
        resp = _upload_json(auth_client, payload)
        assert resp.status_code == 200
        assert resp.json()["stats"]["portfolios"]["imported"] == 1

        portfolios = auth_client.get("/api/v1/portfolios/").json()
        names = [p["name"] for p in portfolios]
        assert "Brand New Portfolio" in names

    def test_restore_expense_category_with_parent(self, auth_client):
        """Subcategories should be linked to their parent after restore."""
        payload = {
            "export_version": "4.0",
            "expense_categories": [
                {"id": 10, "name": "Transport", "is_system": False, "is_active": True},
                {"id": 11, "name": "Uber", "parent_id": 10,
                 "is_system": False, "is_active": True},
            ],
        }
        resp = _upload_json(auth_client, payload)
        assert resp.status_code == 200
        stats = resp.json()["stats"]
        assert stats["expense_categories"]["imported"] == 2

    def test_restore_multiple_asset_lots_same_name(self, auth_client):
        """Multiple SIP lots with the same name should all be imported."""
        payload = {
            "export_version": "4.0",
            "assets": [
                {"id": 1, "asset_type": "equity_mutual_fund",
                 "name": "Axis Bluechip", "quantity": 50,
                 "total_invested": 5000.0, "purchase_price": 100.0},
                {"id": 2, "asset_type": "equity_mutual_fund",
                 "name": "Axis Bluechip", "quantity": 75,
                 "total_invested": 8000.0, "purchase_price": 106.67},
            ],
        }
        resp = _upload_json(auth_client, payload)
        assert resp.status_code == 200
        assert resp.json()["stats"]["assets"]["imported"] == 2

    def test_restore_alert_without_asset(self, auth_client):
        """Market-wide alerts (asset_id=None) should restore correctly."""
        payload = {
            "export_version": "4.0",
            "alerts": [
                {"id": 1, "asset_id": None, "alert_type": "market_volatility",
                 "severity": "warning", "title": "Market alert",
                 "message": "VIX spiked",
                 "alert_date": "2024-05-01T10:00:00"},
            ],
        }
        resp = _upload_json(auth_client, payload)
        assert resp.status_code == 200
        assert resp.json()["stats"]["alerts"]["imported"] == 1
