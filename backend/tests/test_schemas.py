"""Unit tests for Pydantic schema validation."""
import pytest
from pydantic import ValidationError
from app.schemas.user import UserCreate
from app.schemas.asset import AssetCreate
from app.schemas.portfolio import PortfolioCreate
from app.models.asset import AssetType


@pytest.mark.unit
class TestUserCreateSchema:
    def test_valid_user(self):
        user = UserCreate(
            email="valid@example.com",
            username="validuser",
            full_name="Valid User",
            password="SecurePass1!",
        )
        assert user.email == "valid@example.com"
        assert user.username == "validuser"

    def test_short_password_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="x@example.com",
                username="xuser",
                password="short",
            )
        assert "password" in str(exc_info.value).lower() or "min_length" in str(exc_info.value).lower()

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            UserCreate(
                email="not-an-email",
                username="xuser",
                password="ValidPass1!",
            )


@pytest.mark.unit
class TestAssetCreateSchema:
    def test_valid_asset(self):
        asset = AssetCreate(
            asset_type=AssetType.STOCK,
            name="HDFC Bank",
            symbol="HDFCBANK",
            quantity=10.0,
            purchase_price=1500.0,
            total_invested=15000.0,
        )
        assert asset.asset_type == AssetType.STOCK
        assert asset.name == "HDFC Bank"

    def test_negative_quantity_rejected(self):
        with pytest.raises(ValidationError):
            AssetCreate(
                asset_type=AssetType.STOCK,
                name="Bad Asset",
                quantity=-5.0,
            )

    def test_case_insensitive_asset_type(self):
        """UpperStrEnum allows case-insensitive lookups."""
        asset = AssetCreate(
            asset_type="STOCK",  # uppercase string
            name="Test",
        )
        assert asset.asset_type == AssetType.STOCK


@pytest.mark.unit
class TestPortfolioCreateSchema:
    def test_valid_portfolio(self):
        p = PortfolioCreate(name="My Portfolio")
        assert p.name == "My Portfolio"

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            PortfolioCreate(name="")
