"""Sidecar API tests — Expert validation."""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    """TestClient for elite sidecar."""
    import sidecar.main as sidecar_mod
    sidecar_mod.state.active_cycles.clear()
    with TestClient(sidecar_mod.app) as c:
        yield c

def test_health_elite(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["mode"] == "ELITE"

def test_run_cycle_generates_id(client):
    with patch("sidecar.main.PhoenixApp") as mock_app:
        response = client.post("/run-cycle", json={"keyword": "AI"})
        assert response.status_code == 202
        data = response.json()
        assert "cycle_id" in data
        assert data["cycle_id"].startswith("CYC-")

def test_run_cycle_custom_id(client):
    with patch("sidecar.main.PhoenixApp") as mock_app:
        response = client.post("/run-cycle", json={"keyword": "AI", "cycle_id": "MY-TRACK-1"})
        assert response.status_code == 202
        assert response.json()["cycle_id"] == "MY-TRACK-1"

def test_run_cycle_limit_hit(client):
    import sidecar.main as sidecar_mod
    sidecar_mod.state.active_cycles = {"c1": "k1", "c2": "k2", "c3": "k3"}
    
    response = client.post("/run-cycle", json={"keyword": "AI"})
    assert response.status_code == 429
    assert "limit reached" in response.json()["detail"]
