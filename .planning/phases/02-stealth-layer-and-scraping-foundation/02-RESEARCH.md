# Phase 2: Stealth Layer and Scraping Foundation - Research

**Researched:** 2026-03-23
**Domain:** Python async web scraping — patchright CDP stealth, France Travail OAuth2 REST API, Telegram alerting, rate limiting
**Confidence:** MEDIUM (patchright API: HIGH; France Travail endpoint structure: MEDIUM; LinkedIn detection resilience: LOW — see blocker note)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use the official France Travail REST API (OAuth2 client credentials flow) — no browser scraping needed
- Auth: client credentials grant, `FRANCE_TRAVAIL_CLIENT_ID` + `FRANCE_TRAVAIL_CLIENT_SECRET` env vars
- Fetch 50 listings per cycle, filtered by keyword + location read from `Target_Specs.json`
- No hardcoded category codes — dynamic filters driven by brain data
- Replace playwright-stealth with patchright (already added to requirements in Phase 1)
- Public search only (no login session) — simpler, no credential storage risk
- Cap at 10–15 jobs per LinkedIn session to minimize detection fingerprint
- On block (429 / CAPTCHA / 0 results): log, send Telegram alert, return empty list — do NOT crash the cycle
- Random 2–5s delay between page requests (matches existing `_human_scroll` pattern in scraper.py)
- Daily caps: 50 France Travail API calls + 15 LinkedIn page loads — configurable via new `rate_limits` key in `Target_Specs.json`
- On transient error (timeout, 5xx): 1 retry after 10s, then skip the job — no infinite retry loops
- Rate limit config lives in `Target_Specs.json` so the user can tune without touching code
- Alert trigger: any scraper that returns 0 jobs (not every exception — avoid noise)
- Channel: Telegram via python-telegram-bot, using `TELEGRAM_BOT_TOKEN` + `NEMO_AUTH_USER_ID` env vars
- Alert format: brief — platform name + error type + ISO timestamp
- Cycle continues after partial failure: France Travail and LinkedIn run independently

### Claude's Discretion
- Exact patchright API calls (launch args, context options) — follow patchright docs/defaults
- France Travail API endpoint paths and OAuth token refresh logic — follow official API docs
- Internal scraper class structure (extend Scraper or new classes) — prefer extending existing Scraper class
- Error classification (what counts as "blocked" vs "transient timeout")

### Deferred Ideas (OUT OF SCOPE)
- Indeed scraper (selectors already in selectors.yaml) — deferred to Phase 6 multi-platform expansion
- Proxy rotation for LinkedIn — deferred, public search is the Phase 2 baseline
- LinkedIn login session for more results — deferred, requires credential management out of scope for Phase 2
- Cadremploi, WTTJ scrapers — Phase 6
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-05 | playwright-stealth is replaced with patchright for CDP-level bot detection bypass | Patchright 1.58.2 is a verified drop-in replacement — import path change only, same async API |
| SCRAPE-01 | Agent scrapes tech job listings from France Travail via official OAuth2 REST API (no Playwright) | Token endpoint and search endpoint verified; `httpx.AsyncClient` with OAuth2 client credentials is the right implementation |
| SCRAPE-04 | Agent scrapes tech job listings from LinkedIn Jobs (Playwright + patchright, discovery only) | patchright resolves CDP leaks; public `/jobs/search/` URL structure documented; 10-15 job cap is the safe operating window |
| SCRAPE-05 | Each scraper fails loudly with a Telegram alert rather than silently returning empty results | python-telegram-bot 22.7 async context manager pattern documented; `async with Bot(...) as bot: await bot.send_message(...)` |
| SCRAPE-06 | Browser context is reused across URLs within a platform batch | Single `browser.new_context()` + `context.new_page()` per URL pattern — no open/close per page |
| SCRAPE-07 | Per-platform rate limits and human-paced delays are enforced | `asyncio.sleep(random.uniform(min, max))` pattern + daily counter loaded from `Target_Specs.json["rate_limits"]` |
</phase_requirements>

---

## Summary

Phase 2 builds the raw data acquisition layer: two independent scraper paths (France Travail via REST API, LinkedIn via browser) converging on a unified `JobListing` Pydantic model, with rate limiting and Telegram alerting wrapping both. No scoring happens in this phase — pure retrieval.

The biggest risk is LinkedIn detection. Patchright fixes the four main CDP leaks that playwright-stealth patched at application level, but headless mode is still detectable by behavioral heuristics. The existing blocker from STATE.md stands: patchright effectiveness against LinkedIn's 2026 detection stack is not independently verified. The plan must include a validation task before implementing the full scraping pipeline. The validated approach is to use `channel="chrome"`, `headless=False` in CI/CD (where a display is unavailable, use `headless=True` with the understanding that CI will be less reliable), and `no_viewport=True`.

France Travail's API is well-documented, free, and straightforward. The OAuth2 client credentials grant is a standard two-step flow: POST to the token endpoint, then GET the search endpoint with `Bearer` token. Rate limit from the wrapper library documentation: 3 requests/second max. The 50-listing-per-cycle requirement is well within bounds.

**Primary recommendation:** Implement France Travail first (no detection risk, deterministic), add patchright LinkedIn second after a local validation spike confirms the `channel="chrome"` approach passes LinkedIn's public search page without a block.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| patchright | 1.58.2 | CDP-patched Chromium browser for LinkedIn scraping | Drop-in playwright replacement; fixes Runtime.enable, Console.enable, and automation flag leaks at source level |
| httpx | 0.28.0 (pinned in requirements.txt) | Async HTTP client for France Travail API | Already in project; async-native; supports OAuth2 token flow |
| python-telegram-bot | 22.7 | Send Telegram alert messages | Already scoped in project; async context-manager API; depends on httpx |
| pydantic | 2.12.5 (pinned) | `JobListing` unified model | Already used throughout project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio (stdlib) | N/A | `asyncio.sleep()` for rate limiting delays | Random delay between page requests |
| yaml (pyyaml 6.0.3) | 6.0.3 | Load selectors config | Already used in scraper.py |
| logging (stdlib) | N/A | Error/info logging | Follow `logger = logging.getLogger(__name__)` pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncio.sleep for rate limiting | aiolimiter or pyrate-limiter | External libs are overkill; random sleep is sufficient and already pattern-matched in `_human_scroll()` |
| httpx for France Travail | aiohttp | httpx already pinned in requirements; aiohttp would be a second HTTP client |
| python-telegram-bot | requests + Telegram Bot API directly | PTB handles retries and async correctly; direct requests is error-prone |

**Installation:**
```bash
# patchright replaces playwright-stealth; playwright stays as base
pip install patchright==1.58.2 python-telegram-bot==22.7
# Remove playwright-stealth from requirements.txt
# Install Chromium driver for patchright
patchright install chromium
```

**Version verification (run before writing):**
```bash
pip index versions patchright          # latest: 1.58.2 (confirmed Mar 2026)
pip index versions python-telegram-bot # latest: 22.7 (confirmed)
```

---

## Architecture Patterns

### Recommended Project Structure
```
career_agent/
├── src/
│   ├── scraper.py          # Extended Scraper class (patchright + LinkedIn + France Travail)
│   ├── alerter.py          # NEW: AlertService (Telegram one-shot send)
│   ├── app.py              # run_cycle() updated to call both scrapers
│   ├── models.py           # NEW: JobListing Pydantic model (unified schema)
│   └── client_factory.py   # Existing singleton — follow this pattern for FT client
├── config/
│   └── selectors.yaml      # Add linkedin_public selectors, no france_travail key needed
└── tests/
    ├── test_scraper_ft.py  # France Travail API tests (respx mock)
    ├── test_scraper_li.py  # LinkedIn tests (playwright route mock)
    └── test_alerter.py     # AlertService tests (mock Bot)
```

### Pattern 1: patchright Drop-In Replacement

**What:** Replace `from playwright.async_api import async_playwright` with `from patchright.async_api import async_playwright`. No other code changes needed — the API is identical.

**When to use:** All existing and new browser automation code in scraper.py.

**Example:**
```python
# Source: pypi.org/project/patchright + github.com/Kaliiiiiiiiii-Vinyzu/patchright-python
from patchright.async_api import async_playwright  # was: from playwright.async_api import async_playwright

async def search_linkedin_jobs(self, query: str, location: str = "France"):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",   # use real Chrome, not Chromium build
            headless=True,      # headless=False is ideal but not feasible in Docker
            # DO NOT set custom user_agent — patchright handles this
            # DO NOT set no_viewport=True in Docker (no display)
        )
        context = await browser.new_context()  # one context for the batch
        # ... scrape all URLs using this context, then close
        await browser.close()
```

**Critical note on conftest.py:** The existing `career_agent/conftest.py` patches `playwright_stealth.stealth_async`. After replacing playwright-stealth with patchright, this patch must be removed or updated. The `stealth_async(page)` call in scraper.py must also be removed — patchright applies stealth at the driver level, not per-page.

### Pattern 2: Browser Context Reuse (SCRAPE-06)

**What:** Create one `BrowserContext` for the entire platform batch. Create a new `Page` per URL, navigate, extract, close that page. Reuse the same context until the batch is done.

**When to use:** Any time multiple URLs are scraped in sequence (LinkedIn job list + individual job detail pages).

**Example:**
```python
# Source: playwright.dev/python/docs/browser-contexts + playwright.dev/python/docs/pages
async with async_playwright() as p:
    browser = await p.chromium.launch(channel="chrome", headless=True)
    context = await browser.new_context()  # ONE context for the whole batch

    scraped = []
    for url in urls_to_scrape:
        page = await context.new_page()    # new page per URL
        try:
            await page.goto(url, wait_until="networkidle")
            await self._human_delay()      # random 2-5s between pages
            # extract data...
            scraped.append(data)
        finally:
            await page.close()             # close page, NOT context

    await browser.close()                  # close context + browser at end of batch
```

### Pattern 3: France Travail OAuth2 Client Credentials Flow

**What:** Standard two-step: POST for token, then GET jobs with Bearer token. Use httpx.AsyncClient (already in project).

**When to use:** Every scrape cycle. Tokens expire — implement refresh logic.

**Example:**
```python
# Source: userguide.huwise.com/en/articles/2045314 + verified against api.gouv.fr
import httpx
import os
from datetime import datetime, timedelta

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"

async def _get_token(self) -> str:
    """Client credentials grant — returns Bearer token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": os.getenv("FRANCE_TRAVAIL_CLIENT_ID"),
                "client_secret": os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET"),
                "scope": "api_offresdemploiv2 o2dsoffre",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

async def search_jobs(self, keywords: str, location: str, count: int = 50) -> list:
    """Search France Travail for job listings."""
    token = await self._get_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            SEARCH_URL,
            params={
                "motsCles": keywords,
                "commune": location,       # INSEE commune code or city name
                "range": f"0-{count - 1}", # 0-indexed, max 149 per call
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )
        if resp.status_code == 200:
            return resp.json().get("resultats", [])
        return []
```

**France Travail response fields (key fields per `resultats` item):**
- `id` — unique offer identifier
- `intitule` — job title
- `entreprise.nom` — company name
- `lieuTravail.libelle` — location label
- `description` — full job description text
- `dateCreation` — ISO date posted
- `typeContrat` — contract type (CDI, CDD, etc.)
- `urlPostuler` — application URL (may be None)
- `salaire.libelle` — salary label (may be None)

### Pattern 4: Telegram One-Shot Alert

**What:** Send a single Telegram message from within an async function, without a running Application/polling loop.

**When to use:** Scraper failure detection — 0 results returned from a platform.

**Example:**
```python
# Source: docs.python-telegram-bot.org/en/stable/telegram.bot.html
import os
from telegram import Bot

async def send_alert(self, platform: str, error_type: str) -> None:
    """Send a Telegram alert for scraper failure."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("NEMO_AUTH_USER_ID")
    if not token or not chat_id:
        logger.error("Telegram credentials missing — cannot send alert")
        return

    text = (
        f"{platform} scraper: 0 results — {error_type} — "
        f"{datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}"
    )
    try:
        async with Bot(token=token) as bot:
            await bot.send_message(chat_id=int(chat_id), text=text)
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")
        # Do NOT re-raise — alerting failure must not crash the cycle
```

### Pattern 5: Rate Limiting with asyncio.sleep

**What:** Random delay between requests loaded from `Target_Specs.json["rate_limits"]`.

**When to use:** Between every page navigation and between API calls to France Travail.

**Example:**
```python
# Extend existing _human_scroll pattern from scraper.py
import asyncio, random, json, os

def _load_rate_limits(self, brain_path: str) -> dict:
    """Load rate limit config from Target_Specs.json."""
    specs_path = os.path.join(brain_path, "Target_Specs.json")
    with open(specs_path) as f:
        specs = json.load(f)
    return specs.get("rate_limits", {
        "france_travail_daily": 50,
        "linkedin_daily": 15,
        "min_delay_s": 2,
        "max_delay_s": 5,
    })

async def _human_delay(self) -> None:
    """Random human-paced delay between requests."""
    delay = random.uniform(
        self._rate_limits.get("min_delay_s", 2),
        self._rate_limits.get("max_delay_s", 5),
    )
    await asyncio.sleep(delay)
```

**Target_Specs.json addition:**
```json
{
  "rate_limits": {
    "france_travail_daily": 50,
    "linkedin_daily": 15,
    "min_delay_s": 2,
    "max_delay_s": 5
  }
}
```

### Pattern 6: Unified JobListing Pydantic Model

**What:** A single Pydantic model that both scrapers return, abstracting France Travail and LinkedIn differences.

**When to use:** All scraper return types — scoring pipeline (Phase 3) will consume this.

**Example:**
```python
# Source: project pattern — pydantic v2 (already pinned at 2.12.5)
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class JobListing(BaseModel):
    id: str                          # platform-specific ID or URL hash
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    date_posted: Optional[str] = None
    contract_type: Optional[str] = None
    source: str                      # "france_travail" or "linkedin"
    raw: Optional[dict] = None       # original response for debugging
```

### Pattern 7: Scraper Class Extension Strategy

**What:** Add `search_france_travail_jobs()` and `_get_france_travail_token()` methods to the existing `Scraper` class. Replace `from playwright.async_api` with `from patchright.async_api`. Remove `stealth_async` call.

**Key changes to existing `Scraper` class:**
1. Remove playwright-stealth import and `await stealth_async(page)` call
2. Change `from playwright.async_api import async_playwright` to patchright equivalent
3. Add `channel="chrome"` to `p.chromium.launch()`
4. Add `brain_path` constructor parameter for rate limits and Target_Specs loading
5. Add `search_france_travail_jobs()` async method
6. Refactor `search_linkedin_jobs()` to reuse context (SCRAPE-06)
7. Add `_human_delay()` using loaded rate limits
8. Return `list[JobListing]` from both scrapers

### Anti-Patterns to Avoid

- **One browser per URL:** Opening a new `async_playwright()` context per job URL is what the current scraper.py does — this creates detectable patterns and is slow. Use one context per batch.
- **Custom user_agent with patchright:** Do NOT set `user_agent` in launch or context args. Patchright sets this correctly at driver level. Adding a custom one breaks the stealth profile.
- **playwright-stealth alongside patchright:** Do not run both. patchright patches at driver level; playwright-stealth patches at JS injection level. Together they create conflicts and detectable anomalies.
- **Raising on 0 results:** The cycle must not crash when a scraper returns empty. Catch, alert, return `[]`.
- **Hardcoded INSEE commune codes:** Use the `location_preference` string from `Target_Specs.json` — map to a parameter France Travail accepts (free-text `commune` works for city names in most cases).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CDP leak bypass | Custom JS injection patches | patchright | patchright patches at binary/driver level — JS injection is detectable and maintains arms-race |
| OAuth2 token lifecycle | Manual JWT parsing + refresh timers | httpx + standard POST grant flow | Token is a simple Bearer string; just re-request per cycle rather than caching across restarts |
| Telegram message sending | Direct `requests.post()` to Telegram Bot API | python-telegram-bot Bot class | PTB handles connection pooling, retries, and async correctly; raw HTTP is fragile |
| Rate limit enforcement | Custom token bucket class | `asyncio.sleep(random.uniform(...))` | For this use case (max 50 calls/day), random sleep is sufficient and already matches existing pattern |
| Response parsing for both sources | Platform-specific dicts | `JobListing` Pydantic model | Pydantic validates and normalizes at parse time; scoring pipeline (Phase 3) needs a stable schema |

**Key insight:** The scraping domain looks simple but every "custom solution" (hand-rolled stealth, hand-rolled rate limiters) underperforms maintained libraries that have been tested against live detection systems at scale.

---

## Common Pitfalls

### Pitfall 1: patchright + headless = still detectable in some scenarios

**What goes wrong:** LinkedIn uses behavioral analysis beyond CDP leaks. Even with patchright, headless Chrome is fingerprinted by absence of GPU processes, specific screen metrics, and sec-ch-ua headers.

**Why it happens:** Patchright fixes Runtime.enable and Console.enable leaks, which drops headless detection from ~100% to ~67% on CreepJS tests — not zero. Docker containers running headless Chrome are more detectable than desktop browsers.

**How to avoid:** Cap session size to 10–15 jobs (already decided), add random delays between page loads, do NOT add suspicious headers, use `channel="chrome"` over default Chromium. Accept that some sessions will be blocked and the alert system handles it gracefully.

**Warning signs:** LinkedIn returns a redirect to `/authwall`, `/checkpoint/challenge`, or returns 0 `.base-card` elements on a search that should have results.

### Pitfall 2: Removing playwright-stealth breaks conftest.py patches

**What goes wrong:** `career_agent/conftest.py` explicitly patches `playwright_stealth.stealth_async`. If playwright-stealth is removed from requirements.txt but the conftest.py import remains, tests fail with `ModuleNotFoundError`.

**Why it happens:** Phase 1 added a compatibility shim for playwright-stealth v2. Phase 2 removes the library entirely.

**How to avoid:** When removing playwright-stealth from requirements.txt, simultaneously update `career_agent/conftest.py` to remove the playwright_stealth patch block. The `scraper.py` stealth import and `await stealth_async(page)` call must also be removed.

### Pitfall 3: France Travail token scope mismatch

**What goes wrong:** API returns 401 even with valid client credentials.

**Why it happens:** The `scope` parameter in the client credentials grant must exactly match what the application is authorized for in the France Travail developer portal. The scope `api_offresdemploiv2 o2dsoffre` is a space-separated string.

**How to avoid:** During the validation spike, test the token request manually with `curl` before writing production code. Log the HTTP status and response body on auth failure.

**Warning signs:** HTTP 401 with `{"error": "unauthorized_client"}` or `{"error": "invalid_scope"}` body.

### Pitfall 4: France Travail `commune` parameter is INSEE code, not free text

**What goes wrong:** Passing "Paris" returns no results or wrong results. The API expects an INSEE commune code (e.g., `75056` for Paris) for the `commune` parameter.

**Why it happens:** The France Travail API uses French administrative codes (INSEE), not free-text city names. The `Target_Specs.json` `location_preference` field is a human-readable string.

**How to avoid:** Either add a `france_travail_commune_code` field to `Target_Specs.json`, or use the `motsCles` parameter for a combined keyword+location search (less precise but avoids INSEE lookup). The `commune` parameter is optional — omitting it returns national results.

**Warning signs:** Empty `resultats` array when you expect results, or results from wrong regions.

### Pitfall 5: LinkedIn selector drift

**What goes wrong:** `job_card: ".base-card"` in selectors.yaml stops matching — LinkedIn updated their class names.

**Why it happens:** LinkedIn changes CSS class names frequently. The current selectors are from Phase 1 and may be stale.

**How to avoid:** The validation spike for LinkedIn (before implementation) must verify selectors against current live HTML. Keep selectors externalized in selectors.yaml so they can be updated without code changes.

**Warning signs:** `len(job_cards) == 0` from `page.query_selector_all()` on a page that renders normally in a browser.

### Pitfall 6: python-telegram-bot httpx version conflict

**What goes wrong:** pip install fails or runtime error due to conflicting httpx versions.

**Why it happens:** `python-telegram-bot==22.7` requires `httpx>=0.27,<0.29`. The project has `httpx==0.28.0` pinned — this is compatible, but must not be bumped to 0.29+.

**How to avoid:** Pin `python-telegram-bot==22.7` exactly in requirements.txt, not `>=22.7`. Verify `pip check` passes after adding it.

**Warning signs:** `pip install` error about httpx version conflict.

### Pitfall 7: `NEMO_AUTH_USER_ID` vs `TELEGRAM_CHAT_ID` env var name

**What goes wrong:** `bot.send_message(chat_id=...)` fails because the wrong env var name is used.

**Why it happens:** STATE.md documents that `TELEGRAM_CHAT_ID` is set from `NEMO_AUTH_USER_ID` (same Telegram user ID). The env var in docker-compose.yml is `NEMO_AUTH_USER_ID`, not `TELEGRAM_CHAT_ID`.

**How to avoid:** Always read `NEMO_AUTH_USER_ID` for the `chat_id` parameter. Never introduce a separate `TELEGRAM_CHAT_ID` variable.

---

## Code Examples

### Complete patchright Migration Delta

```python
# Source: pypi.org/project/patchright + github.com/Kaliiiiiiiiii-Vinyzu/patchright-python

# BEFORE (scraper.py lines 1-12):
from playwright.async_api import async_playwright
try:
    from playwright_stealth import stealth_async
except ImportError:
    from playwright_stealth import stealth as stealth_async

# AFTER:
from patchright.async_api import async_playwright
# No stealth import needed — patchright applies stealth at driver level

# BEFORE (inside search_linkedin_jobs):
browser = await p.chromium.launch(headless=self.headless)
context = await browser.new_context(user_agent="Mozilla/5.0 ...")
page = await context.new_page()
await stealth_async(page)  # REMOVE THIS

# AFTER:
browser = await p.chromium.launch(
    channel="chrome",
    headless=self.headless,
    # DO NOT set user_agent — patchright sets it correctly
)
context = await browser.new_context()
page = await context.new_page()
# No stealth call needed
```

### France Travail Full Client Pattern

```python
# Source: userguide.huwise.com/en/articles/2045314 + github.com/etiennekintzler/api-offres-emploi

TOKEN_URL = (
    "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"
)
SEARCH_URL = (
    "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
)

async def search_france_travail_jobs(
    self, keywords: str, count: int = 50
) -> list[JobListing]:
    try:
        token = await self._get_france_travail_token()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                SEARCH_URL,
                params={
                    "motsCles": keywords,
                    "range": f"0-{min(count, 149) - 1}",
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            resultats = data.get("resultats", [])

            jobs = [self._parse_ft_listing(r) for r in resultats]

            if not jobs:
                await self.alerter.send_alert("France Travail", "0 results")
            return jobs
    except Exception as e:
        logger.error(f"France Travail scrape failed: {e}")
        await self.alerter.send_alert("France Travail", str(type(e).__name__))
        return []

def _parse_ft_listing(self, raw: dict) -> JobListing:
    return JobListing(
        id=raw.get("id", ""),
        title=raw.get("intitule", ""),
        company=raw.get("entreprise", {}).get("nom"),
        location=raw.get("lieuTravail", {}).get("libelle"),
        description=raw.get("description"),
        url=raw.get("urlPostuler") or raw.get("origineOffre", {}).get("urlOrigine"),
        date_posted=raw.get("dateCreation"),
        contract_type=raw.get("typeContrat"),
        source="france_travail",
        raw=raw,
    )
```

### run_cycle Integration

```python
# Source: career_agent/src/app.py — update run_cycle to call both scrapers
async def run_cycle(self, keyword: str, location: str = "France"):
    logger.info(f"--- Starting Phoenix Cycle for: {keyword} in {location} ---")

    # Run both scrapers independently — one failure does not kill the other
    ft_jobs, li_jobs = await asyncio.gather(
        self.scraper.search_france_travail_jobs(keyword, count=50),
        self.scraper.search_linkedin_jobs(keyword, location),
        return_exceptions=True,  # prevents one failure propagating
    )

    # Flatten and process
    all_jobs = []
    if isinstance(ft_jobs, list):
        all_jobs.extend(ft_jobs)
    if isinstance(li_jobs, list):
        all_jobs.extend(li_jobs)

    tasks = [self.process_job(job) for job in all_jobs[:5]]
    await asyncio.gather(*tasks)
    logger.info("--- Cycle complete ---")
```

### docker-compose.yml env additions

```yaml
# Add to career-agent service environment:
- FRANCE_TRAVAIL_CLIENT_ID=${FRANCE_TRAVAIL_CLIENT_ID}
- FRANCE_TRAVAIL_CLIENT_SECRET=${FRANCE_TRAVAIL_CLIENT_SECRET}
- NEMO_AUTH_USER_ID=${NEMO_AUTH_USER_ID}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| playwright-stealth JS injection | patchright binary-level CDP patches | 2024-2025 | More reliable; no per-page call needed; Runtime.enable fully removed |
| `stealth_async(page)` per page | No call needed (patchright default) | With patchright adoption | Remove call from code; simplifies scraper methods |
| `playwright.async_api` import | `patchright.async_api` import | With patchright migration | Single line change; identical API |
| `p.chromium.launch()` (bare) | `p.chromium.launch(channel="chrome")` | Patchright recommendation | Uses real Chrome binary for better fingerprint realism |
| One browser per method call | One context reused across batch | This phase | Reduces fingerprinting surface; more efficient |

**Deprecated/outdated:**
- `playwright-stealth==2.0.2`: Remove from requirements.txt entirely. The Phase 1 compatibility shim in conftest.py and the try/except import in scraper.py are both obsolete after this migration.
- `from playwright.async_api import async_playwright` in scraper.py: Replace with patchright import.

---

## Open Questions

1. **LinkedIn's 2026 detection resilience with patchright + headless**
   - What we know: patchright reduces headless detection from ~100% to ~67% on CreepJS. STATE.md explicitly flags this as unverified.
   - What's unclear: Whether Docker headless + `channel="chrome"` passes LinkedIn's `/jobs/search/` public page without an authwall redirect.
   - Recommendation: First task of Phase 2 plan must be a validation spike — manually run patchright against LinkedIn `/jobs/search/?keywords=developer&location=France` and observe whether it redirects, returns results, or blocks. If blocked consistently, fallback is to return `[]` + alert and defer LinkedIn to a later phase.

2. **France Travail `commune` parameter — INSEE codes vs free text**
   - What we know: The `commune` parameter officially expects INSEE codes. Some community code examples pass city names and get results.
   - What's unclear: Whether free-text city names work reliably in production, or whether the project needs an INSEE lookup table.
   - Recommendation: Initial implementation should use only `motsCles` (keywords from Target_Specs) and omit `commune` (returns national results). This is safer and avoids a blocking dependency on INSEE code mapping.

3. **France Travail token expiry interval**
   - What we know: Client credentials tokens expire. The Python wrapper documentation does not specify the expiry duration.
   - What's unclear: Whether the token lasts long enough for a 50-job fetch (probably yes), or needs refresh mid-cycle.
   - Recommendation: Request a fresh token at the start of every `search_france_travail_jobs()` call. Since this runs once per cycle (daily), the overhead is negligible.

4. **patchright Dockerfile compatibility**
   - What we know: patchright requires `patchright install chromium` after pip install, similar to `playwright install chromium`.
   - What's unclear: Whether the existing `career_agent/Dockerfile` already runs `playwright install chromium` (not inspected).
   - Recommendation: Verify the Dockerfile during Wave 0 — add `RUN patchright install chromium` after removing the playwright equivalent if present.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x |
| Config file | `career_agent/conftest.py` (root) + `career_agent/tests/conftest.py` |
| Quick run command | `cd career_agent && python -m pytest tests/test_scraper_ft.py tests/test_alerter.py -x -q` |
| Full suite command | `cd career_agent && python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-05 | `from patchright.async_api import async_playwright` imports without error; no playwright-stealth import | unit | `pytest tests/test_scraper_li.py::test_patchright_import -x` | ❌ Wave 0 |
| INFRA-05 | stealth_async call is absent from Scraper class | unit (AST check or import test) | `pytest tests/test_scraper_li.py::test_no_stealth_call -x` | ❌ Wave 0 |
| SCRAPE-01 | France Travail token request POSTs correct grant_type, client_id, scope | unit (respx mock) | `pytest tests/test_scraper_ft.py::test_token_request -x` | ❌ Wave 0 |
| SCRAPE-01 | France Travail search returns list of JobListing when API responds 200 | unit (respx mock) | `pytest tests/test_scraper_ft.py::test_search_returns_listings -x` | ❌ Wave 0 |
| SCRAPE-01 | France Travail search returns [] and triggers alert on 401 | unit (respx mock) | `pytest tests/test_scraper_ft.py::test_search_401_returns_empty -x` | ❌ Wave 0 |
| SCRAPE-04 | LinkedIn search uses patchright context; returns list of JobListing | unit (page.route mock) | `pytest tests/test_scraper_li.py::test_linkedin_returns_listings -x` | ❌ Wave 0 |
| SCRAPE-05 | AlertService.send_alert calls Bot.send_message with platform name and timestamp | unit (mock Bot) | `pytest tests/test_alerter.py::test_alert_message_format -x` | ❌ Wave 0 |
| SCRAPE-05 | AlertService.send_alert does not raise if Bot.send_message throws | unit (mock Bot raising) | `pytest tests/test_alerter.py::test_alert_swallows_exception -x` | ❌ Wave 0 |
| SCRAPE-06 | One browser context is created per batch; page closed per URL; browser closed at end | unit (patchright mock) | `pytest tests/test_scraper_li.py::test_context_reuse -x` | ❌ Wave 0 |
| SCRAPE-07 | `_human_delay()` calls asyncio.sleep with value in [min_delay_s, max_delay_s] range | unit (mock asyncio.sleep) | `pytest tests/test_scraper_ft.py::test_human_delay_range -x` | ❌ Wave 0 |
| SCRAPE-07 | Rate limits loaded from Target_Specs.json rate_limits key | unit | `pytest tests/test_scraper_ft.py::test_rate_limits_from_specs -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd career_agent && python -m pytest tests/test_scraper_ft.py tests/test_alerter.py -x -q`
- **Per wave merge:** `cd career_agent && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `career_agent/tests/test_scraper_ft.py` — covers SCRAPE-01, SCRAPE-07 (France Travail unit tests with respx mock)
- [ ] `career_agent/tests/test_scraper_li.py` — covers INFRA-05, SCRAPE-04, SCRAPE-06 (LinkedIn unit tests with playwright route mock)
- [ ] `career_agent/tests/test_alerter.py` — covers SCRAPE-05 (AlertService unit tests with mock Bot)
- [ ] `career_agent/src/models.py` — JobListing Pydantic model (needed by all scraper tests)
- [ ] `career_agent/src/alerter.py` — AlertService class (needed by test_alerter.py)
- [ ] `career_agent/conftest.py` update — remove playwright_stealth shim after INFRA-05 implementation
- [ ] `career_agent/requirements.txt` additions: `patchright==1.58.2`, `python-telegram-bot==22.7`, remove `playwright-stealth==2.0.2`
- [ ] `respx` added to requirements.txt for France Travail API mocking: `respx>=0.22.0`

---

## Sources

### Primary (HIGH confidence)
- [pypi.org/project/patchright](https://pypi.org/project/patchright/) — version 1.58.2, async import syntax, install command, Python >=3.9
- [github.com/Kaliiiiiiiiii-Vinyzu/patchright-python](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python) — drop-in replacement confirmation, recommended launch args, CDP leak fixes
- [deepwiki.com/Kaliiiiiiiiii-Vinyzu/patchright-python/4-user-guide](https://deepwiki.com/Kaliiiiiiiiii-Vinyzu/patchright-python/4-user-guide) — import changes, headless recommendation, console disabled note
- [docs.python-telegram-bot.org/en/stable/telegram.bot.html](https://docs.python-telegram-bot.org/en/stable/telegram.bot.html) — `async with Bot(...) as bot` pattern, `send_message` signature, initialize/shutdown lifecycle
- [pypi.org/project/python-telegram-bot](https://pypi.org/project/python-telegram-bot/) — version 22.7, httpx dependency constraint `>=0.27,<0.29`
- [playwright.dev/python/docs/browser-contexts](https://playwright.dev/python/docs/browser-contexts) — context isolation model, new_page() lifecycle

### Secondary (MEDIUM confidence)
- [userguide.huwise.com/en/articles/2045314](https://userguide.huwise.com/en/articles/2045314) — France Travail token URL `https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire` (verified against multiple secondary sources)
- [github.com/etiennekintzler/api-offres-emploi](https://github.com/etiennekintzler/api-offres-emploi) — France Travail API wrapper: `range` parameter format, 3 req/sec limit, response schema structure (filtresPossibles + resultats)
- [all-api.fr/api/detail/france-travail](https://all-api.fr/api/detail/france-travail) — search endpoint `https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search`, params: motsCles, commune, rayon
- [datawookie.dev/blog/2025/04/test-a-playwright-web-scraper/](https://datawookie.dev/blog/2025/04/test-a-playwright-web-scraper/) — `page.route("**/*", handler)` pattern for test mocking

### Tertiary (LOW confidence — flag for validation spike)
- LinkedIn detection behavior with patchright in Docker headless — inferred from CreepJS 67% statistic and multiple blog posts; no direct test on LinkedIn /jobs/search/ endpoint verified
- France Travail response field names (intitule, entreprise.nom, lieuTravail.libelle, etc.) — sourced from community wrapper code and partial documentation; MUST verify against live API response during spike

---

## Metadata

**Confidence breakdown:**
- Standard stack (patchright, httpx, PTB): HIGH — verified against PyPI and official docs with exact versions
- Architecture (patchright migration pattern): HIGH — identical API confirmed, launch arg recommendation verified
- France Travail API endpoints and auth: MEDIUM — token URL and search URL verified from multiple sources; response schema field names are MEDIUM (community sources, not official Swagger)
- LinkedIn detection resilience: LOW — no direct verification; the STATE.md blocker is accurate; a validation spike is mandatory
- Rate limiting pattern: HIGH — asyncio.sleep is stdlib, pattern already established in project
- Telegram alerting: HIGH — official docs confirm `async with Bot(...) as bot` pattern for one-shot sends

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (France Travail API is stable; patchright is fast-moving — check version within 30 days)

---

## RESEARCH COMPLETE
