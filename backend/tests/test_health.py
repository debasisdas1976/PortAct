"""Health check and root endpoint tests for CI pipeline."""
import pytest


@pytest.mark.unit
def test_app_imports():
    """Verify the FastAPI app can be imported without errors."""
    from app.main import app
    assert app is not None
    assert app.title is not None


@pytest.mark.api
def test_root_endpoint(client):
    """GET / returns app name and version."""
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "version" in data
    assert "PortAct" in data["message"]


@pytest.mark.api
def test_health_endpoint(client):
    """GET /health returns status, version, environment, database keys."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "version" in data
    assert "environment" in data
    assert "database" in data


@pytest.mark.api
def test_app_version_not_empty(client):
    """The version string should be non-empty."""
    resp = client.get("/")
    data = resp.json()
    assert data["version"] != ""
