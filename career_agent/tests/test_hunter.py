"""HunterService scoring pipeline tests — Phase 3.

Tests cover SCORE-01 through SCORE-04:
  SCORE-01: Gemini scoring with Bio_Context and Target_Specs
  SCORE-02: Fast-fail exclusion check runs before Gemini call
  SCORE-03: Jobs below scoring_threshold are marked SKIPPED
  SCORE-04: ScoreRecord fields persisted per job
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from career_agent.src.hunter import HunterService
from career_agent.src.models import JobListing, ScoreRecord


def _make_listing(title: str, description: str = "A great job at a tech company.") -> JobListing:
    """Helper: build a minimal JobListing for testing."""
    return JobListing(
        id="test-job-1",
        title=title,
        company="Test Corp",
        location="Paris, France",
        description=description,
        url="https://example.com/job/1",
        source="linkedin",
    )


def _mock_gemini_response(score: float, recommendation: str, reasoning: str = "Test reasoning"):
    """Helper: build a mock AsyncOpenAI response object."""
    content = json.dumps({
        "score": score,
        "recommendation": recommendation,
        "reasoning": reasoning,
        "match_reasons": ["Relevant experience"],
        "gap_analysis": [],
    })
    mock_message = MagicMock()
    mock_message.content = content
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


@pytest.mark.asyncio
async def test_fast_fail_skips_gemini(tmp_brain_path):
    """SCORE-02: A job containing an exclusion keyword never calls the Gemini API."""
    listing = _make_listing(title="Internship — Python Developer")

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock()

    with patch("career_agent.src.hunter.ai_factory") as mock_factory:
        mock_factory.get_client.return_value = mock_client
        hunter = HunterService(brain_path=tmp_brain_path)
        await hunter.score_job(listing)

    mock_client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_fast_fail_returns_skipped_score_record(tmp_brain_path):
    """SCORE-02 + SCORE-04: Fast-failed job returns ScoreRecord with score=0.0, recommendation='SKIP', fast_failed=True."""
    listing = _make_listing(title="Internship — Python Developer")

    with patch("career_agent.src.hunter.ai_factory") as mock_factory:
        mock_factory.get_client.return_value = MagicMock()
        hunter = HunterService(brain_path=tmp_brain_path)
        record = await hunter.score_job(listing)

    assert isinstance(record, ScoreRecord)
    assert record.fast_failed is True
    assert record.score == 0.0
    assert record.recommendation == "SKIP"
    assert record.threshold_met is False
    assert "intern" in record.reasoning.lower()


@pytest.mark.asyncio
async def test_gemini_called_for_passing_job(tmp_brain_path):
    """SCORE-01: A job that passes exclusion check triggers exactly one Gemini API call."""
    listing = _make_listing(title="Senior Python Engineer")

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_gemini_response(score=0.9, recommendation="APPLY")
    )

    with patch("career_agent.src.hunter.ai_factory") as mock_factory:
        mock_factory.get_client.return_value = mock_client
        hunter = HunterService(brain_path=tmp_brain_path)
        await hunter.score_job(listing)

    mock_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_score_record_fields_populated(tmp_brain_path):
    """SCORE-04: ScoreRecord returned from score_job() has score, recommendation, reasoning all non-empty."""
    listing = _make_listing(title="Senior Python Engineer")

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_gemini_response(score=0.9, recommendation="APPLY", reasoning="Strong Python match")
    )

    with patch("career_agent.src.hunter.ai_factory") as mock_factory:
        mock_factory.get_client.return_value = mock_client
        hunter = HunterService(brain_path=tmp_brain_path)
        record = await hunter.score_job(listing)

    assert isinstance(record, ScoreRecord)
    assert record.score == 0.9
    assert record.recommendation == "APPLY"
    assert record.reasoning == "Strong Python match"
    assert record.fast_failed is False
    assert record.job_id == "test-job-1"
    assert record.title == "Senior Python Engineer"


@pytest.mark.asyncio
async def test_below_threshold_marked_skip(tmp_brain_path):
    """SCORE-03: A job scoring below scoring_threshold (0.85) gets recommendation='SKIP' and threshold_met=False."""
    listing = _make_listing(title="Junior Python Developer")

    mock_client = MagicMock()
    # Gemini says APPLY but score 0.5 — threshold (0.85) overrides recommendation
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_gemini_response(score=0.5, recommendation="APPLY")
    )

    with patch("career_agent.src.hunter.ai_factory") as mock_factory:
        mock_factory.get_client.return_value = mock_client
        hunter = HunterService(brain_path=tmp_brain_path)
        record = await hunter.score_job(listing)

    assert record.recommendation == "SKIP"
    assert record.threshold_met is False
    assert record.score == 0.5


@pytest.mark.asyncio
async def test_above_threshold_marked_apply(tmp_brain_path):
    """SCORE-03: A job scoring at or above scoring_threshold (0.85) gets threshold_met=True and recommendation != 'SKIP'."""
    listing = _make_listing(title="Senior AI Engineer")

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_gemini_response(score=0.9, recommendation="APPLY")
    )

    with patch("career_agent.src.hunter.ai_factory") as mock_factory:
        mock_factory.get_client.return_value = mock_client
        hunter = HunterService(brain_path=tmp_brain_path)
        record = await hunter.score_job(listing)

    assert record.threshold_met is True
    assert record.recommendation != "SKIP"
    assert record.score == 0.9
