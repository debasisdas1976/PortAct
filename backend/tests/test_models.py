"""Unit tests for SQLAlchemy model methods and relationships."""
import pytest
from app.models.asset import Asset, AssetType
from app.models.user import User
from app.models.portfolio import Portfolio


@pytest.mark.unit
class TestAssetCalculateMetrics:
    def test_positive_return(self):
        asset = Asset(
            quantity=10.0,
            current_price=120.0,
            total_invested=1000.0,
        )
        asset.calculate_metrics()
        assert asset.current_value == 1200.0
        assert asset.profit_loss == 200.0
        assert asset.profit_loss_percentage == pytest.approx(20.0)

    def test_negative_return(self):
        asset = Asset(
            quantity=10.0,
            current_price=80.0,
            total_invested=1000.0,
        )
        asset.calculate_metrics()
        assert asset.current_value == 800.0
        assert asset.profit_loss == -200.0
        assert asset.profit_loss_percentage == pytest.approx(-20.0)

    def test_zero_investment(self):
        asset = Asset(
            quantity=5.0,
            current_price=50.0,
            total_invested=0.0,
        )
        asset.calculate_metrics()
        assert asset.profit_loss == 0.0
        assert asset.profit_loss_percentage == 0.0


@pytest.mark.unit
class TestModelRelationships:
    def test_user_has_expected_relationships(self):
        """Verify the User model declares the key relationship properties."""
        rel_names = {r.key for r in User.__mapper__.relationships}
        expected = {"assets", "portfolios", "bank_accounts", "demat_accounts",
                    "crypto_accounts", "statements", "alerts", "expenses"}
        assert expected.issubset(rel_names)

    def test_portfolio_has_expected_fields(self):
        columns = {c.name for c in Portfolio.__table__.columns}
        expected = {"id", "user_id", "name", "is_default", "is_active"}
        assert expected.issubset(columns)
