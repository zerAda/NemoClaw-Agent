"""France Travail API scraper tests — respx mocks for OAuth2 + search."""
import pytest
import respx
import httpx
import os
from unittest.mock import AsyncMock, patch
from src.scraper import Scraper, FTConfig
from src.models import JobListing
from src.alerter import AlertService

@respx.mock
@pytest.mark.asyncio
async def test_token_request():
    """SCRAPE-01: Token POST sends correct grant_type, client_id, scope."""
    token_route = respx.post(FTConfig.TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "test-token-123"})
    )
    # Using real Scraper __init__ but mocking sub-calls
    with patch.dict("os.environ", {"FRANCE_TRAVAIL_CLIENT_ID": "test-id", "FRANCE_TRAVAIL_CLIENT_SECRET": "test-secret"}):
        scraper = Scraper(brain_path="")
        token = await scraper._get_france_travail_token()
    assert token == "test-token-123"
    assert token_route.called
    request = token_route.calls[0].request
    body = request.content.decode()
    assert "grant_type=client_credentials" in body
    assert "client_id=test-id" in body
    assert "scope=api_offresdemploiv2" in body

@respx.mock
@pytest.mark.asyncio
async def test_search_returns_listings():
    """SCRAPE-01: Search returns list[JobListing] on 200 response."""
    respx.post(FTConfig.TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "tok"})
    )
    respx.get(FTConfig.SEARCH_URL).mock(
        return_value=httpx.Response(200, json={
            "resultats": [
                {"id": "123", "intitule": "Dev Python", "entreprise": {"nom": "ACME"}, "lieuTravail": {"libelle": "Paris"}, "description": "Job desc", "typeContrat": "CDI"},
                {"id": "456", "intitule": "Data Engineer", "entreprise": {"nom": "Corp"}, "lieuTravail": {"libelle": "Lyon"}, "description": "Another", "typeContrat": "CDD"},
            ]
        })
    )
    with patch.dict("os.environ", {"FRANCE_TRAVAIL_CLIENT_ID": "id", "FRANCE_TRAVAIL_CLIENT_SECRET": "sec"}):
        scraper = Scraper(brain_path="")
        jobs = await scraper.search_france_travail_jobs("Python")
    assert len(jobs) == 2
    assert isinstance(jobs[0], JobListing)
    assert jobs[0].title == "Dev Python"
    assert jobs[0].source == "france_travail"
    assert jobs[1].company == "Corp"

@respx.mock
@pytest.mark.asyncio
async def test_search_error_triggers_alert():
    """SCRAPE-01: Search returns [] and triggers alert on failure."""
    respx.post(FTConfig.TOKEN_URL).mock(
        return_value=httpx.Response(500)
    )
    mock_alerter = AsyncMock(spec=AlertService)
    with patch.dict("os.environ", {"FRANCE_TRAVAIL_CLIENT_ID": "id", "FRANCE_TRAVAIL_CLIENT_SECRET": "sec"}):
        scraper = Scraper(brain_path="", alerter=mock_alerter)
        jobs = await scraper.search_france_travail_jobs("Python")
    assert jobs == []
    mock_alerter.send_alert.assert_called_once()

@pytest.mark.asyncio
async def test_human_delay_range():
    """SCRAPE-07: _human_delay() sleeps within [min_delay_s, max_delay_s]."""
    scraper = Scraper(brain_path="")
    scraper._rate_limits = {"min_delay_s": 2, "max_delay_s": 5}
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await scraper._human_delay()
        mock_sleep.assert_called_once()
        delay = mock_sleep.call_args[0][0]
        assert 2 <= delay <= 5

@pytest.mark.asyncio
async def test_rate_limits_from_specs(tmp_path):
    """SCRAPE-07: Rate limits loaded from Target_Specs.json."""
    import json
    specs = {"rate_limits": {"min_delay_s": 3, "max_delay_s": 7}}
    (tmp_path / "Target_Specs.json").write_text(json.dumps(specs))
    scraper = Scraper(brain_path=str(tmp_path))
    assert scraper._rate_limits["min_delay_s"] == 3
    assert scraper._rate_limits["max_delay_s"] == 7
