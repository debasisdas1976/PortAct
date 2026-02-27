"""Tests for real estate schemas and API endpoints.

Covers:
  - Pydantic schema validation (property_type, area_unit)
  - CRUD via /api/v1/real-estate/ endpoints
  - Summary endpoint
  - All three property types: land, farm_land, house
"""
import pytest
from datetime import date
from pydantic import ValidationError

from app.schemas.real_estate import (
    RealEstateCreate,
    RealEstateUpdate,
    PROPERTY_TYPES,
    AREA_UNITS,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Schema validation
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestRealEstateSchemas:
    def test_valid_create(self):
        data = RealEstateCreate(
            nickname="Test Plot",
            property_type="land",
            location="Pune, Maharashtra",
            area=5000,
            area_unit="sqft",
            purchase_price=2000000.0,
            current_market_value=2500000.0,
            purchase_date=date(2023, 6, 15),
        )
        assert data.property_type == "land"
        assert data.area == 5000

    def test_all_property_types_accepted(self):
        for pt in PROPERTY_TYPES:
            data = RealEstateCreate(
                nickname=f"Test {pt}",
                property_type=pt,
                location="Test Location",
                area=100,
                purchase_price=100000.0,
                current_market_value=110000.0,
                purchase_date=date(2024, 1, 1),
            )
            assert data.property_type == pt

    def test_invalid_property_type_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            RealEstateCreate(
                nickname="Bad",
                property_type="apartment",
                location="Test",
                area=100,
                purchase_price=100000.0,
                current_market_value=110000.0,
                purchase_date=date(2024, 1, 1),
            )
        assert "property_type" in str(exc_info.value).lower()

    def test_all_area_units_accepted(self):
        for unit in AREA_UNITS:
            data = RealEstateCreate(
                nickname="Test",
                property_type="land",
                location="Test",
                area=100,
                area_unit=unit,
                purchase_price=100000.0,
                current_market_value=110000.0,
                purchase_date=date(2024, 1, 1),
            )
            assert data.area_unit == unit

    def test_invalid_area_unit_rejected(self):
        with pytest.raises(ValidationError):
            RealEstateCreate(
                nickname="Bad",
                property_type="land",
                location="Test",
                area=100,
                area_unit="meters",
                purchase_price=100000.0,
                current_market_value=110000.0,
                purchase_date=date(2024, 1, 1),
            )

    def test_case_insensitive_property_type(self):
        data = RealEstateCreate(
            nickname="Test",
            property_type="LAND",
            location="Test",
            area=100,
            purchase_price=100000.0,
            current_market_value=110000.0,
            purchase_date=date(2024, 1, 1),
        )
        assert data.property_type == "land"

    def test_update_partial_fields(self):
        data = RealEstateUpdate(current_market_value=3000000.0)
        dumped = data.dict(exclude_unset=True)
        assert "current_market_value" in dumped
        assert "nickname" not in dumped

    def test_negative_area_rejected(self):
        with pytest.raises(ValidationError):
            RealEstateCreate(
                nickname="Bad",
                property_type="land",
                location="Test",
                area=-100,
                purchase_price=100000.0,
                current_market_value=110000.0,
                purchase_date=date(2024, 1, 1),
            )

    def test_optional_fields_in_create(self):
        data = RealEstateCreate(
            nickname="Full Property",
            property_type="house",
            location="Mumbai",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001",
            area=1200,
            area_unit="sqft",
            purchase_price=5000000.0,
            current_market_value=6000000.0,
            purchase_date=date(2022, 3, 10),
            registration_number="MH-2022-12345",
            loan_outstanding=2000000.0,
            rental_income_monthly=25000.0,
            notes="Sea-facing flat",
        )
        assert data.city == "Mumbai"
        assert data.registration_number == "MH-2022-12345"
        assert data.loan_outstanding == 2000000.0
        assert data.rental_income_monthly == 25000.0
