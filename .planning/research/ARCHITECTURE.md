# Architecture Research

**Domain:** Autonomous job-hunting agent — LLM orchestrator + Python tool layer + Telegram interface
**Researched:** 2026-03-23
**Confidence:** HIGH (OpenClaw integration pattern verified via official docs; tool layer based on existing code inspection; scheduling patterns verified against APScheduler docs)

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        TELEGRAM INTERFACE                            │
│   User sends commands  ←→  NemoClaw pushes digests + alerts          │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │ Telegram Bot API (long polling)
┌─────────────────────────────────▼────────────────────────────────────┐
│                     OPENCLAW CONTAINER (port 8080)                   │
│   LLM (Gemini via OpenAI-compat layer)                               │
│   Agent identity: /app/agent.md                                      │
│   Session state: openclaw-workspace volume                           │
│   Mounted brain: /app/brain  (shared read/write with tool layer)     │
│                                                                      │
│   Invocation paths:                                                  │
│   ┌─────────────────┐   ┌────────────────────┐                       │
│   │  OpenClaw Skill  │   │  POST /tools/invoke │                      │
│   │  (SKILL.md +    │   │  HTTP endpoint —    │                      │
│   │   shell/Python) │   │  external trigger   │                      │
│   └────────┬────────┘   └──────────┬──────────┘                      │
└────────────┼──────────────────────┼──────────────────────────────────┘
             │ HTTP / subprocess     │ HTTP webhook
┌────────────▼──────────────────────▼──────────────────────────────────┐
│                   CAREER AGENT SIDECAR (FastAPI)                     │
│   Thin HTTP wrapper around career_agent/ Python module               │
│   Exposes:  POST /cycle  POST /status  GET /pipeline                 │
│   Runs:     PhoenixApp.run_cycle() via asyncio                       │
│   Scheduler: APScheduler AsyncIOScheduler (cron, daily)              │
│                                                                      │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────┐ ┌────────────────┐  │
│  │  Scraper    │ │ HunterService│ │  Tailor   │ │ ApplyService   │  │
│  │ (Playwright │ │  (Gemini     │ │ (Gemini   │ │ (Playwright    │  │
│  │  + stealth) │ │   scoring)   │ │  letters) │ │  form fill)    │  │
│  └──────┬──────┘ └──────┬───────┘ └─────┬─────┘ └───────┬────────┘  │
└─────────┼───────────────┼───────────────┼───────────────┼────────────┘
          │               │               │               │
┌─────────▼───────────────▼───────────────▼───────────────▼────────────┐
│                      SHARED BRAIN VOLUME  ./brain/                   │
│   Bio_Context.md        Target_Specs.json   applications/            │
│   qdrant_db/            (Qdrant local)                               │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Existing / New |
|-----------|---------------|----------------|
| OpenClaw container | LLM reasoning, Telegram I/O, skill dispatch, session memory | Existing |
| OpenClaw Skill (career_agent skill) | SKILL.md definition that teaches NemoClaw to call the sidecar API | New |
| Career Agent Sidecar (FastAPI) | HTTP wrapper around PhoenixApp; exposes cycle, status, pipeline endpoints | New |
| APScheduler | Cron-based trigger for daily autonomous cycles inside the sidecar | New |
| Scraper (Playwright + stealth) | Headless browser scraping of LinkedIn, Welcome to the Jungle, APEC, etc. | Existing (extend) |
| HunterService | Fast-fail exclusion check + Gemini scoring → MatchReport | Existing |
| TailorService | Gemini cover letter generation → TailoredContent | Existing |
| ApplyService | Playwright form-fill automation for supported platforms | New |
| FollowUpService | Timed follow-up message generation and send | New |
| MemoryService (Qdrant) | Deduplication by URL (UUIDv5), application status tracking | Existing (extend) |
| brain/ volume | Shared filesystem between OpenClaw container and Career Agent sidecar | Existing (extend) |
| Telegram reporter | push_message() helper — career agent sidecar calls Telegram Bot API directly | New |

## Recommended Project Structure

```
nemoclaw-standalone/
├── docker-compose.yml              # Existing: openclaw container
├── agent.md                        # Existing: NemoClaw identity
├── brain/                          # Existing: shared brain volume
│   ├── Bio_Context.md
│   ├── Target_Specs.json
│   └── applications/               # Existing: per-job artifacts (extend)
│       └── <uuid>/
│           ├── cover_letter.txt
│           ├── match_report.json
│           └── apply_result.json   # New: application submission receipt
├── career_agent/
│   ├── config/
│   │   └── selectors.yaml          # Existing: externalized CSS selectors
│   └── src/
│       ├── app.py                  # Existing: PhoenixApp orchestrator
│       ├── hunter.py               # Existing: HunterService
│       ├── tailor.py               # Existing: TailorService
│       ├── scraper.py              # Existing: Playwright scraper
│       ├── memory.py               # Existing: Qdrant MemoryService
│       ├── client_factory.py       # Existing: Gemini singleton
│       ├── apply.py                # New: ApplyService (form-fill)
│       ├── followup.py             # New: FollowUpService
│       ├── reporter.py             # New: Telegram push notifications
│       └── api.py                  # New: FastAPI sidecar entrypoint
├── skills/
│   └── career_agent/
│       └── SKILL.md                # New: OpenClaw skill definition
└── .planning/
    └── research/
```

### Structure Rationale

- **career_agent/src/api.py:** FastAPI thin wrapper. Does not duplicate logic — it imports PhoenixApp and exposes HTTP endpoints so OpenClaw can call it as a skill. Keeps career_agent/ self-contained.
- **skills/career_agent/SKILL.md:** OpenClaw skill definition in YAML + natural-language frontmatter. Teaches NemoClaw which HTTP endpoints to call for "run a job search cycle", "show pipeline status", etc. No code needed here — just schema.
- **brain/ (shared volume):** Both OpenClaw and the sidecar mount this path. Single source of truth for candidate data, application history, and Qdrant DB. No inter-service sync required.
- **career_agent/src/reporter.py:** The sidecar calls Telegram Bot API directly (HTTP POST to api.telegram.org) to push real-time alerts. NemoClaw handles command parsing; reporter handles outbound-only push.

## Architectural Patterns

### Pattern 1: Skill-as-HTTP-Proxy (OpenClaw invokes Python)

**What:** OpenClaw cannot natively run Python code. The integration path is a SKILL.md that maps natural-language tool calls to HTTP requests against the FastAPI sidecar. OpenClaw reads the skill schema, generates the correct JSON arguments, and POSTs to the sidecar's endpoints.

**When to use:** Any time the LLM-facing agent (NemoClaw/OpenClaw) needs to invoke a Python capability that lives in a separate process.

**Trade-offs:** Adds one network hop (localhost); HTTP overhead is negligible on a VPS. Benefit: clean process isolation — a crashed Playwright browser cannot take down the NemoClaw Telegram session.

**Example SKILL.md frontmatter:**
```yaml
name: career_agent
description: Run an autonomous job search cycle, check pipeline status, or retrieve results.
tools:
  - name: run_cycle
    description: Start a job search and scoring cycle for a given keyword and location.
    method: POST
    url: http://career-agent:8001/cycle
    parameters:
      keyword: {type: string, required: true}
      location: {type: string, default: "France"}
  - name: get_pipeline
    description: Return current application pipeline with statuses.
    method: GET
    url: http://career-agent:8001/pipeline
```

### Pattern 2: Shared-Volume State Store (brain/ as IPC)

**What:** OpenClaw container and career_agent sidecar share a single host directory (./brain) mounted at /app/brain and /brain respectively. State persists across restarts without a database migration — files and Qdrant's local on-disk store are the entire persistence layer.

**When to use:** Single-host deployments where both services are on the same machine. Eliminates network state sync.

**Trade-offs:** Works for a single VPS. Would need replacing with a shared object store (S3, Postgres) if the architecture ever splits across hosts. Acceptable given the single-server constraint.

**Example Docker Compose addition:**
```yaml
  career-agent:
    build: ./career_agent
    container_name: career-agent
    volumes:
      - ./brain:/brain          # matches PhoenixApp(brain_path="/brain")
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=${NEMO_AUTH_USER_ID}
    networks:
      - traefik-net
    ports:
      - "8001:8001"
```

### Pattern 3: APScheduler AsyncIOScheduler Inside FastAPI Lifespan

**What:** The sidecar uses APScheduler's AsyncIOScheduler (not BackgroundScheduler) to schedule daily cycles. It is started inside FastAPI's lifespan context manager so the scheduler shares the same event loop as the HTTP server. Cron trigger fires PhoenixApp.run_cycle() as a coroutine.

**When to use:** Asyncio-native applications where all I/O (Playwright, Gemini API, Qdrant) is already async. AsyncIOScheduler avoids thread-pool overhead and keeps the scheduler on the same event loop.

**Trade-offs:** If a cycle takes longer than the cron interval, APScheduler will skip the next run (coalesce: true behavior). For a daily cycle this is not an issue.

**Example:**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager
from fastapi import FastAPI

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(run_daily_cycle, "cron", hour=8, minute=0)
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
```

### Pattern 4: State Machine for Application Pipeline

**What:** Each job record in Qdrant carries a `status` field that transitions through a defined set of states. Transitions are one-directional. The MemoryService's `add_application()` upsert pattern (UUIDv5 idempotent key) handles the state store — subsequent upserts update the status without duplicating records.

**State machine:**
```
SCRAPED → SCORED → SKIPPED
              ↓
          TAILORED → APPLYING → APPLIED → VIEWED → INTERVIEW
                                    ↓               ↓
                                REJECTED        OFFER / NEGOTIATING
                                    ↓
                              FOLLOWED_UP (after no-response timeout)
```

**Trade-offs:** Flat string states in Qdrant payload are simple to query but offer no transition enforcement. For an autonomous single-user system, simplicity wins over formal state machine enforcement.

### Pattern 5: Direct Telegram Push for Reporting

**What:** The career agent sidecar does NOT route reports back through OpenClaw. It calls the Telegram Bot API directly (`POST https://api.telegram.org/bot{TOKEN}/sendMessage`) for outbound-only notifications: daily digests, real-time match alerts, application submission confirmations, and response alerts.

NemoClaw handles inbound commands. The sidecar handles outbound pushes. Responsibilities are split by direction of communication — no circular dependency.

**When to use:** When the LLM agent does not need to reason about the notification content (e.g., "application submitted to X at Y") — just send it.

**Trade-offs:** Two Telegram actors (NemoClaw for commands, reporter for push). Both use the same bot token. This is standard practice for Telegram bots: send-only flows bypass the bot session and post directly.

## Data Flow

### Flow 1: Autonomous Scheduled Cycle (no user input)

```
APScheduler (cron: 08:00 daily)
    ↓ triggers coroutine
PhoenixApp.run_cycle(keyword, location)
    ↓
Scraper.search_jobs()          ← per-platform: LinkedIn, WTTJ, APEC, ...
    ↓ list[JobRecord]
MemoryService.is_already_processed(url)   ← dedup via Qdrant UUIDv5
    ↓ unseen jobs only
HunterService.score_job(jd_text)         ← fast-fail exclusions + Gemini
    ↓ MatchReport (score, recommendation)
    ├─ SKIP → MemoryService.upsert(status=SKIPPED)
    └─ APPLY / TAILOR_REQUIRED →
        TailorService.customize_letter()  ← Gemini Pro
            ↓ TailoredContent
        MemoryService.upsert(status=TAILORED)
        ApplyService.submit(job, letter)  ← Playwright form-fill
            ↓ ApplyResult
        MemoryService.upsert(status=APPLIED)
        reporter.push_match_alert(job, score)  ← Telegram Bot API direct POST
    ↓ cycle complete
reporter.push_daily_digest(stats)        ← summary pushed to Telegram
```

### Flow 2: User-Triggered Command (Telegram → NemoClaw → Sidecar)

```
User: "run a search for 'data engineer' in Paris"
    ↓ Telegram message
OpenClaw (NemoClaw session)
    ↓ LLM reasoning → selects career_agent skill → run_cycle tool
    ↓ HTTP POST http://career-agent:8001/cycle  {keyword, location}
Career Agent Sidecar (FastAPI)
    ↓ PhoenixApp.run_cycle()
    ↓ [pipeline as above]
    ↓ HTTP 200  {jobs_scraped, matched, applied}
OpenClaw → Telegram reply: "Found 12 jobs, 3 matched, 2 applications submitted."
```

### Flow 3: Status Query

```
User: "show me my application pipeline"
    ↓ Telegram → OpenClaw → skill: get_pipeline
    ↓ HTTP GET http://career-agent:8001/pipeline
Sidecar: MemoryService.scroll_all() → list[ApplicationRecord]
    ↓ HTTP 200  JSON array
OpenClaw: formats as Telegram message table
```

### Flow 4: Follow-Up Check (Scheduler)

```
APScheduler (cron: daily)
    ↓
FollowUpService.check_pending()
    ↓ MemoryService.query(status=APPLIED, applied_days_ago >= N)
    ↓ TailorService.generate_followup_email()
    ↓ reporter.push_followup_alert()   ← Telegram notification to user
    ↓ MemoryService.upsert(status=FOLLOWED_UP)
```

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Telegram Bot API | Long poll (OpenClaw built-in) + direct HTTP POST from reporter.py | Two paths; same bot token; no conflict |
| Gemini API | AsyncOpenAI client via OpenAI-compat layer (existing client_factory.py) | Shared across hunter, tailor, openclaw container |
| LinkedIn | Playwright + playwright_stealth + human-scroll simulation | Advanced anti-bot since 2024-25; residential proxy recommended for production scale |
| Welcome to the Jungle | Playwright + stealth; site uses React SPA with public-ish job API | Selector externalization in selectors.yaml is the right pattern |
| APEC | Playwright or direct API (APEC has a documented JSON endpoint) | Verify API availability before building Playwright fallback |
| Qdrant (local) | Direct Python client, on-disk at ./qdrant_db inside brain/ | No network required; Qdrant local mode handles single-process access |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| OpenClaw ↔ Career Agent Sidecar | HTTP REST (localhost / docker network) via OpenClaw Skill | Only path NemoClaw can invoke Python; sidecar must be on same Docker network |
| Career Agent Sidecar ↔ brain/ | Shared Docker volume (./brain) | Both containers mount same host path |
| Career Agent Sidecar → Telegram | Direct HTTP POST to api.telegram.org (outbound only) | Requires TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID env vars in sidecar |
| Scraper ↔ HunterService | In-process Python (same asyncio event loop) | No IPC needed; Scraper is owned by HunterService |
| HunterService / TailorService ↔ Gemini | AsyncOpenAI singleton (client_factory.py) | Already implemented; shared across services |

## Build Order

The dependency graph determines the safe build sequence. Each phase must not break CI.

```
1. Career Agent HTTP Sidecar (api.py + FastAPI)
   └─ Wraps existing PhoenixApp — zero logic changes to existing code
   └─ Proves integration path before any new features

2. OpenClaw Skill (skills/career_agent/SKILL.md)
   └─ Requires sidecar to be callable
   └─ Validates end-to-end: Telegram command → NemoClaw → sidecar → brain

3. Scheduler (APScheduler inside sidecar lifespan)
   └─ Requires sidecar to be running
   └─ Proves autonomous operation without user trigger

4. Telegram Reporter (reporter.py)
   └─ Requires scheduler (to have events to report)
   └─ Push digest + match alerts

5. Multi-Platform Scraper Extension
   └─ Extend Scraper with WTTJ, APEC, Indeed scrapers
   └─ Add per-platform selectors to selectors.yaml
   └─ Requires sidecar (to be callable end-to-end before adding surface area)

6. Apply Service (apply.py)
   └─ Requires memory state machine with TAILORED status existing
   └─ Requires reporter to push application confirmations
   └─ Highest risk phase — Playwright form-fill is platform-specific

7. Follow-Up Service (followup.py)
   └─ Requires Apply producing APPLIED status records in Qdrant
   └─ Requires reporter for notifications

8. Status Tracking + Negotiation Prep
   └─ Requires all upstream statuses established
   └─ Enriches existing Qdrant records with inbound signals
```

## Anti-Patterns

### Anti-Pattern 1: Running PhoenixApp as a Subprocess of OpenClaw

**What people do:** Register a shell skill that calls `python -m career_agent.src.app` as a subprocess from inside the OpenClaw container.

**Why it's wrong:** Playwright chromium cannot run inside the OpenClaw container (not installed, no sandboxing, memory conflicts). Subprocess stderr is not observable to the LLM. No HTTP contract — the LLM cannot parse unstructured stdout. Career agent crashes take OpenClaw's session with them.

**Do this instead:** Run the career agent as a separate Docker Compose service with a FastAPI HTTP boundary. OpenClaw calls it via the skill HTTP client. Crash isolation, observable logs, typed responses.

### Anti-Pattern 2: Storing Application State Only in Brain/ Markdown Files

**What people do:** Write job status as markdown log files in brain/applications/ and query them by reading files.

**Why it's wrong:** No structured query — you cannot ask "how many jobs are in APPLIED status older than 7 days" without parsing every file. Qdrant is already in the stack and handles exactly this query pattern via payload filters.

**Do this instead:** Use Qdrant as the state store for all structured query needs. Use brain/applications/<uuid>/ directories only for large text artifacts (cover letters, JD text) — not for queryable metadata.

### Anti-Pattern 3: Polling Telegram for Job Application Responses

**What people do:** Build a polling loop inside the agent that periodically checks job platform inboxes for responses (applied / viewed / rejected signals).

**Why it's wrong:** Job platforms (LinkedIn, WTTJ) do not expose inbox read events via API. Playwright-based inbox scraping is extremely fragile and quickly detected. The signal is low-fidelity.

**Do this instead:** Track only what can be reliably observed — submission confirmation (ApplyService receipts) and user-reported updates. The user tells NemoClaw via Telegram "I got a response from X" and the agent updates Qdrant status. Semi-automatic status tracking beats brittle inbox scraping.

### Anti-Pattern 4: One Playwright Browser Instance per Job

**What people do:** The existing Scraper opens and closes a browser context for every single job description fetch (see scraper.py lines 69-80).

**Why it's wrong:** Each chromium launch takes 2-4 seconds of overhead. For a batch of 10 jobs, that is 20-40 seconds of wasted time before any scraping. Also, rapid repeated browser spawning raises fingerprinting risk.

**Do this instead:** Reuse a single browser context across a scraping session. Launch once, scrape N pages, close. Implement context-manager pattern on Scraper to manage browser lifecycle at the batch level, not the per-URL level.

### Anti-Pattern 5: Hardcoding scoring_threshold in HunterService

**What people do:** Default to 0.85 and never surface it as a runtime parameter.

**Why it's wrong:** The threshold is a user preference that changes with market conditions ("I'll accept a 0.70 match if I need more applications"). Forcing code changes for a config value breaks the autonomous-agent promise.

**Do this instead:** Read `scoring_threshold` from Target_Specs.json at scoring time (already partially in place via `_load_specs()`). Expose a Telegram command to update it at runtime — NemoClaw writes to Target_Specs.json, sidecar reloads on next cycle.

## Scaling Considerations

| Scale | Architecture Adjustment |
|-------|------------------------|
| Single user, single VPS (target) | Monolith sidecar with APScheduler is correct. Qdrant local is correct. No queue needed. |
| Multiple users (future) | Add per-user brain/ directories. Route OpenClaw skill calls with userId. Qdrant moves to collection-per-user. |
| High job volume (100+ jobs/cycle) | Replace asyncio.gather(tasks[:5]) with asyncio.Queue-based worker pool. Add scraping rate limiting per domain. |
| Multiple platforms simultaneously | Playwright concurrency limited by RAM (each browser context ~100-200MB). On a 2GB VPS: max 8-10 concurrent contexts. Stagger platform scraping sequentially within a cycle. |

## Sources

- OpenClaw Tools Invoke HTTP API: https://docs.openclaw.ai/gateway/tools-invoke-http-api
- OpenClaw Skills documentation: https://docs.openclaw.ai/tools/skills
- APScheduler AsyncIOScheduler docs: https://apscheduler.readthedocs.io/en/3.x/modules/schedulers/asyncio.html
- APScheduler asyncio best practices: https://betterstack.com/community/guides/scaling-python/apscheduler-scheduled-tasks/
- Anthropic building effective agents: https://www.anthropic.com/research/building-effective-agents
- Playwright stealth anti-detection patterns: https://www.zenrows.com/blog/playwright-stealth
- Playwright stealth at scale (browserless): https://www.browserless.io/blog/stealth-scraping-puppeteer-playwright
- Multi-platform job board scraping guide 2025: https://www.jobboardly.com/blog/job-board-scraping-complete-guide-2025
- Proxy strategy for anti-bot 2025: https://scrapingant.com/blog/proxy-strategy-in-2025-beating-anti-bot-systems-without
- OpenClaw webhooks and skills integration: https://lumadock.com/tutorials/openclaw-custom-api-integration-guide
- Function calling with LLMs (Martin Fowler): https://martinfowler.com/articles/function-call-LLM.html
- python-telegram-bot JobQueue (APScheduler wrapper): https://docs.python-telegram-bot.org/en/stable/telegram.ext.jobqueue.html

---
*Architecture research for: NemoClaw autonomous job-hunting agent*
*Researched: 2026-03-23*
