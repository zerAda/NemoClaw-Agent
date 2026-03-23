import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client(mock_phoenix_app):
    """TestClient with PhoenixApp mocked out — no real Playwright/Gemini/Qdrant."""
    with patch("career_agent.sidecar.main._phoenix", mock_phoenix_app):
        from career_agent.sidecar.main import app
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


def test_health_endpoint_returns_200(client):
    """GET /health returns {"status": "ok"}"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_run_cycle_returns_202(client):
    """POST /run-cycle returns 202 Accepted"""
    response = client.post("/run-cycle", json={"keyword": "AI Engineer", "location": "France"})
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"


def test_run_cycle_triggers_background_task(client, mock_phoenix_app):
    """POST /run-cycle enqueues PhoenixApp.run_cycle as background task"""
    response = client.post("/run-cycle", json={"keyword": "Backend Dev", "location": "Paris"})
    assert response.status_code == 202
    # TestClient executes background tasks synchronously
    mock_phoenix_app.run_cycle.assert_called_once()
