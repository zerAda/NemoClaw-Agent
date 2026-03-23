# Stack Research

**Domain:** Autonomous job-hunting agent — French + global job markets
**Researched:** 2026-03-23
**Confidence:** MEDIUM-HIGH (see per-area breakdown)

---

## Executive Context

This is a brownfield extension. The existing `career_agent/` already ships:
- `Scraper` — Playwright + playwright-stealth, LinkedIn + Indeed selectors
- `HunterService` — Gemini-1.5-flash scoring via OpenAI-compat API
- `TailorService` — Gemini-1.5-pro cover letter generation
- `MemoryService` — local Qdrant (qdrant-client, path-mode), UUIDv5 deduplication
- `PhoenixApp` — asyncio orchestrator, 5-concurrent gather

The NemoClaw container runs `ghcr.io/openclaw/openclaw:latest` with Gemini as inference, python-telegram-bot-style Telegram gateway, deployed behind Traefik.

Stack decisions below prescribe what to **add**, what to **upgrade**, and what to **keep**.

---

## Recommended Stack

### Core Technologies (Keep + Upgrade)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Runtime | Existing codebase; 3.11 gives 10-25% asyncio perf improvement over 3.10; required for patchright |
| Playwright (async) | 1.49+ (via patchright) | Browser automation base | Already in codebase; patchright wraps Playwright so you keep the same API |
| **patchright** | 1.58.2 | Stealth browser automation | Replaces `playwright-stealth`; patches CDP leaks at the binary level; current `playwright-stealth` only defeats simple checks; patchright is undetectable against DataDome, PerimeterX, Cloudflare in headless Chromium — the tier LinkedIn/WTTJ use |
| qdrant-client | 1.17.1 | Vector store + deduplication | Already in codebase; version 1.17.1 (Mar 2026) is current; local path-mode is fine for single-VPS deploy |
| openai (AsyncOpenAI) | 1.x | Gemini via OpenAI-compat layer | Already in codebase via `client_factory.py`; keep as-is |

### New Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **python-telegram-bot** | 22.7 | Telegram bot framework + job scheduling | Latest release (Mar 16 2026); built on asyncio since v20; `JobQueue` (backed by APScheduler AsyncIOScheduler) handles daily digest + follow-up scheduling natively — no second scheduler dependency needed; PTB v22 is the right choice over aiogram because the existing OpenClaw bot likely already uses PTB conventions and PTB's `ConversationHandler` FSM is better documented for command interfaces |
| **aiosqlite** | 0.22.1 | Application status tracking DB | SQLite is sufficient for one user's job pipeline (hundreds of rows max); aiosqlite bridges sqlite3 to asyncio event loop without blocking; no separate Postgres server needed on VPS; file-based → survives container restarts via volume mount |
| **APScheduler** | ~3.10.4 | Follow-up scheduling | Installed automatically with PTB `[job-queue]` extra; `AsyncIOScheduler` for follow-up reminders at configurable delays; already used inside PTB's JobQueue so no version conflict |

### Scraping Layer — Platform Matrix

| Platform | Method | Rationale | Confidence |
|----------|--------|-----------|------------|
| **LinkedIn** | Playwright + patchright + session cookies | No official public API. LinkedIn scraping is legally cleared for public data (HiQ ruling) but ToS-violating. Rate limit ~100-150 Easy Apply/day; must throttle 2-5s between actions. Session cookie reuse across runs is mandatory (no fresh login each cycle). | HIGH |
| **France Travail (ex-Pôle Emploi)** | Official REST API (`francetravail.io`) | France Travail publishes a real, production-grade public API at `francetravail.io/data/api/offres-emploi`. OAuth2 + client credentials. Returns paginated JSON. Free to use. This is the only scraping-free French platform. **Use this first, it covers the largest French public sector + SME listing volume.** | HIGH |
| **APEC** | Playwright + patchright (HTML scraping) | No official public API. APEC.fr is the primary cadre/executive-level board in France (directly relevant to 70K-100K EUR roles). Community scrapers exist (GitHub: atchopba/scraping-jobs) confirming it is scrapable. Algolia-based internal search can be reverse-engineered for faster results. | MEDIUM |
| **Welcome to the Jungle (WTTJ)** | Playwright + patchright OR WTTJ Algolia endpoint | No official public API. WTTJ uses Algolia internally — internal search API calls are observable via DevTools and return structured JSON (salary, remote, tech stack, etc.). Scraping Algolia endpoints is more reliable than HTML parsing. Multiple Apify actors confirm viability. | MEDIUM |
| **Cadremploi** | Playwright + patchright (HTML scraping) | No official API found. Standard JS-rendered site; Playwright handles rendering. Mid-tier French cadre board. Selector-based scraping via externalized `selectors.yaml` (existing pattern). | LOW-MEDIUM |
| **Indeed France** | Playwright + patchright | Official API discontinued. Indeed is currently the most scrapable (no rate limiting per JobSpy docs); French jobs available at `fr.indeed.com` with `&l=France` parameter. | HIGH |
| **Glassdoor** | Playwright + patchright | No public API. ScrapingBee and Oxylabs both confirm it requires headless browser. Low priority for French market (thin French listing volume). | MEDIUM |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pydantic` | 2.x | Data models (MatchReport, TailoredContent, ApplicationRecord) | Already in codebase; extend ApplicationRecord model for tracking |
| `httpx` | 0.27+ | France Travail API calls (async HTTP client) | For OAuth2 token exchange + REST calls to francetravail.io; lighter than Playwright for API-only platforms |
| `python-dateutil` | 2.9+ | Follow-up date arithmetic | Parsing job post dates, calculating follow-up deadlines |
| `pyyaml` | 6.x | Selector config loading | Already in codebase (`selectors.yaml`); extend for French platform selectors |
| `tenacity` | 8.x | Retry logic with exponential backoff | Wrapping all scraper calls and API calls; critical for anti-bot retry resilience |
| `loguru` | 0.7+ | Structured logging | Replace stdlib `logging`; better for async multi-service logs; searchable on VPS |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `bandit` | SAST security scan | Already in CI pipeline; keep |
| `flake8` | Lint | Already in CI pipeline; keep |
| `pytest-asyncio` | Async test runner | Required for testing async scraper and service code |
| `pytest-mock` | Mock Playwright/Gemini in tests | Prevents live browser calls in CI |

---

## Installation

```bash
# Upgrade stealth browser (replaces playwright-stealth)
pip install patchright==1.58.2
patchright install chromium

# New additions
pip install python-telegram-bot[job-queue]==22.7
pip install aiosqlite==0.22.1
pip install httpx==0.27.0
pip install tenacity==8.2.3
pip install python-dateutil==2.9.0
pip install loguru==0.7.2

# Existing — pin current working versions
pip install qdrant-client==1.17.1
pip install pydantic==2.7.0
pip install pyyaml==6.0.1
pip install openai==1.30.0

# Dev
pip install pytest-asyncio pytest-mock
```

---

## What to Keep vs Replace

| Component | Decision | Reason |
|-----------|----------|--------|
| `scraper.py` — Playwright base | KEEP, upgrade stealth layer | Replace `playwright-stealth` import with `patchright`; rest of API is identical (`async_playwright`, `page.goto`, etc.) |
| `scraper.py` — LinkedIn method | KEEP, harden | Add session-cookie persistence; add `tenacity` retry; add patchright |
| `scraper.py` — Indeed method (selector) | KEEP | Add `fr.indeed.com` URL variant |
| `hunter.py` | KEEP | Model upgrade from `gemini-1.5-flash` to `gemini-2.5-flash` only |
| `tailor.py` | KEEP | Model upgrade from `gemini-1.5-pro` to `gemini-2.5-flash` (costs less, performs similarly) |
| `memory.py` — deduplication | KEEP | Already correct UUIDv5 pattern |
| `memory.py` — application status | EXTEND | Add `status` field (`APPLIED / VIEWED / REJECTED / INTERVIEW / OFFER`) and `applied_at` timestamp to Qdrant payload; currently only stores dedup ID |
| `client_factory.py` | KEEP | OpenAI-compat layer for Gemini still valid; update model IDs |
| `selectors.yaml` | EXTEND | Add APEC, WTTJ, Cadremploi selector blocks |
| New: `tracker.py` | ADD | aiosqlite-backed application status store with follow-up scheduling integration |
| New: `reporter.py` | ADD | python-telegram-bot integration; daily digest + real-time alerts |
| New: `scheduler.py` | ADD | PTB JobQueue wrapper for cycle scheduling and follow-up triggers |
| New: `applier.py` | ADD | Auto-apply logic per platform (Easy Apply form fill, redirect to company ATS) |

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| patchright 1.58.2 | playwright-stealth (current) | playwright-stealth patches JS properties only; fails against enterprise anti-bot (DataDome, Cloudflare AI Labyrinth introduced Mar 2025); patchright patches at CDP binary level — currently undetectable in headless Chromium |
| patchright 1.58.2 | undetected-chromedriver (UC) | UC is Selenium-based; existing code is Playwright-based; mixing frameworks adds complexity; patchright keeps the Playwright API |
| patchright 1.58.2 | Camoufox | Camoufox is Firefox-based; performs better against DataDome than patchright in some tests but requires rewriting all browser launch code; overkill for current threat model |
| python-telegram-bot 22.7 | aiogram 3.x | aiogram requires FSM wiring from scratch; PTB JobQueue is built-in scheduling without extra dependencies; OpenClaw container probably uses PTB internals already; PTB v22 is now fully async — performance parity |
| aiosqlite (SQLite) | PostgreSQL | Postgres requires a separate container, docker-compose coordination, backup strategy; one user's job pipeline is hundreds of rows max; SQLite file can be volume-mounted same as qdrant_db |
| aiosqlite (SQLite) | Qdrant as status store | Qdrant is a vector DB optimized for similarity search, not relational status queries; querying `WHERE status='APPLIED' AND applied_at < 7_days_ago` is a SQL problem, not a vector search problem; keep Qdrant for dedup only |
| France Travail official API | Scraping francetravail.fr | Official API is free, returns structured JSON, no Playwright overhead; always prefer official API when one exists |
| JobSpy (python-jobspy) as supplementary | JobSpy as primary scraper | JobSpy 1.1.82 supports LinkedIn/Indeed/Glassdoor but has NO French-specific boards (APEC, WTTJ, Cadremploi); useful as a fallback for global boards, not a replacement for the existing Playwright scraper stack |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `playwright-stealth` (current dep) | Only defeats webdriver flag checks; fails against DataDome, Cloudflare Turnstile, and AI Labyrinth (Mar 2025); LinkedIn uses enterprise-tier detection that `playwright-stealth` cannot bypass reliably in 2026 | `patchright` |
| `gemini-1.5-flash` / `gemini-1.5-pro` model IDs | As of Mar 6 2026, `gemini-2.0-flash-001` is restricted to existing customers only; `gemini-1.5-*` models are deprecated; new projects must use `gemini-2.5-flash` | `gemini-2.5-flash` via same OpenAI-compat URL |
| Selenium / undetected-chromedriver | Existing codebase is Playwright; mixing runtimes doubles browser binary overhead on VPS; Playwright is faster and modern | Stay on Playwright via patchright |
| Apify cloud scrapers | Paid SaaS with per-event billing; introduces external dependency; existing Playwright stack already handles same task; cost grows with scale | Self-hosted Playwright + patchright |
| Proxycurl LinkedIn API | Shut down under legal pressure (confirmed 2025); no longer available | Direct scraping with session cookies + throttling |
| A second task scheduler (e.g., Celery + Redis) | Overkill for a single-user agent; PTB's JobQueue backed by APScheduler handles all scheduling needs without Redis or broker | PTB `[job-queue]` extra |
| `asyncio.gather` with >10 concurrent browser instances | VPS has 2G memory limit (docker-compose); each Playwright Chromium context uses ~200-300MB; launching 10+ simultaneous browsers will OOM; existing cap of 5 is already aggressive | Keep existing `asyncio.gather` cap at 3-5; use sequential scraping per platform |

---

## Stack Patterns by Variant

**For France Travail (official API path):**
- Use `httpx.AsyncClient` with OAuth2 client-credentials flow
- Cache the bearer token (expires in 1500s per France Travail docs)
- No Playwright needed for this platform
- Returns structured JSON natively — no HTML parsing

**For WTTJ (Algolia internal API path):**
- Open DevTools on WTTJ, observe `/1/indexes/wttj_production_jobs/query` calls
- Replicate via `httpx` — significantly faster than Playwright HTML scraping
- Use Playwright as fallback if Algolia endpoint changes
- Algolia app ID is public (embedded in WTTJ JS bundle)

**For LinkedIn (session-cookie path):**
- Store LinkedIn session cookies in a JSON file mounted as a brain volume
- Use `patchright`'s persistent context with `storage_state` to reuse cookies
- Never re-login programmatically — manual cookie refresh every ~30 days
- Rate limit: max 100 Easy Apply per day; implement `asyncio.sleep` with jitter

**For all Playwright-based scrapers:**
- Reuse one `Browser` instance per scraping cycle (not per job)
- Create a fresh `BrowserContext` per platform session
- Pass `storage_state` for platforms with saved cookies

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|----------------|-------|
| patchright 1.58.2 | Python 3.9+ | Chromium-only; does not support Firefox or WebKit |
| patchright 1.58.2 | playwright (not required as separate dep) | patchright ships its own Chromium; do NOT `pip install playwright` alongside patchright — they conflict if both try to manage Chromium |
| python-telegram-bot 22.7 | APScheduler ~3.10.4 | PTB `[job-queue]` pins APScheduler version; do not upgrade APScheduler independently |
| python-telegram-bot 22.7 | Python 3.9+ | Requires asyncio; use Python 3.11 for best performance |
| aiosqlite 0.22.1 | Python 3.9+ | Standard asyncio bridge; no known conflicts |
| qdrant-client 1.17.1 | Python 3.8+ | Local path-mode confirmed working; does not require running Qdrant server |
| openai 1.x | httpx 0.27+ | openai SDK uses httpx internally; pin httpx ≥0.27 to avoid version conflicts |

---

## Model Upgrade Path

The existing `client_factory.py` pattern (AsyncOpenAI pointed at Gemini's OpenAI-compat endpoint) is correct and should be kept. Only the model ID strings need changing:

| Service | Current Model | Recommended Model | Why |
|---------|--------------|-------------------|-----|
| `hunter.py` scoring | `gemini-1.5-flash` | `gemini-2.5-flash` | 1.5-flash deprecated; 2.5-flash has better reasoning at similar speed/cost |
| `tailor.py` cover letters | `gemini-1.5-pro` | `gemini-2.5-flash` | 1.5-pro deprecated; 2.5-flash matches 1.5-pro quality for generation tasks; lower cost |
| NemoClaw container | `gemini-1.5-flash` (in docker-compose.yml) | `gemini-2.5-flash` | Same deprecation reason |

---

## Sources

- patchright PyPI — version 1.58.2 confirmed current (MEDIUM confidence, PyPI)
- patchright GitHub `Kaliiiiiiiiii-Vinyzu/patchright` — CDP leak patching mechanism (MEDIUM confidence, GitHub)
- ZenRows patchright guide — detection capability vs DataDome/Cloudflare (MEDIUM confidence, WebSearch)
- playwright-stealth limitations — confirmed fails vs enterprise anti-bot 2025 (MEDIUM confidence, multiple WebSearch sources)
- France Travail official API — `api.gouv.fr/les-api/api_offresdemplois` + `francetravail.io/data/api/offres-emploi` — REST, OAuth2, free (HIGH confidence, official government source)
- WTTJ no official API — confirmed via Apify actor descriptions and mantiks.io (MEDIUM confidence, WebSearch)
- APEC no official API — confirmed via GitHub scraping projects and Apify actor (MEDIUM confidence, WebSearch)
- LinkedIn no public jobs API + HiQ ruling — confirmed by multiple scraping guides (HIGH confidence, multiple sources)
- Indeed API discontinued — confirmed multiple scraping guides 2025 (HIGH confidence, multiple sources)
- JobSpy `speedyapply/JobSpy` — version 1.1.82, covers LinkedIn/Indeed/Glassdoor/Google, no French-specific boards (MEDIUM confidence, GitHub + PyPI)
- python-telegram-bot v22.7 — confirmed current Mar 16 2026 (HIGH confidence, official docs + PyPI)
- python-telegram-bot JobQueue + APScheduler AsyncIOScheduler — confirmed in official PTB v21.8 and v22.x docs (HIGH confidence, official docs)
- aiosqlite 0.22.1 — confirmed Dec 23 2025 release (HIGH confidence, PyPI)
- qdrant-client 1.17.1 — confirmed Mar 13 2026 release (HIGH confidence, PyPI)
- Gemini 2.0-flash-001 deprecation for new projects (Mar 2026) + 2.5-flash recommended — confirmed Google AI docs (HIGH confidence, official Google docs)
- LinkedIn rate limits ~100-150 Easy Apply/day 2025 — MEDIUM confidence (multiple automation tool docs, not official LinkedIn statement)
- Cloudflare AI Labyrinth (Mar 2025) — confirmed as new defense defeating basic playwright-stealth (MEDIUM confidence, WebSearch multiple sources)

---

*Stack research for: NemoClaw autonomous job-hunting agent — French + global markets*
*Researched: 2026-03-23*
