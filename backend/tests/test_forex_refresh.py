"""Unit tests for the forex refresh service.

Tests the internal routing logic and price recalculation without hitting
real exchange rate APIs.  We mock get_usd_to_inr_rate() and
get_all_rates_to_inr() to provide deterministic rates.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.models.asset import Asset, AssetType
from app.models.crypto_account import CryptoAccount
from app.models.demat_account import DematAccount
from app.services.forex_refresh_service import (
    _refresh_asset_forex,
    _refresh_demat_cash_usd,
    _refresh_crypto_cash_usd,
    _USD_PRICED_TYPES,
    _CONDITIONALLY_USD_TYPES,
    _MULTI_CURRENCY_TYPES,
)


MOCK_USD_INR = 85.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_asset(asset_type, **kwargs):
    """Create an in-memory Asset with sensible defaults."""
    defaults = dict(
        asset_type=asset_type,
        name="Test",
        symbol="TST",
        quantity=10.0,
        purchase_price=100.0,
        current_price=100.0,
        total_invested=1000.0,
        current_value=1000.0,
        is_active=True,
        details={},
    )
    defaults.update(kwargs)
    asset = Asset(**defaults)
    return asset


# ═══════════════════════════════════════════════════════════════════════════
# 1. Routing sets sanity
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestRoutingSets:
    def test_usd_priced_types(self):
        assert AssetType.CRYPTO in _USD_PRICED_TYPES
        assert AssetType.US_STOCK in _USD_PRICED_TYPES

    def test_conditionally_usd_types(self):
        assert AssetType.ESOP in _CONDITIONALLY_USD_TYPES
        assert AssetType.RSU in _CONDITIONALLY_USD_TYPES

    def test_multi_currency_types(self):
        assert AssetType.CASH in _MULTI_CURRENCY_TYPES

    def test_no_overlap(self):
        assert _USD_PRICED_TYPES.isdisjoint(_CONDITIONALLY_USD_TYPES)
        assert _USD_PRICED_TYPES.isdisjoint(_MULTI_CURRENCY_TYPES)
        assert _CONDITIONALLY_USD_TYPES.isdisjoint(_MULTI_CURRENCY_TYPES)


# ═══════════════════════════════════════════════════════════════════════════
# 2. USD-priced assets (crypto, us_stock)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestUsdPricedAssets:
    @patch("app.services.forex_refresh_service.get_all_rates_to_inr", return_value={})
    def test_crypto_price_conversion(self, mock_rates):
        crypto = _make_asset(
            AssetType.CRYPTO,
            name="Bitcoin", symbol="BTC",
            quantity=0.5,
            total_invested=2000000.0,
            details={"price_usd": 67000.0},
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [crypto]

        stats = _refresh_asset_forex(db, MOCK_USD_INR)

        assert stats["updated"] == 1
        assert stats["skipped"] == 0
        expected_price = 67000.0 * MOCK_USD_INR
        assert crypto.current_price == pytest.approx(expected_price)
        assert crypto.current_value == pytest.approx(0.5 * expected_price)
        assert crypto.details["usd_to_inr_rate"] == MOCK_USD_INR

    @patch("app.services.forex_refresh_service.get_all_rates_to_inr", return_value={})
    def test_us_stock_price_conversion(self, mock_rates):
        stock = _make_asset(
            AssetType.US_STOCK,
            name="AAPL", symbol="AAPL",
            quantity=5,
            total_invested=50000.0,
            details={"price_usd": 180.0},
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [stock]

        stats = _refresh_asset_forex(db, MOCK_USD_INR)

        assert stats["updated"] == 1
        expected_price = 180.0 * MOCK_USD_INR
        assert stock.current_price == pytest.approx(expected_price)

    @patch("app.services.forex_refresh_service.get_all_rates_to_inr", return_value={})
    def test_missing_price_usd_skipped(self, mock_rates):
        crypto = _make_asset(
            AssetType.CRYPTO,
            name="No Price", symbol="NOP",
            details={},
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [crypto]

        stats = _refresh_asset_forex(db, MOCK_USD_INR)

        assert stats["skipped"] == 1
        assert stats["updated"] == 0


# ═══════════════════════════════════════════════════════════════════════════
# 3. Conditionally USD (ESOP, RSU)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestConditionallyUsd:
    @patch("app.services.forex_refresh_service.get_all_rates_to_inr", return_value={})
    def test_rsu_usd_converted(self, mock_rates):
        rsu = _make_asset(
            AssetType.RSU,
            name="Google RSU", symbol="GOOG",
            quantity=20,
            total_invested=200000.0,
            details={"price_usd": 175.0, "currency": "USD"},
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [rsu]

        stats = _refresh_asset_forex(db, MOCK_USD_INR)

        assert stats["updated"] == 1
        expected = 175.0 * MOCK_USD_INR
        assert rsu.current_price == pytest.approx(expected)

    @patch("app.services.forex_refresh_service.get_all_rates_to_inr", return_value={})
    def test_esop_inr_skipped(self, mock_rates):
        esop = _make_asset(
            AssetType.ESOP,
            name="Indian ESOP", symbol="IND",
            details={"currency": "INR", "price_usd": 100},
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [esop]

        stats = _refresh_asset_forex(db, MOCK_USD_INR)

        assert stats["skipped"] == 1
        assert stats["updated"] == 0

    @patch("app.services.forex_refresh_service.get_all_rates_to_inr", return_value={})
    def test_rsu_no_currency_defaults_to_inr_skipped(self, mock_rates):
        """RSU without currency key defaults to INR — should be skipped."""
        rsu = _make_asset(
            AssetType.RSU,
            name="INR RSU", symbol="IRSU",
            details={"price_usd": 50.0},
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [rsu]

        stats = _refresh_asset_forex(db, MOCK_USD_INR)
        assert stats["skipped"] == 1


# ═══════════════════════════════════════════════════════════════════════════
# 4. Multi-currency CASH
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestMultiCurrencyCash:
    @patch("app.services.forex_refresh_service.get_all_rates_to_inr")
    def test_eur_cash_converted(self, mock_rates):
        mock_rates.return_value = {"EUR": 92.5}
        cash = _make_asset(
            AssetType.CASH,
            name="EUR Locker", symbol="EUR",
            quantity=1,
            details={"currency": "EUR", "original_amount": 5000},
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [cash]

        stats = _refresh_asset_forex(db, MOCK_USD_INR)

        assert stats["updated"] == 1
        expected = 5000 * 92.5
        assert cash.current_price == pytest.approx(expected)

    @patch("app.services.forex_refresh_service.get_all_rates_to_inr", return_value={})
    def test_inr_cash_skipped(self, mock_rates):
        cash = _make_asset(
            AssetType.CASH,
            name="INR Cash",
            details={"currency": "INR", "original_amount": 50000},
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [cash]

        stats = _refresh_asset_forex(db, MOCK_USD_INR)
        assert stats["skipped"] == 1

    @patch("app.services.forex_refresh_service.get_all_rates_to_inr", return_value={})
    def test_usd_cash_uses_usd_rate(self, mock_rates):
        cash = _make_asset(
            AssetType.CASH,
            name="USD Cash", symbol="USD",
            quantity=1,
            details={"currency": "USD", "original_amount": 1000},
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [cash]

        stats = _refresh_asset_forex(db, MOCK_USD_INR)

        assert stats["updated"] == 1
        assert cash.current_price == pytest.approx(1000 * MOCK_USD_INR)


# ═══════════════════════════════════════════════════════════════════════════
# 5. Account cash refresh
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestAccountCashRefresh:
    def test_demat_usd_cash_refreshed(self):
        acct = DematAccount(
            broker_name="Vested",
            account_id="VSD001",
            currency="USD",
            cash_balance_usd=250.0,
            cash_balance=0.0,
            is_active=True,
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [acct]

        stats = _refresh_demat_cash_usd(db, MOCK_USD_INR)

        assert stats["updated"] == 1
        assert acct.cash_balance == pytest.approx(250.0 * MOCK_USD_INR)

    def test_crypto_usd_cash_refreshed(self):
        acct = CryptoAccount(
            exchange_name="Binance",
            account_id="BIN001",
            cash_balance_usd=500.0,
            cash_balance_inr=0.0,
            is_active=True,
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [acct]

        stats = _refresh_crypto_cash_usd(db, MOCK_USD_INR)

        assert stats["updated"] == 1
        assert acct.cash_balance_inr == pytest.approx(500.0 * MOCK_USD_INR)
