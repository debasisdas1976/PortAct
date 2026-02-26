"""API tests for dashboard endpoints (/api/v1/dashboard/*)."""
import os
import pytest
from tests.conftest import make_asset

# The /overview endpoint uses PG-specific date_trunc, which fails on SQLite.
_IS_SQLITE = os.environ.get("TEST_DATABASE_URL", "sqlite").startswith("sqlite")


@pytest.mark.api
class TestDashboardOverview:
    @pytest.mark.skipif(_IS_SQLITE, reason="date_trunc is PG-specific")
    def test_overview_empty_portfolio(self, auth_client):
        resp = auth_client.get("/api/v1/dashboard/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["portfolio_summary"]["total_invested"] == 0
        assert data["portfolio_summary"]["total_current_value"] == 0

    @pytest.mark.skipif(_IS_SQLITE, reason="date_trunc is PG-specific")
    def test_overview_with_assets(self, auth_client, db, test_user):
        portfolios = auth_client.get("/api/v1/portfolios/").json()
        pid = portfolios[0]["id"]
        make_asset(db, test_user, pid, name="OV1",
                   total_invested=5000.0, current_value=6000.0,
                   quantity=10, current_price=600.0)
        db.commit()

        resp = auth_client.get("/api/v1/dashboard/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["portfolio_summary"]["total_invested"] > 0

    @pytest.mark.skipif(_IS_SQLITE, reason="date_trunc is PG-specific")
    def test_overview_response_shape(self, auth_client):
        resp = auth_client.get("/api/v1/dashboard/overview")
        assert resp.status_code == 200
        data = resp.json()
        expected_keys = {
            "portfolio_summary", "assets_by_type", "value_by_type",
            "recent_transactions", "unread_alerts",
            "top_performers", "bottom_performers",
        }
        assert expected_keys.issubset(set(data.keys()))

    def test_unauthenticated_dashboard(self, client):
        resp = client.get("/api/v1/dashboard/overview")
        assert resp.status_code == 401


@pytest.mark.api
class TestAssetAllocation:
    def test_allocation_empty(self, auth_client):
        resp = auth_client.get("/api/v1/dashboard/asset-allocation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_value"] == 0

    def test_allocation_with_assets(self, auth_client, db, test_user):
        from app.models.asset import AssetType
        portfolios = auth_client.get("/api/v1/portfolios/").json()
        pid = portfolios[0]["id"]
        make_asset(db, test_user, pid, name="S1", asset_type=AssetType.STOCK,
                   total_invested=1000.0, current_value=1200.0,
                   quantity=10, current_price=120.0)
        make_asset(db, test_user, pid, name="MF1", asset_type=AssetType.EQUITY_MUTUAL_FUND,
                   total_invested=2000.0, current_value=2300.0,
                   quantity=100, current_price=23.0)
        db.commit()

        resp = auth_client.get("/api/v1/dashboard/asset-allocation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_value"] > 0
        assert len(data["allocation"]) >= 2


@pytest.mark.api
class TestAssetsList:
    def test_assets_list(self, auth_client, db, test_user):
        portfolios = auth_client.get("/api/v1/portfolios/").json()
        pid = portfolios[0]["id"]
        make_asset(db, test_user, pid, name="ListAsset")
        db.commit()

        resp = auth_client.get("/api/v1/dashboard/assets-list")
        assert resp.status_code == 200
        data = resp.json()
        assert "assets" in data

    def test_assets_list_filtered_by_portfolio(self, auth_client, db, test_user):
        portfolios = auth_client.get("/api/v1/portfolios/").json()
        default_pid = portfolios[0]["id"]

        p2_resp = auth_client.post("/api/v1/portfolios/", json={"name": "FilterP"})
        p2_id = p2_resp.json()["id"]
        make_asset(db, test_user, p2_id, name="InFilterP")
        db.commit()

        resp = auth_client.get("/api/v1/dashboard/assets-list",
                               params={"portfolio_id": p2_id})
        assert resp.status_code == 200
