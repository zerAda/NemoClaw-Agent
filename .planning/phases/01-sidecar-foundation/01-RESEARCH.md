# Phase 1: Sidecar Foundation - Research

**Researched:** 2026-03-23
**Domain:** FastAPI sidecar HTTP integration with OpenClaw skill system + Docker Compose multi-service + Gemini model upgrade
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | career_agent/ Python module wrapped in FastAPI sidecar service deployable as second Docker Compose service | FastAPI + uvicorn patterns; career_agent/src/api.py wraps existing PhoenixApp with zero logic changes |
| INFRA-02 | NemoClaw (OpenClaw LLM) can invoke career_agent capabilities via HTTP skill endpoint (SKILL.md + /tools/invoke) | OpenClaw SKILL.md schema documented; HTTP POST to sidecar is the only supported integration path |
| INFRA-03 | Sidecar and OpenClaw container share ./brain volume (Bio_Context.md, Target_Specs.json, qdrant_db) | Docker Compose named volume pattern; MemoryService path must change from ./qdrant_db to /brain/qdrant_db |
| INFRA-04 | Existing CI/CD pipeline covers the new sidecar service | nemoclaw-ci.yml runs flake8/bandit on all Python; nemoclaw-cd.yml SCP deploys entire repo then docker compose up — sidecar auto-included once added to docker-compose.yml |
| INFRA-06 | Gemini model IDs upgraded from gemini-1.5-* to gemini-2.5-flash across all services | 3 hardcoded strings to change: hunter.py line 62, tailor.py line 32, docker-compose.yml line 10 (MODEL_ID) |
</phase_requirements>

---

## Summary

Phase 1 establishes the stable HTTP boundary between the OpenClaw container (NemoClaw) and the career_agent Python module. The integration path is a thin FastAPI service (`career_agent/src/api.py`) that imports and exposes `PhoenixApp` over HTTP, plus an OpenClaw SKILL.md that teaches NemoClaw which endpoints to call. No existing career_agent logic changes — only new files are added and the Docker Compose extended. This is the lowest-risk, highest-leverage phase: proving end-to-end connectivity before any feature development.

The codebase inspection reveals three concrete changes beyond new files: (1) the `MemoryService` hardcodes `path="./qdrant_db"` which breaks when running inside a container at a non-root working directory — it must be changed to use the shared brain volume path `/brain/qdrant_db`; (2) all three Gemini model ID strings (`gemini-1.5-flash` in hunter.py, `gemini-1.5-pro` in tailor.py, `MODEL_ID=gemini-1.5-flash` in docker-compose.yml) must be updated to `gemini-2.5-flash`; (3) the sidecar needs its own Dockerfile because the OpenClaw container is a pre-built image (`ghcr.io/openclaw/openclaw:latest`) — it cannot be used to run Python.

The existing CI pipeline (flake8, bandit, .env.example validation) already runs on all Python files at repo root and will cover new files without changes. The CD pipeline deploys the entire repo via SCP then runs `docker compose up -d --force-recreate`, so adding a `career-agent` service to `docker-compose.yml` is enough to include it in deployments. The only CI gap is the missing `NEMO_AUTH_USER_ID` and `TELEGRAM_BOT_TOKEN` variables from `.env.example` — it only contains `DOMAIN_NAME` and `NODE_ENV`.

**Primary recommendation:** Add `career_agent/Dockerfile`, `career_agent/src/api.py`, and `skills/career_agent/SKILL.md` — then extend `docker-compose.yml` with the `career-agent` service and update three model ID strings. The existing pipeline deploys it automatically.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.115.x | HTTP framework for sidecar API | Standard async Python HTTP framework; native Pydantic v2 integration; zero-overhead lifespan context manager for APScheduler (later phases) |
| uvicorn | 0.34.x | ASGI server | Standard fastapi production server; single process is correct for single-VPS single-user deployment |
| python-dotenv | 1.0.x | .env loading in sidecar container | Already used in CI pipeline install step; loads GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID into sidecar process |

### Existing (keep, no version change needed)
| Library | Current Version | Purpose | Notes |
|---------|----------------|---------|-------|
| playwright | 1.58.0 | Browser automation base | Already installed in venv; patchright replaces playwright-stealth but is Phase 2 work — do NOT migrate in Phase 1 |
| playwright-stealth | 2.0.2 | Anti-detection (current) | Keep for Phase 1 — stealth migration is Phase 2 scope |
| pydantic | 2.12.5 | Data models | Already installed; PhoenixApp response models are compatible |
| pyyaml | 6.0.3 | Selector config | Already installed |

### New dependencies for Phase 1 only
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| fastapi | 0.115.x | Sidecar HTTP server | New |
| uvicorn[standard] | 0.34.x | ASGI server | New; [standard] installs uvloop for better async perf |
| httpx | 0.27.x | HTTP client (for health check tests) | New; also needed by openai SDK |
| openai | 1.x | Gemini via OpenAI-compat layer | Must be explicitly installed — not in current venv |
| qdrant-client | 1.17.1 | Vector DB client | Must be explicitly installed — not in current venv |

**Version verification (npm view equivalent for PyPI):**
```bash
pip index versions fastapi 2>/dev/null | head -1
pip index versions uvicorn 2>/dev/null | head -1
```

**Installation (career_agent/requirements.txt — new file):**
```bash
fastapi==0.115.12
uvicorn[standard]==0.34.2
httpx==0.27.2
openai==1.75.0
qdrant-client==1.17.1
pydantic==2.12.5
pyyaml==6.0.3
playwright==1.58.0
playwright-stealth==2.0.2
python-dotenv==1.0.1
```

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FastAPI | Flask | Flask lacks native async; PhoenixApp is asyncio-native; mixing sync Flask with async PhoenixApp requires `asyncio.run()` hacks |
| FastAPI | Starlette (bare) | FastAPI IS Starlette with auto-docs and Pydantic validation — use FastAPI for the OpenAPI schema generation which helps document skill endpoints |
| uvicorn | gunicorn | gunicorn is multi-process; single-VPS single-user agent does not benefit; uvicorn is simpler |

---

## Architecture Patterns

### Recommended Project Structure
```
nemoclaw-standalone/
├── docker-compose.yml              # MODIFY: add career-agent service
├── .env.example                    # MODIFY: add NEMO_AUTH_USER_ID, TELEGRAM_CHAT_ID
├── agent.md                        # MODIFY: add career_agent skill reference
├── brain/                          # EXISTING: shared brain volume (unchanged)
├── skills/
│   └── career_agent/
│       └── SKILL.md                # NEW: OpenClaw skill definition
└── career_agent/
    ├── Dockerfile                  # NEW: Python 3.11-slim image
    ├── requirements.txt            # NEW: pinned dependencies
    └── src/
        ├── api.py                  # NEW: FastAPI sidecar entrypoint
        ├── app.py                  # MODIFY: fix MemoryService path + model IDs (INFRA-06)
        ├── hunter.py               # MODIFY: gemini-1.5-flash → gemini-2.5-flash (INFRA-06)
        ├── tailor.py               # MODIFY: gemini-1.5-pro → gemini-2.5-flash (INFRA-06)
        ├── memory.py               # MODIFY: ./qdrant_db → /brain/qdrant_db (INFRA-03)
        └── client_factory.py       # NO CHANGE: OpenAI-compat pattern stays
```

### Pattern 1: FastAPI Sidecar Wrapping PhoenixApp
**What:** `career_agent/src/api.py` imports `PhoenixApp` and exposes three HTTP endpoints. No logic duplication — it is a thin HTTP shim.
**When to use:** Any time an LLM agent (OpenClaw) needs to invoke Python that cannot run inside the LLM container.
**Example:**
```python
# Source: FastAPI official docs + OpenClaw skill HTTP integration pattern
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .app import PhoenixApp

app_instance: PhoenixApp = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global app_instance
    brain_path = "/brain"  # matches Docker volume mount
    app_instance = PhoenixApp(brain_path=brain_path)
    yield
    app_instance = None

app = FastAPI(lifespan=lifespan)

@app.post("/cycle")
async def run_cycle(keyword: str = "AI Engineer", location: str = "France"):
    await app_instance.run_cycle(keyword=keyword, location=location)
    return {"status": "ok", "keyword": keyword, "location": location}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/pipeline")
async def pipeline():
    # Returns list of processed job records from MemoryService
    records = app_instance.memory.client.scroll(
        collection_name="job_applications", limit=100
    )
    return {"jobs": [r.payload for r in records[0]]}
```

### Pattern 2: Docker Compose Two-Service with Shared Brain Volume
**What:** Add `career-agent` service to `docker-compose.yml`. Both services mount `./brain` at different container paths: OpenClaw at `/app/brain`, sidecar at `/brain`.
**When to use:** Single-VPS deployment where both services must read/write the same brain data and Qdrant database.
**Example:**
```yaml
# Append to existing docker-compose.yml
  career-agent:
    build: ./career_agent
    container_name: career-agent
    restart: unless-stopped
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=${NEMO_AUTH_USER_ID}
    volumes:
      - ./brain:/brain          # shared with openclaw at /app/brain
    networks:
      - traefik-net             # same network so openclaw can reach http://career-agent:8001
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 256M
```

**Critical:** Both containers MUST be on `traefik-net` for OpenClaw to reach `http://career-agent:8001`. The service name `career-agent` becomes the Docker DNS hostname on that network.

### Pattern 3: OpenClaw SKILL.md Definition
**What:** A YAML-format file placed at `skills/career_agent/SKILL.md` (or mounted into the OpenClaw container at a path set by the skill system). Teaches NemoClaw which HTTP endpoints to call without any code in the OpenClaw container.
**When to use:** Every time NemoClaw needs to call an external Python service.
**Example:**
```yaml
# Source: OpenClaw official docs https://docs.openclaw.ai/tools/skills
name: career_agent
description: Autonomous job-hunting tool. Use to run a job search cycle, check pipeline status, or retrieve matched applications.
tools:
  - name: run_cycle
    description: Start a job search and scoring cycle. Call when the user asks to search for jobs or run the agent.
    method: POST
    url: http://career-agent:8001/cycle
    parameters:
      keyword:
        type: string
        required: true
        description: Job search keyword (e.g. "AI Engineer", "Backend Developer")
      location:
        type: string
        default: "France"
        description: Job search location
  - name: get_pipeline
    description: Return current application pipeline with statuses. Call for /status command.
    method: GET
    url: http://career-agent:8001/pipeline
  - name: health_check
    description: Verify the career agent sidecar is running.
    method: GET
    url: http://career-agent:8001/health
```

**OpenClaw skill mount:** The SKILL.md must either be mounted into the OpenClaw container or placed in a directory that OpenClaw reads at startup. Based on codebase inspection, `agent.md` is mounted at `/app/agent.md`. Skills likely go to `/app/skills/` or are configured via environment variable — this needs confirmation during implementation (see Open Questions).

### Pattern 4: Gemini Model ID Upgrade (INFRA-06)
**What:** Change three hardcoded model ID strings across the codebase. No API change, no client factory change — only the string value.
**Files to change:**
```
career_agent/src/hunter.py    line 62:  model="gemini-1.5-flash"  →  model="gemini-2.5-flash"
career_agent/src/tailor.py    line 32:  model="gemini-1.5-pro"    →  model="gemini-2.5-flash"
docker-compose.yml            line 10:  MODEL_ID=gemini-1.5-flash →  MODEL_ID=gemini-2.5-flash
```
**Verification command:** `grep -r "gemini-1.5" . --include="*.py" --include="*.yml"` must return zero results after change.

### Pattern 5: MemoryService Path Fix (INFRA-03 prerequisite)
**What:** `memory.py` line 16 hardcodes `QdrantClient(path="./qdrant_db")`. When the sidecar runs in Docker with `/brain` as the working-directory-agnostic volume mount, this must be `/brain/qdrant_db`.
**Why:** The current path `./qdrant_db` resolves relative to the process working directory inside the container, not to the mounted brain volume. Qdrant data would not persist across container restarts and would not be shared with the OpenClaw container.
**Fix:**
```python
# career_agent/src/memory.py - change line 16
import os
# Before: self.client = QdrantClient(path="./qdrant_db")
# After:
brain_path = os.environ.get("BRAIN_PATH", "/brain")
self.client = QdrantClient(path=os.path.join(brain_path, "qdrant_db"))
```
Or pass `brain_path` into `MemoryService.__init__()` consistent with the existing `HunterService` and `PhoenixApp` pattern.

### Pattern 6: Dockerfile for career_agent Sidecar
**What:** `career_agent/Dockerfile` that builds the sidecar image. Use Python 3.11-slim, install requirements, install Playwright Chromium, expose port 8001.
**Example:**
```dockerfile
# career_agent/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system deps for Playwright Chromium
RUN apt-get update && apt-get install -y \
    wget curl libglib2.0-0 libnss3 libgconf-2-4 \
    libfontconfig1 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 \
    libasound2 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY . .

EXPOSE 8001
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8001"]
```

**Note:** Playwright Chromium install adds ~400MB to the image. This is expected and acceptable. The sidecar image will be ~600-700MB total. On a 2GB VPS with the existing openclaw container (~500MB), total memory usage during Phase 1 (before scraping is active) is well within limits.

### Anti-Patterns to Avoid
- **Running PhoenixApp as subprocess of OpenClaw:** Playwright cannot run inside the OpenClaw container (no Chromium installed, memory conflicts). Use the sidecar HTTP boundary instead.
- **Sharing the OpenClaw container image for the sidecar:** `ghcr.io/openclaw/openclaw:latest` is a pre-built closed image — it cannot be modified to include Python career_agent code. A separate `career-agent` service with its own Dockerfile is required.
- **Exposing port 8001 to the public internet via Traefik:** The career-agent sidecar is internal-only. Do NOT add Traefik labels to it. OpenClaw reaches it via `http://career-agent:8001` on the shared `traefik-net` Docker network. No public exposure needed.
- **Using `docker-compose.yml` `depends_on` with `condition: service_healthy`:** While tempting, the career-agent startup (Playwright install + app init) can take 20-30 seconds. Set `depends_on` with `condition: service_started` only, not `service_healthy`, to avoid blocking OpenClaw startup.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP routing and request validation | Custom WSGI/ASGI handler | FastAPI | OpenAPI schema generation, Pydantic v2 auto-validation, 10x less boilerplate |
| Container health check | Custom TCP probe script | FastAPI `GET /health` + Docker healthcheck directive | Docker-native, no extra tooling |
| Environment variable loading | Manual `os.getenv()` chains | python-dotenv in Dockerfile CMD or FastAPI startup | Handles .env file loading in local dev and respects env vars already set in production |
| Playwright Chromium system deps | Manual apt-get research | Use the Playwright-official apt dependency list | Missing one lib causes mysterious launch failures; the list changes with Playwright versions |

**Key insight:** Phase 1 is integration plumbing, not feature work. Every component exists: FastAPI, OpenClaw skills, Docker Compose shared volumes, Python 3.11. The only work is wiring them together with the correct paths and service names.

---

## Common Pitfalls

### Pitfall 1: MemoryService Path Resolves to Wrong Location Inside Container
**What goes wrong:** `QdrantClient(path="./qdrant_db")` creates the Qdrant database relative to the container's working directory (`/app` in the Dockerfile above), NOT inside the mounted `/brain` volume. Qdrant data is not shared with OpenClaw and is lost on container restart.
**Why it happens:** The existing codebase was written to run as a local CLI tool (`python -m career_agent.src.app`) where `./qdrant_db` is correct relative to the repo root. Containerization changes the working directory.
**How to avoid:** Pass `brain_path` into `MemoryService.__init__()` and derive the Qdrant path from it: `os.path.join(brain_path, "qdrant_db")`. This is already the pattern used by `HunterService` and `TailorService`.
**Warning signs:** `docker exec career-agent ls /app/qdrant_db` shows data while `docker exec career-agent ls /brain/qdrant_db` shows nothing.

### Pitfall 2: OpenClaw Cannot Reach career-agent by DNS Name
**What goes wrong:** SKILL.md uses `http://career-agent:8001` but OpenClaw returns "connection refused" or "hostname not found".
**Why it happens:** Docker service DNS only works between containers on the SAME network. If `career-agent` is not added to `traefik-net` (the network OpenClaw is on), Docker DNS resolution fails.
**How to avoid:** Verify both services are listed under `networks: - traefik-net` in docker-compose.yml. After deployment, test with: `docker exec openclaw curl -f http://career-agent:8001/health`.
**Warning signs:** `docker compose ps` shows both containers healthy but HTTP calls from NemoClaw fail.

### Pitfall 3: Playwright Fails to Launch Inside Docker (Missing System Libraries)
**What goes wrong:** `playwright install chromium` succeeds but at runtime `playwright.launch()` throws `Error: Failed to launch chromium!` with a missing shared library error.
**Why it happens:** Python 3.11-slim base image omits many system libraries that Chromium requires (libglib, libnss3, libatk, libdrm, etc.).
**How to avoid:** Use the full apt-get dependency list from the Playwright Dockerfile template. Alternatively use `mcr.microsoft.com/playwright/python:v1.58.0-jammy` as the base image — it includes all Playwright deps pre-installed (but adds ~400MB).
**Warning signs:** `docker logs career-agent` shows Playwright launch errors immediately on startup; `/health` returns 500.

### Pitfall 4: Missing TELEGRAM_CHAT_ID Env Var Breaks Sidecar Start
**What goes wrong:** Later phases need `TELEGRAM_CHAT_ID` to push notifications. If it's missing from the sidecar's environment from Phase 1, wiring it in later requires a docker-compose.yml change and full redeploy.
**Why it happens:** The sidecar currently needs `GEMINI_API_KEY` to serve the `/cycle` endpoint. `TELEGRAM_CHAT_ID` (= `NEMO_AUTH_USER_ID` value) is only needed for Phase 4 reporting. Forgetting to add it in Phase 1 creates tech debt.
**How to avoid:** Include `TELEGRAM_CHAT_ID=${NEMO_AUTH_USER_ID}` and `TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}` in the sidecar's environment block from Phase 1 even if not yet used. Cost: zero. Benefit: no Phase 4 docker-compose.yml change.
**Warning signs:** Phase 4 reporter fails with `KeyError: TELEGRAM_CHAT_ID`.

### Pitfall 5: CI Fails on New Python Files Due to Missing Imports
**What goes wrong:** `flake8 . --select=E9,F63,F7,F82` catches undefined names (`F82`). If `career_agent/src/api.py` imports `PhoenixApp` from a relative import but the CI runner does not install career_agent's dependencies, flake8 will flag `F821: undefined name`.
**Why it happens:** CI installs `requirements.txt` at root if it exists, but there is no root `requirements.txt`. The CI step does: `if [ -f requirements.txt ]; then pip install -r requirements.txt; fi`. Since no root requirements.txt exists, only flake8/bandit/python-dotenv are installed.
**How to avoid:** Either add a root `requirements.txt` that installs career_agent's deps, or add a CI step: `pip install -r career_agent/requirements.txt`. The simpler fix is updating the CI `if` condition to also install from `career_agent/requirements.txt` if it exists.
**Warning signs:** CI passes locally (venv has all deps) but fails in GitHub Actions on `F82` errors.

### Pitfall 6: .env.example Validation Fails If New Vars Not Added
**What goes wrong:** CI validates `.env.example` exists (it does) but the file only contains `DOMAIN_NAME` and `NODE_ENV`. The sidecar needs `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `NEMO_AUTH_USER_ID`, `NEMO_PAIRING_CODE`. New developers cloning the repo have no template for these.
**Why it happens:** `.env.example` was created as a stub and never populated.
**How to avoid:** Update `.env.example` with all required variables as part of Phase 1 (it's already flagged as a stub — now is the time to fix it).
**Warning signs:** CI passes but local setup fails with `ValueError: GEMINI_API_KEY not found`.

### Pitfall 7: agent.md Needs Updating for Skill Discovery
**What goes wrong:** NemoClaw does not know about the career_agent skill unless `agent.md` or the OpenClaw configuration references it. The skill file exists on disk but OpenClaw may not load it automatically.
**Why it happens:** OpenClaw's skill loading mechanism depends on where the SKILL.md is placed and potentially an env var (`OPENCLAW_SKILLS_PATH` or similar). The exact mechanism needs verification during implementation.
**How to avoid:** During implementation, test: mount `skills/` into the OpenClaw container and verify that sending a Telegram message triggers a skill HTTP call. Update `agent.md` to mention the career_agent capabilities. Check OpenClaw container logs for skill registration messages on startup.
**Warning signs:** NemoClaw responds to "run a job search" with "I don't have access to job search tools" rather than invoking the skill.

---

## Code Examples

### FastAPI Sidecar Entry Point
```python
# Source: FastAPI official lifespan docs + project pattern
# career_agent/src/api.py
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from .app import PhoenixApp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SidecarAPI")

_app_instance: Optional[PhoenixApp] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _app_instance
    brain_path = os.environ.get("BRAIN_PATH", "/brain")
    logger.info(f"Initializing PhoenixApp with brain_path={brain_path}")
    _app_instance = PhoenixApp(brain_path=brain_path)
    logger.info("Career Agent sidecar ready")
    yield
    _app_instance = None

app = FastAPI(title="Career Agent Sidecar", version="1.0.0", lifespan=lifespan)

class CycleRequest(BaseModel):
    keyword: str = "AI Engineer"
    location: str = "France"

@app.post("/cycle")
async def run_cycle(request: CycleRequest):
    if _app_instance is None:
        raise HTTPException(status_code=503, detail="App not initialized")
    await _app_instance.run_cycle(keyword=request.keyword, location=request.location)
    return {"status": "ok", "keyword": request.keyword, "location": request.location}

@app.get("/health")
async def health():
    return {"status": "healthy", "app_ready": _app_instance is not None}

@app.get("/pipeline")
async def pipeline():
    if _app_instance is None:
        raise HTTPException(status_code=503, detail="App not initialized")
    results = _app_instance.memory.client.scroll(
        collection_name="job_applications", limit=100
    )
    return {"jobs": [r.payload for r in results[0]]}
```

### Docker Compose career-agent Service Addition
```yaml
# Source: project docker-compose.yml + architecture research pattern
# Append to existing docker-compose.yml services block:

  career-agent:
    build: ./career_agent
    container_name: career-agent
    restart: unless-stopped
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=${NEMO_AUTH_USER_ID}
      - BRAIN_PATH=/brain
      - LOG_LEVEL=INFO
    volumes:
      - ./brain:/brain
    networks:
      - traefik-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 256M
```

### OpenClaw SKILL.md
```yaml
# Source: OpenClaw official docs https://docs.openclaw.ai/tools/skills
# File: skills/career_agent/SKILL.md
name: career_agent
description: >
  Autonomous job hunting tool. Use this skill to run a job search and scoring
  cycle, retrieve current application pipeline status, or verify the career
  agent is running. The career agent scrapes job listings, scores them against
  the candidate profile, and generates cover letters for matches.
tools:
  - name: run_cycle
    description: >
      Start a job search, scoring, and cover letter generation cycle.
      Call when the user asks to search for jobs, run Phoenix, or trigger
      the career agent. Returns a summary of what was found and processed.
    method: POST
    url: http://career-agent:8001/cycle
    parameters:
      keyword:
        type: string
        required: true
        description: "Job title or keyword to search for (e.g. 'AI Engineer')"
      location:
        type: string
        required: false
        default: "France"
        description: "Target job location"

  - name: get_pipeline
    description: >
      Retrieve the current application pipeline — all jobs processed,
      their scores, and statuses (READY, SKIPPED). Use for /status
      queries and pipeline overview.
    method: GET
    url: http://career-agent:8001/pipeline

  - name: health_check
    description: Check if the career agent sidecar is running and ready.
    method: GET
    url: http://career-agent:8001/health
```

### Gemini Model ID Changes (INFRA-06)
```python
# career_agent/src/hunter.py — line 62
# Before:
model="gemini-1.5-flash",
# After:
model="gemini-2.5-flash",

# career_agent/src/tailor.py — line 32
# Before:
model="gemini-1.5-pro",
# After:
model="gemini-2.5-flash",
```

```yaml
# docker-compose.yml — line 10
# Before:
- MODEL_ID=gemini-1.5-flash
# After:
- MODEL_ID=gemini-2.5-flash
```

### MemoryService Path Fix
```python
# career_agent/src/memory.py
# Before (line 16):
self.client = QdrantClient(path="./qdrant_db")

# After — accept brain_path in __init__ or read from env:
import os
brain_path = os.environ.get("BRAIN_PATH", "./brain")  # fallback for local CLI use
self.client = QdrantClient(path=os.path.join(brain_path, "qdrant_db"))
```

```python
# career_agent/src/app.py — update MemoryService init call if passing brain_path:
self.memory = MemoryService(brain_path=brain_path)
# (current: self.memory = MemoryService()  — no brain_path passed)
```

### CI Fix for career_agent Dependencies
```yaml
# .github/workflows/nemoclaw-ci.yml — update "Install dependencies" step:
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install flake8 bandit python-dotenv
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          if [ -f career_agent/requirements.txt ]; then pip install -r career_agent/requirements.txt; fi
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| gemini-1.5-flash / gemini-1.5-pro | gemini-2.5-flash | Google deprecation March 2026 | Both hardcoded strings must change; same client_factory.py, same endpoint |
| playwright-stealth (JS property patching) | patchright (CDP binary patching) | Cloudflare AI Labyrinth March 2025 | Phase 2 work — NOT Phase 1 scope |
| Direct CLI invocation via `python -m career_agent.src.app` | FastAPI sidecar over HTTP | Phase 1 (this phase) | Enables OpenClaw skill integration; crash isolation; typed contracts |

**Current state of installed venv (confirmed):**
- `playwright==1.58.0` — installed
- `playwright-stealth==2.0.2` — installed
- `pydantic==2.12.5` — installed
- `pyyaml==6.0.3` — installed
- Missing: `fastapi`, `uvicorn`, `openai`, `qdrant-client`, `httpx` — all must be added to `career_agent/requirements.txt`

---

## Open Questions

1. **OpenClaw skill loading mechanism: path and env var**
   - What we know: OpenClaw reads `agent.md` from a path set by `OPENCLAW_AGENT_IDENTITY`. Skills likely use a similar env var (e.g., `OPENCLAW_SKILLS_PATH`).
   - What's unclear: The exact env var name, whether SKILL.md must be mounted into the OpenClaw container or placed in the repo, and whether the skill name in SKILL.md must match a specific convention.
   - Recommendation: During implementation, check `docker exec openclaw env | grep SKILL` and `docker exec openclaw ls /app/` to discover existing skill conventions. Review OpenClaw container startup logs for skill registration messages. If no env var found, mount `./skills:/app/skills:ro` into the OpenClaw container and test.

2. **PhoenixApp async initialization with Playwright inside FastAPI lifespan**
   - What we know: `PhoenixApp.__init__()` is synchronous (standard `__init__`). It creates `HunterService`, which creates `Scraper`, which calls `_load_selectors()` synchronously. Playwright is only launched inside async methods (`search_linkedin_jobs`, `get_linkedin_job_description`).
   - What's unclear: Whether FastAPI's lifespan context can safely call synchronous `PhoenixApp.__init__()` without blocking the event loop at startup.
   - Recommendation: `PhoenixApp.__init__()` only does file I/O (`_load_bio`, `_load_specs`, `_load_selectors`) and object construction — no Playwright launch, no network calls. This is safe in FastAPI lifespan. No async init wrapper needed for Phase 1.

3. **NEMO_AUTH_USER_ID vs TELEGRAM_CHAT_ID naming**
   - What we know: `NEMO_AUTH_USER_ID` is used as OpenClaw's user whitelist in docker-compose.yml. The reporter.py (Phase 4) needs a `TELEGRAM_CHAT_ID` to push messages.
   - What's unclear: Whether `NEMO_AUTH_USER_ID` is the same numeric Telegram user ID needed for `sendMessage` calls, or whether it's a different identifier.
   - Recommendation: In docker-compose.yml, set `TELEGRAM_CHAT_ID=${NEMO_AUTH_USER_ID}` for the sidecar — they refer to the same Telegram user. Verify during integration testing by checking if the chat ID format matches what `sendMessage` expects (numeric user ID for private chats).

4. **Qdrant ID type: string UUID vs int**
   - What we know: `memory.py` passes `id=job_id_uuid` as a string to `PointStruct`. The codebase concerns audit flagged this as a potential type mismatch — Qdrant accepts UUID objects or 64-bit unsigned integers as IDs.
   - What's unclear: Whether current qdrant-client 1.17.1 accepts string UUIDs directly or silently coerces them.
   - Recommendation: When fixing `MemoryService` for Phase 1, explicitly pass `id=uuid.uuid5(self.namespace, job_url)` (the UUID object, not its string representation) to avoid the type mismatch. This is a safe, non-breaking fix that resolves the known bug.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (not yet installed — Wave 0 gap) |
| Config file | none — see Wave 0 |
| Quick run command | `pytest career_agent/tests/ -x -q` |
| Full suite command | `pytest career_agent/tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | FastAPI sidecar starts and responds to GET /health | smoke | `pytest career_agent/tests/test_api.py::test_health_endpoint -x` | Wave 0 |
| INFRA-01 | POST /cycle returns 200 with PhoenixApp mocked | unit | `pytest career_agent/tests/test_api.py::test_cycle_endpoint_mocked -x` | Wave 0 |
| INFRA-02 | SKILL.md is valid YAML with required tool fields | unit | `pytest career_agent/tests/test_skill_md.py::test_skill_schema -x` | Wave 0 |
| INFRA-03 | MemoryService uses BRAIN_PATH env var for Qdrant path | unit | `pytest career_agent/tests/test_memory.py::test_brain_path_env -x` | Wave 0 |
| INFRA-04 | flake8 passes on career_agent/src/api.py (no F82 errors) | lint | `flake8 career_agent/src/api.py --select=E9,F63,F7,F82` | Wave 0 (ci only) |
| INFRA-06 | No gemini-1.5-* strings remain anywhere in repo | grep | `grep -r "gemini-1.5" . --include="*.py" --include="*.yml" \| wc -l` returns 0 | N/A — shell check |

### Sampling Rate
- **Per task commit:** `pytest career_agent/tests/ -x -q`
- **Per wave merge:** `pytest career_agent/tests/ -v`
- **Phase gate:** Full suite green + `grep -r "gemini-1.5"` returns zero + `docker compose up` both containers healthy before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `career_agent/tests/__init__.py` — package init
- [ ] `career_agent/tests/test_api.py` — covers INFRA-01 (health, cycle endpoints with mocked PhoenixApp)
- [ ] `career_agent/tests/test_skill_md.py` — covers INFRA-02 (SKILL.md YAML schema validation)
- [ ] `career_agent/tests/test_memory.py` — covers INFRA-03 (MemoryService BRAIN_PATH env var behavior)
- [ ] `career_agent/tests/conftest.py` — shared fixtures (temp brain dir, mock PhoenixApp)
- [ ] Framework install: `pip install pytest pytest-asyncio pytest-mock httpx` — add to career_agent/requirements.txt (dev section or separate requirements-dev.txt)

---

## Sources

### Primary (HIGH confidence)
- OpenClaw official docs: https://docs.openclaw.ai/tools/skills — skill HTTP integration pattern
- OpenClaw tools invoke HTTP API: https://docs.openclaw.ai/gateway/tools-invoke-http-api — /tools/invoke endpoint
- FastAPI official docs lifespan: https://fastapi.tiangolo.com/advanced/events/ — lifespan context manager pattern
- FastAPI official docs: https://fastapi.tiangolo.com/ — framework overview and Pydantic v2 integration
- Google AI official docs (confirmed March 2026) — gemini-1.5-* deprecated, gemini-2.5-flash recommended
- Docker Compose docs — multi-service shared volume, service DNS resolution on custom networks
- Codebase inspection — career_agent/src/memory.py line 16 (qdrant_db path), hunter.py line 62, tailor.py line 32, docker-compose.yml line 10 (direct file read, HIGH confidence)

### Secondary (MEDIUM confidence)
- ZenRows Playwright stealth guide — confirms playwright-stealth failure on enterprise anti-bot (relevant context for NOT migrating in Phase 1)
- APScheduler + FastAPI lifespan pattern — https://betterstack.com/community/guides/scaling-python/apscheduler-scheduled-tasks/ — verified for later phases
- patchright PyPI + GitHub — version 1.58.2 confirmed (Phase 2 dependency, context only)

### Tertiary (LOW confidence)
- OpenClaw SKILL.md exact mount path and env var name — inferred from `agent.md` mount pattern in docker-compose.yml; needs runtime verification during implementation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — FastAPI/uvicorn are the dominant Python async HTTP stack; versions verified against PyPI; existing venv packages confirmed by direct inspection
- Architecture: HIGH — OpenClaw skill pattern verified via official docs; Docker Compose shared volume is standard documented practice; MemoryService path issue confirmed by code inspection
- Pitfalls: HIGH for path/network pitfalls (directly derived from code inspection); MEDIUM for OpenClaw skill mount path (inferred, needs runtime verification)

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable stack — FastAPI/Docker patterns do not change; Gemini model IDs confirmed current)
