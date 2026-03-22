# Architecture

**Analysis Date:** 2026-03-23

## Pattern Overview

**Overall:** Dual-component distributed system with orchestrated microservices and CLI automation.

**Key Characteristics:**
- **Two independent subsystems:** NemoClaw (containerized AI agent) and Career Agent (Python CLI automation)
- **Async-first design:** Career Agent uses Python asyncio for parallel job processing (up to 5 concurrent)
- **LLM-centric intelligence:** Both components leverage Google Gemini via OpenAI-compatible API adapter
- **Persistent memory model:** NemoClaw uses mounted volumes; Career Agent uses Qdrant vector DB for deduplication
- **Configuration-as-code:** Selectors and specs externalized to YAML/JSON for runtime updates without code changes

## Layers

**NemoClaw Container (Docker):**
- Purpose: Autonomous Telegram-based AI agent with tool-calling capabilities
- Location: `ghcr.io/openclaw/openclaw:latest` (pre-built image)
- Contains: Telegram gateway, OpenClaw runtime, sandboxed execution environment
- Depends on: Google Gemini API (via `BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai`)
- Used by: End users via Telegram; orchestrates Career Agent via API calls

**Career Agent Orchestration (`career_agent/src/app.py`):**
- Purpose: High-level job search automation controller
- Location: `C:/Users/mon pc/Desktop/nemoclaw-standalone/career_agent/src/app.py`
- Contains: `PhoenixApp` class; `run_cycle()` method; parallel job processing via `asyncio.gather`
- Depends on: HunterService, TailorService, MemoryService
- Used by: CLI entry point; manual invocation or scheduled tasks

**Job Scoring & Filtering (`career_agent/src/hunter.py`):**
- Purpose: Evaluate job descriptions against candidate profile; perform fast-fail exclusions
- Location: `C:/Users/mon pc/Desktop/nemoclaw-standalone/career_agent/src/hunter.py`
- Contains: `HunterService` class; `MatchReport` Pydantic model; exclusion filter logic
- Depends on: ClientFactory (Gemini), Scraper (LinkedIn), bio/specs from brain/
- Used by: PhoenixApp.process_job()

**Web Scraping (`career_agent/src/scraper.py`):**
- Purpose: LinkedIn (and Indeed) job extraction with stealth/anti-detection measures
- Location: `C:/Users/mon pc/Desktop/nemoclaw-standalone/career_agent/src/scraper.py`
- Contains: `Scraper` class; Playwright headless browser; human-like scroll simulation
- Depends on: Playwright, playwright_stealth, selectors from YAML config
- Used by: HunterService (job description extraction); PhoenixApp (job search)

**Cover Letter Generation (`career_agent/src/tailor.py`):**
- Purpose: Custom cover letter synthesis for matching jobs
- Location: `C:/Users/mon pc/Desktop/nemoclaw-standalone/career_agent/src/tailor.py`
- Contains: `TailorService` class; `TailoredContent` Pydantic model; Gemini Pro integration
- Depends on: ClientFactory (Gemini)
- Used by: PhoenixApp.process_job() (only if recommendation != SKIP)

**Memory & Deduplication (`career_agent/src/memory.py`):**
- Purpose: Track processed jobs; prevent duplicate applications; persistent audit trail
- Location: `C:/Users/mon pc/Desktop/nemoclaw-standalone/career_agent/src/memory.py`
- Contains: `MemoryService` class; local Qdrant DB at `./qdrant_db`; UUIDv5-based deduplication
- Depends on: Qdrant client
- Used by: PhoenixApp (before/after job processing)

**AI Client Factory (`career_agent/src/client_factory.py`):**
- Purpose: Centralized singleton for Gemini API initialization and connection pooling
- Location: `C:/Users/mon pc/Desktop/nemoclaw-standalone/career_agent/src/client_factory.py`
- Contains: `ClientFactory` singleton; AsyncOpenAI wrapper
- Depends on: OpenAI Python SDK; GEMINI_API_KEY env var
- Used by: HunterService, TailorService (shared instance via `ai_factory` global)

**Brain Data (`brain/`):**
- Purpose: Candidate persona and job search criteria (injected into both NemoClaw container and Career Agent)
- Location: `C:/Users/mon pc/Desktop/nemoclaw-standalone/brain/`
- Contains: `Bio_Context.md` (candidate skills/experience), `Target_Specs.json` (roles, salary, exclusions)
- Used by: HunterService (scoring context), NemoClaw container (mounted read-write)

**Selectors Config (`career_agent/config/selectors.yaml`):**
- Purpose: Externalized CSS selectors for LinkedIn/Indeed to decouple from scraper logic
- Location: `C:/Users/mon pc/Desktop/nemoclaw-standalone/career_agent/config/selectors.yaml`
- Contains: DOM selectors for job cards, titles, URLs, descriptions
- Used by: Scraper (loaded at init via `_load_selectors()`)

## Data Flow

**Career Agent Job Processing Cycle:**

1. **Search Phase** (PhoenixApp.run_cycle)
   - Call `Scraper.search_linkedin_jobs(keyword, location)` → returns list of job objects (title, url)

2. **Parallel Processing Phase** (asyncio.gather over job list, up to 5 concurrent)
   - For each job in `process_job()`:
     a. Check `MemoryService.is_already_processed(job_url)` → skip if duplicate
     b. Call `Scraper.get_linkedin_job_description(job_url)` → fetch full JD text
     c. Call `HunterService.score_job(jd_text)` → returns `MatchReport(score, recommendation, gap_analysis)`
     d. If recommendation == "SKIP" → log & store in memory, proceed to next job
     e. If recommendation != "SKIP" → call `TailorService.customize_letter(jd_text, report)` → returns `TailoredContent`

3. **Artifact Storage Phase**
   - Generate UUIDv5 from job URL (deterministic, URL-stable)
   - Create directory `brain/applications/{uuid}/`
   - Write cover letter to `cover_letter.txt`
   - Call `MemoryService.add_application(url, metadata)` → persist to Qdrant with status READY/SKIPPED

**NemoClaw Agent Request Flow:**

1. User sends Telegram message → NemoClaw receives via Telegram Bot API
2. Message → OpenClaw runtime → Gemini inference via `BASE_URL` adapter
3. If action requires tool-calling → OpenShell sandbox execution
4. Response → Telegram reply

**State Management:**

- **NemoClaw State:** Mounted volumes (persistent across restarts)
  - `/app/workspace` — transient work directory
  - `/app/brain` — persistent memory (mapped from local `brain/`)
  - `/app/agent.md` — read-only agent identity (mapped from local `agent.md`)

- **Career Agent State:** File system + Qdrant
  - `brain/applications/{uuid}/cover_letter.txt` — generated artifacts
  - `qdrant_db/` — vector DB for deduplication & metadata tracking

- **Secrets:** Environment variables (`.env` file, not committed; loaded at container/process start)

## Key Abstractions

**MatchReport:**
- Purpose: Structured job scoring result with recommendation
- Examples: `C:/Users/mon pc/Desktop/nemoclaw-standalone/career_agent/src/hunter.py` (lines 11-15)
- Pattern: Pydantic BaseModel with fields: `score` (0.0-1.0), `match_reasons`, `gap_analysis`, `recommendation` (APPLY/SKIP/TAILOR_REQUIRED)

**TailoredContent:**
- Purpose: Structured cover letter output
- Examples: `C:/Users/mon pc/Desktop/nemoclaw-standalone/career_agent/src/tailor.py` (lines 10-13)
- Pattern: Pydantic BaseModel with `subject`, `body`, `suggested_edits`

**PhoenixApp Orchestrator:**
- Purpose: Coordinates all sub-services in a single job search cycle
- Examples: `C:/Users/mon pc/Desktop/nemoclaw-standalone/career_agent/src/app.py` (lines 14-87)
- Pattern: Async init + async run_cycle; error isolation per job (try/except in process_job)

**ClientFactory Singleton:**
- Purpose: Ensure single Gemini client instance, shared across HunterService + TailorService
- Examples: `C:/Users/mon pc/Desktop/nemoclaw-standalone/career_agent/src/client_factory.py` (lines 7-32)
- Pattern: Singleton via __new__; lazy initialization on first get_client() call

## Entry Points

**NemoClaw Container:**
- Location: `C:/Users/mon pc/Desktop/nemoclaw-standalone/docker-compose.yml`
- Triggers: `docker compose up -d` or CD pipeline
- Responsibilities: Listen on port 8080 (behind Traefik), handle Telegram messages, execute tools

**Career Agent CLI:**
- Location: `C:/Users/mon pc/Desktop/nemoclaw-standalone/career_agent/src/app.py` (main block, lines 77-87)
- Triggers: `python -m career_agent.src.app`
- Responsibilities: Initialize PhoenixApp, run_cycle with hardcoded keyword ("AI Engineer"), orchestrate job processing

**GitHub Actions CI:**
- Location: `C:/Users/mon pc/Desktop/nemoclaw-standalone/.github/workflows/nemoclaw-ci.yml`
- Triggers: Every push/PR to master
- Responsibilities: Flake8 lint, Bandit SAST, validate .env.example existence

**GitHub Actions CD:**
- Location: `C:/Users/mon pc/Desktop/nemoclaw-standalone/.github/workflows/nemoclaw-cd.yml`
- Triggers: After CI passes (workflow_run event)
- Responsibilities: SSH to VPS, SCP repo, recreate containers with fresh image pull

## Error Handling

**Strategy:** Defensive per-job isolation with logging

**Patterns:**
- **PhoenixApp.process_job()**: Try/except wrapper (lines 25-63) catches all exceptions, logs error, continues to next job
- **HunterService.score_job()**: Validation checks for empty JD (line 44); fast-fail exclusions (line 48); returns default MatchReport on failure
- **Scraper methods**: No exception handling (assumes network is available); relies on caller to validate returned data
- **MemoryService**: No explicit error handling; assumes Qdrant is running (local instance)

## Cross-Cutting Concerns

**Logging:**
- Centralized via Python logging module
- HunterService, TailorService, Scraper, PhoenixApp all use logger = logging.getLogger(__name__)
- Set to INFO level; INFO, WARNING, ERROR used descriptively

**Validation:**
- Pydantic models validate response JSON shapes (MatchReport, TailoredContent)
- JD text length checks (> 100 chars in process_job; > 50 chars in score_job)
- HunterService._fast_fail_check() validates against exclusions list from Target_Specs.json

**Authentication:**
- NemoClaw: TELEGRAM_BOT_TOKEN, NEMO_AUTH_USER_ID, NEMO_PAIRING_CODE
- Career Agent: GEMINI_API_KEY (raises ValueError if missing in ClientFactory)
- All secrets loaded from .env file or GitHub Actions secrets

**Rate Limiting:**
- Scraper._human_scroll() uses randomized delays (0.5-1.5s between scrolls)
- No explicit rate limiting in Gemini calls; relies on quota/tier

---

*Architecture analysis: 2026-03-23*
