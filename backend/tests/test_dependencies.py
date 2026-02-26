"""Unit tests for FastAPI dependency functions."""
import pytest
from app.core.security import create_access_token
from app.api.dependencies import get_default_portfolio_id


@pytest.mark.unit
class TestGetDefaultPortfolioId:
    def test_returns_default_portfolio_id(self, db, test_user):
        pid = get_default_portfolio_id(test_user.id, db)
        assert pid is not None

    def test_returns_none_for_unknown_user(self, db):
        pid = get_default_portfolio_id(99999, db)
        assert pid is None


@pytest.mark.api
class TestAuthDependencies:
    def test_authenticated_endpoint_with_valid_token(self, auth_client):
        resp = auth_client.get("/api/v1/portfolios/")
        assert resp.status_code == 200

    def test_authenticated_endpoint_with_invalid_token(self, client):
        client.headers.update({"Authorization": "Bearer invalid.token.here"})
        resp = client.get("/api/v1/portfolios/")
        assert resp.status_code == 401

    def test_inactive_user_rejected(self, client, db, test_user):
        """Deactivated users should get a 400/401 error."""
        test_user.is_active = False
        db.flush()

        token = create_access_token(
            data={"sub": test_user.username, "user_id": test_user.id}
        )
        client.headers.update({"Authorization": f"Bearer {token}"})
        resp = client.get("/api/v1/portfolios/")
        assert resp.status_code in (400, 401)
