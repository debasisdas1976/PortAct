"""Tests for asset category master table and API endpoints.

Covers:
  - Schema validation
  - GET /asset-categories/ endpoint
  - GET /asset-categories/{id} endpoint
  - PUT /asset-categories/{id} endpoint
  - Category validation on asset_types PUT
"""
import pytest

from app.models.asset_category_master import AssetCategoryMaster
from app.schemas.asset_category_master import AssetCategoryMasterUpdate, AssetCategoryMasterResponse


# ═══════════════════════════════════════════════════════════════════════════
# 1. Schema validation
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestAssetCategorySchemas:
    def test_update_partial_fields(self):
        data = AssetCategoryMasterUpdate(display_label="New Label")
        dumped = data.model_dump(exclude_unset=True)
        assert "display_label" in dumped
        assert "color" not in dumped

    def test_update_color(self):
        data = AssetCategoryMasterUpdate(color="#ff5733")
        dumped = data.model_dump(exclude_unset=True)
        assert dumped["color"] == "#ff5733"

    def test_update_all_fields(self):
        data = AssetCategoryMasterUpdate(
            display_label="Updated",
            color="#000000",
            sort_order=99,
            is_active=False,
        )
        dumped = data.model_dump(exclude_unset=True)
        assert len(dumped) == 4


# ═══════════════════════════════════════════════════════════════════════════
# 2. API endpoints
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestAssetCategoriesAPI:
    def test_get_all_categories(self, auth_client, db):
        """GET /asset-categories/ returns seeded categories."""
        # Ensure at least one category exists (seeded by conftest)
        count = db.query(AssetCategoryMaster).count()
        assert count >= 1

        response = auth_client.get("/api/v1/asset-categories/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "name" in data[0]
        assert "display_label" in data[0]

    def test_get_category_by_id(self, auth_client, db):
        """GET /asset-categories/{id} returns single category."""
        cat = db.query(AssetCategoryMaster).first()
        assert cat is not None

        response = auth_client.get(f"/api/v1/asset-categories/{cat.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == cat.name

    def test_get_category_not_found(self, auth_client):
        """GET /asset-categories/9999 returns 404."""
        response = auth_client.get("/api/v1/asset-categories/9999")
        assert response.status_code == 404

    def test_update_category(self, auth_client, db):
        """PUT /asset-categories/{id} updates fields."""
        cat = db.query(AssetCategoryMaster).first()
        original_label = cat.display_label

        response = auth_client.put(
            f"/api/v1/asset-categories/{cat.id}",
            json={"display_label": "Updated Label"},
        )
        assert response.status_code == 200
        assert response.json()["display_label"] == "Updated Label"

        # Restore original
        auth_client.put(
            f"/api/v1/asset-categories/{cat.id}",
            json={"display_label": original_label},
        )

    def test_update_category_not_found(self, auth_client):
        """PUT /asset-categories/9999 returns 404."""
        response = auth_client.put(
            "/api/v1/asset-categories/9999",
            json={"display_label": "Nope"},
        )
        assert response.status_code == 404

    def test_unauthenticated_request(self, client):
        """GET /asset-categories/ without auth returns 401."""
        response = client.get("/api/v1/asset-categories/")
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# 3. FK constraint validation on asset_types
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestAssetTypeCategoryValidation:
    def test_update_asset_type_with_valid_category(self, auth_client, db):
        """PUT /asset-types/{id} with valid category succeeds."""
        from app.models.asset_type_master import AssetTypeMaster
        at = db.query(AssetTypeMaster).first()
        assert at is not None

        response = auth_client.put(
            f"/api/v1/asset-types/{at.id}",
            json={"category": at.category},  # same category — should work
        )
        assert response.status_code == 200

    def test_update_asset_type_with_invalid_category(self, auth_client, db):
        """PUT /asset-types/{id} with nonexistent category returns 400."""
        from app.models.asset_type_master import AssetTypeMaster
        at = db.query(AssetTypeMaster).first()
        assert at is not None

        response = auth_client.put(
            f"/api/v1/asset-types/{at.id}",
            json={"category": "Nonexistent Category"},
        )
        assert response.status_code == 400
        assert "Invalid category" in response.json()["detail"]
