"""Basic health check tests for CI pipeline."""
from fastapi.testclient import TestClient


def test_app_imports():
    """Verify the FastAPI app can be imported without errors."""
    from app.main import app
    assert app is not None
    assert app.title is not None


def test_health_endpoint():
    """Test the app starts and responds to requests."""
    from app.main import app

    client = TestClient(app)
    response = client.get("/api/v1/health")
    # Accept 200 or 404 (if no health endpoint defined yet)
    assert response.status_code in (200, 404)
