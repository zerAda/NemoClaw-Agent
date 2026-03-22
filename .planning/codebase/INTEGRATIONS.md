# External Integrations

**Analysis Date:** 2026-03-23

## APIs & External Services

**AI/LLM:**
- Google Gemini - Inference backend for NemoClaw and Career Agent
  - SDK/Client: `openai` package (AsyncOpenAI wrapper)
  - Endpoint: `https://generativelanguage.googleapis.com/v1beta/openai`
  - Models used: `gemini-1.5-flash` (scoring), `gemini-1.5-pro` (cover letter generation)
  - Auth: `GEMINI_API_KEY` environment variable in `docker-compose.yml` line 8
  - Implementation: Singleton factory in `career_agent/src/client_factory.py`

**Job Scraping:**
- LinkedIn - Job search and description extraction
  - Implementation: Headless Playwright browser in `career_agent/src/scraper.py`
  - Selectors: Externalized in `career_agent/config/selectors.yaml` (lines 1-5)
  - Selectors: job_card (`.base-card`), job_title (`.base-search-card__title`), job_url (`a`), job_description (`.description__text`)
  - Auth: None (unauthenticated scraping with stealth headers)

- Indeed - Job search alternative (configured but not actively used)
  - Selectors: In `career_agent/config/selectors.yaml` (lines 7-11)
  - Selectors: job_card (`.job_seen_beacon`), job_title (`h2.jobTitle`), job_url (`a[data-jk]`), job_description (`#jobDescriptionText`)
  - Auth: None

**Communication:**
- Telegram Bot API - NemoClaw messaging interface
  - Token: `TELEGRAM_BOT_TOKEN` environment variable in `docker-compose.yml` line 13
  - Used by: OpenClaw container (pre-built image)

## Data Storage

**Databases:**
- Qdrant Vector Database - Job deduplication and memory tracking
  - Client: `qdrant-client` package
  - Connection: Local filesystem at `./qdrant_db`
  - Implementation: `career_agent/src/memory.py` MemoryService class
  - Collection: `job_applications` (384-dim COSINE vectors, metadata payloads)
  - Purpose: Stores job URLs, status (SKIPPED/READY), scores, timestamps with UUIDv5-based deduplication

**File Storage:**
- Local filesystem only
  - Mounted Docker volume: `openclaw-workspace` in `docker-compose.yml` line 28
  - Brain directory mount: `./brain:/app/brain:rw` in `docker-compose.yml` line 30
  - Career Agent output: `brain/applications/{uuid}/cover_letter.txt` per `career_agent/src/app.py`

**Caching:**
- None detected

## Authentication & Identity

**Auth Provider:**
- OpenClaw Custom - Whitelist-based access control
  - User whitelist: `NEMO_AUTH_USER_ID` in `docker-compose.yml` line 17
  - Pairing secret: `NEMO_PAIRING_CODE` in `docker-compose.yml` line 18
  - Routing mode: `NEMO_ROUTING_MODE=cloud` (line 15)

**Agent Identity:**
- Custom file-based identity
  - Location: `agent.md` mounted read-only at `/app/agent.md` in `docker-compose.yml` line 32
  - Env var: `OPENCLAW_AGENT_IDENTITY=/app/agent.md` (line 23)
  - Purpose: Defines agent personality, guardrails, and behavior

## Monitoring & Observability

**Error Tracking:**
- None detected (no Sentry, Datadog, etc.)

**Logs:**
- Docker logs - NemoClaw container logging via `docker logs openclaw --tail=50`
- Python logging - Career Agent uses standard logging module in all services
  - Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
  - Level: INFO (configurable via `LOG_LEVEL` in `docker-compose.yml` line 20)
  - Output: stdout (captured by Docker)

**Health Checks:**
- Docker health check: `curl -f http://localhost:8080/health` in `docker-compose.yml` lines 33-38
  - Interval: 30 seconds
  - Timeout: 10 seconds
  - Start period: 15 seconds

## CI/CD & Deployment

**Hosting:**
- VPS with Docker support
  - Deployment path: `/opt/nemoclaw`
  - SSH-based deployment via GitHub Actions
  - Deployment trigger: Post-CI success in `nemoclaw-cd.yml`

**CI Pipeline:**
- GitHub Actions - `.github/workflows/nemoclaw-ci.yml`
  - Runs on: Push to master, PRs to master
  - Steps: Python setup 3.11, Flake8 lint, Bandit SAST, .env.example validation
  - No testing stage (tests not configured)

**CD Pipeline:**
- GitHub Actions - `.github/workflows/nemoclaw-cd.yml`
  - Runs on: CI success on master
  - Steps:
    1. SSH pre-transfer cleanup (`/opt/nemoclaw` directory reset)
    2. SCP code transfer (entire repo)
    3. Hot-swap via SSH: `.env` sync, `traefik-net` creation, `docker compose down -v`, `docker compose up -d --force-recreate`
    4. Image cleanup (24h old images pruned)
  - Secrets injected: `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN` via GitHub secrets

**Reverse Proxy:**
- Traefik (external container on same VPS)
  - Network: `traefik-net` (external, must exist on VPS)
  - Domain: `nemoclaw.resto-bot.com`
  - Entrypoint: `websecure` (HTTPS)
  - TLS resolver: Let's Encrypt
  - Backend port: 8080 (OpenClaw container)
  - Configuration: Traefik labels in `docker-compose.yml` lines 47-52

## Environment Configuration

**Required env vars:**
- `GEMINI_API_KEY` - Google Gemini API key (critical for both NemoClaw and Career Agent)
- `TELEGRAM_BOT_TOKEN` - Telegram Bot token for messaging
- `NEMO_AUTH_USER_ID` - Whitelist user ID for OpenClaw access
- `NEMO_PAIRING_CODE` - Pairing secret for OpenClaw
- `VPS_HOST` - VPS hostname (GitHub vars)
- `VPS_USER` - SSH user (default: `root`, GitHub vars)
- `VPS_SSH_KEY` - SSH private key (GitHub secrets)

**Secrets location:**
- Local: `.env` file (template: `.env.example` at repo root)
- GitHub Actions:
  - Secrets: `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `VPS_SSH_KEY`
  - Vars: `VPS_HOST`, `VPS_USER`
- VPS: `.env` at `/opt/nemoclaw/.env` (injected during CD pipeline)

## Webhooks & Callbacks

**Incoming:**
- Telegram Bot polling - NemoClaw container receives updates via Telegram Bot API
- Health check endpoint: `http://localhost:8080/health` (Docker health check)

**Outgoing:**
- None detected (Career Agent is fire-and-forget, no callbacks)

## Career Agent Specific Integrations

**Brain Data Files:**
- `brain/Bio_Context.md` - Candidate bio/skills loaded in `career_agent/src/hunter.py` line 28
- `brain/Target_Specs.json` - Job criteria loaded in `career_agent/src/hunter.py` line 32
- Target roles, locations, salary range, industries, keywords, scoring_threshold (default 0.85)

**Scraper Configuration:**
- `career_agent/config/selectors.yaml` - CSS selectors for LinkedIn/Indeed updated without code changes
- Selectors loaded in `career_agent/src/scraper.py` line 19

**Job Processing Pipeline:**
1. Scraper (`career_agent/src/scraper.py`) → LinkedIn job list via Playwright
2. Hunter (`career_agent/src/hunter.py`) → Score via Gemini 1.5 Flash
3. Tailor (`career_agent/src/tailor.py`) → Generate cover letter via Gemini 1.5 Pro
4. Memory (`career_agent/src/memory.py`) → Store in Qdrant with UUIDv5 dedup
5. Orchestrator (`career_agent/src/app.py`) → Run 5 jobs concurrently via `asyncio.gather`

---

*Integration audit: 2026-03-23*
