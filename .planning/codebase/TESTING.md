# Testing Patterns

**Analysis Date:** 2026-03-23

## Test Framework

**Runner:**
- Not detected in codebase

**Assertion Library:**
- Not detected in codebase

**Run Commands:**
- No test commands configured in `package.json` or CI pipeline
- CI pipeline runs linting and SAST only (no unit/integration tests)

## Test File Organization

**Location:**
- No dedicated test files found in the repository
- No `tests/`, `test/`, or `*_test.py` / `*_spec.py` files present

**Naming:**
- Not applicable

**Structure:**
- Not applicable

## Test Coverage

**Status:** No automated testing present

**Requirements:** Not enforced

## Test Types

**Unit Tests:**
- Not implemented

**Integration Tests:**
- Not implemented

**E2E Tests:**
- Not implemented

## Linting & Static Analysis (Current Quality Gate)

**What IS tested in CI:**

### Flake8 Linting
- **Location:** `.github/workflows/nemoclaw-ci.yml` (line 35-40)
- **Configuration:**
  - Strict mode: `--select=E9,F63,F7,F82` (syntax errors only)
  - Warning mode: `--exit-zero --max-complexity=10 --max-line-length=127`
- **Run:**
  ```bash
  # Strict checks (build fails if violations)
  flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

  # Advisory checks (warnings only)
  flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
  ```

### Bandit Security Scanning
- **Location:** `.github/workflows/nemoclaw-ci.yml` (line 42-44)
- **Configuration:** `-f custom -ll -ii` (low-level logging, level II+ severity)
- **Run:**
  ```bash
  bandit -r . -f custom -ll -ii
  ```
- **Purpose:** Identify security risks (hardcoded credentials, weak crypto, SQL injection, etc.)

### Environment Configuration Validation
- **Location:** `.github/workflows/nemoclaw-ci.yml` (line 46-52)
- **Check:** `.env.example` must exist in repository root
- **Purpose:** Ensure secrets are not committed; guide developers on required variables

## Test Patterns (Not Present - Testing Gap)

**Current limitation:** No unit, integration, or E2E test coverage for Career Agent logic.

**Services without test coverage:**
- `career_agent/src/app.py` (`PhoenixApp`) — Orchestrator, no mocking
- `career_agent/src/hunter.py` (`HunterService`) — Gemini API integration, no mocks
- `career_agent/src/tailor.py` (`TailorService`) — Cover letter generation, no mocks
- `career_agent/src/scraper.py` (`Scraper`) — LinkedIn Playwright automation, no mocks
- `career_agent/src/memory.py` (`MemoryService`) — Qdrant vector DB integration, no mocks
- `career_agent/src/client_factory.py` (`ClientFactory`) — Singleton AI client, no mocks

## Recommended Testing Structure (If Implemented)

**Test Location Convention:**
- Co-located with source: `career_agent/src/test_app.py`, `career_agent/src/test_hunter.py`
- Or separate: `career_agent/tests/test_app.py`

**Test Framework to Add:**
- `pytest` — Standard for async Python testing
- `pytest-asyncio` — For async function testing
- `pytest-cov` — For coverage reporting

**Mock Pattern (Recommended):**
```python
# Example async mock pattern (not currently used)
from unittest.mock import AsyncMock, patch
import pytest

@pytest.mark.asyncio
async def test_score_job_with_mock():
    with patch('career_agent.src.client_factory.ai_factory.get_client') as mock_client:
        mock_response = AsyncMock()
        mock_response.choices[0].message.content = '{"score": 0.9, ...}'
        mock_client.return_value.chat.completions.create.return_value = mock_response

        hunter = HunterService(brain_path='./brain')
        report = await hunter.score_job("Sample JD")
        assert report.score == 0.9
```

**What Should Be Mocked:**
- Gemini API calls (`client_factory`)
- LinkedIn Playwright automation (use fixtures for selectors)
- Qdrant database operations
- File I/O (Bio_Context.md, Target_Specs.json, selectors.yaml)

**What Should NOT Be Mocked:**
- Pydantic model validation (BaseModel instantiation)
- Error handling logic
- Data transformation functions (JSON parsing, UUID generation)

## Test Gaps & Risks

**Critical areas without coverage:**

1. **Gemini Integration (`hunter.py`, `tailor.py`)**
   - Risk: API failures, prompt injection, unexpected response formats
   - Impact: Silent failures in job scoring and cover letter generation
   - Recommendation: Mock API responses, test error cases

2. **Scraper (`scraper.py`)**
   - Risk: Selector breakage, network errors, stealth evasion failure
   - Impact: Scraper silently returns empty results
   - Recommendation: Mock Playwright pages, test selector loading

3. **Memory/Qdrant (`memory.py`)**
   - Risk: Database connection failures, duplicate processing
   - Impact: Lost job history, reprocessing same jobs
   - Recommendation: Mock Qdrant client, test UUID deduplication

4. **Orchestrator (`app.py`)**
   - Risk: Exception handling, concurrent processing issues
   - Impact: Partial cycle completion, lost job metadata
   - Recommendation: Integration tests with mocked services

5. **Config Loading**
   - Risk: Missing files, malformed JSON/YAML
   - Impact: Service initialization failures
   - Recommendation: Test with valid and invalid config fixtures

## Linting & Format Verification

**Current tools in use:**
- `flake8` — Detects syntax errors, undefined names, complexity
- `bandit` — Security vulnerability scanning

**No formatter enforced** — Code style enforcement relies on developer discipline. Consider adding:
- `black` — Automatic Python code formatter
- `isort` — Automatic import sorting

---

*Testing analysis: 2026-03-23*
