"""API tests for portfolio endpoints (/api/v1/portfolios/*)."""
import pytest
from tests.conftest import make_asset


@pytest.mark.api
class TestPortfolioList:
    def test_list_portfolios_returns_default(self, auth_client):
        resp = auth_client.get("/api/v1/portfolios/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(p["is_default"] for p in data)

    def test_unauthenticated_access_returns_401(self, client):
        resp = client.get("/api/v1/portfolios/")
        assert resp.status_code == 401


@pytest.mark.api
class TestPortfolioCreate:
    def test_create_portfolio(self, auth_client):
        resp = auth_client.post("/api/v1/portfolios/", json={
            "name": "Trading",
            "description": "Day trading portfolio",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Trading"
        assert data["is_default"] is False

    def test_create_duplicate_portfolio_name(self, auth_client):
        auth_client.post("/api/v1/portfolios/", json={"name": "DupTest"})
        resp = auth_client.post("/api/v1/portfolios/", json={"name": "DupTest"})
        assert resp.status_code == 400


@pytest.mark.api
class TestPortfolioGetUpdateDelete:
    def test_get_portfolio_by_id(self, auth_client):
        create_resp = auth_client.post("/api/v1/portfolios/", json={"name": "GetMe"})
        pid = create_resp.json()["id"]
        resp = auth_client.get(f"/api/v1/portfolios/{pid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "GetMe"

    def test_get_nonexistent_portfolio(self, auth_client):
        resp = auth_client.get("/api/v1/portfolios/99999")
        assert resp.status_code == 404

    def test_update_portfolio_name(self, auth_client):
        create_resp = auth_client.post("/api/v1/portfolios/", json={"name": "OldName"})
        pid = create_resp.json()["id"]
        resp = auth_client.put(f"/api/v1/portfolios/{pid}", json={"name": "NewName"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "NewName"

    def test_cannot_deactivate_default_portfolio(self, auth_client):
        # Find the default portfolio
        portfolios = auth_client.get("/api/v1/portfolios/").json()
        default_id = next(p["id"] for p in portfolios if p["is_default"])
        resp = auth_client.put(f"/api/v1/portfolios/{default_id}", json={"is_active": False})
        assert resp.status_code == 400

    def test_cannot_delete_default_portfolio(self, auth_client):
        portfolios = auth_client.get("/api/v1/portfolios/").json()
        default_id = next(p["id"] for p in portfolios if p["is_default"])
        resp = auth_client.delete(f"/api/v1/portfolios/{default_id}")
        assert resp.status_code == 400

    def test_delete_portfolio_moves_assets(self, auth_client, db, test_user):
        # Get default portfolio
        portfolios = auth_client.get("/api/v1/portfolios/").json()
        default_id = next(p["id"] for p in portfolios if p["is_default"])

        # Create a second portfolio
        create_resp = auth_client.post("/api/v1/portfolios/", json={"name": "ToDelete"})
        new_pid = create_resp.json()["id"]

        # Create an asset in the new portfolio
        asset = make_asset(db, test_user, new_pid, name="Movable Stock")
        db.commit()
        asset_id = asset.id

        # Delete the new portfolio
        resp = auth_client.delete(f"/api/v1/portfolios/{new_pid}")
        assert resp.status_code == 204

        # Verify asset moved to default
        asset_resp = auth_client.get(f"/api/v1/assets/{asset_id}")
        assert asset_resp.status_code == 200
        assert asset_resp.json()["portfolio_id"] == default_id
