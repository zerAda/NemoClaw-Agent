import pytest


@pytest.mark.skip(reason="Plan 03 creates career_agent/sidecar/main.py")
def test_health_endpoint_returns_200():
    """GET /health returns {"status": "ok"}"""
    pass


@pytest.mark.skip(reason="Plan 03 creates career_agent/sidecar/main.py")
def test_run_cycle_returns_202():
    """POST /run-cycle returns 202 Accepted"""
    pass


@pytest.mark.skip(reason="Plan 03 creates career_agent/sidecar/main.py")
def test_run_cycle_triggers_background_task():
    """POST /run-cycle enqueues PhoenixApp.run_cycle as background task"""
    pass
