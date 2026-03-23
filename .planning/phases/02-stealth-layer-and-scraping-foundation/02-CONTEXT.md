# Phase 2: Stealth Layer and Scraping Foundation - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace playwright-stealth with patchright for LinkedIn scraping, integrate France Travail official REST API as the primary French source, enforce per-platform rate limits, and surface scraper failures to the user via Telegram alerts. This phase delivers working scrapers for two sources (France Travail + LinkedIn) with production-grade resilience. No scoring, no applying — raw job retrieval only.

</domain>

<decisions>
## Implementation Decisions

### France Travail Integration
- Use the official France Travail REST API (OAuth2 client credentials flow) — no browser scraping needed
- Auth: client credentials grant, `FRANCE_TRAVAIL_CLIENT_ID` + `FRANCE_TRAVAIL_CLIENT_SECRET` env vars
- Fetch 50 listings per cycle, filtered by keyword + location read from `Target_Specs.json`
- No hardcoded category codes — dynamic filters driven by brain data

### LinkedIn Stealth Strategy
- Replace playwright-stealth with patchright (already added to requirements in Phase 1)
- Public search only (no login session) — simpler, no credential storage risk
- Cap at 10–15 jobs per LinkedIn session to minimize detection fingerprint
- On block (429 / CAPTCHA / 0 results): log, send Telegram alert, return empty list — do NOT crash the cycle

### Rate Limiting
- Random 2–5s delay between page requests (matches existing `_human_scroll` pattern in scraper.py)
- Daily caps: 50 France Travail API calls + 15 LinkedIn page loads — configurable via new `rate_limits` key in `Target_Specs.json`
- On transient error (timeout, 5xx): 1 retry after 10s, then skip the job — no infinite retry loops
- Rate limit config lives in `Target_Specs.json` so the user can tune without touching code

### Failure Alerting
- Alert trigger: any scraper that returns 0 jobs (not every exception — avoid noise)
- Channel: Telegram via python-telegram-bot, using `TELEGRAM_BOT_TOKEN` + `NEMO_AUTH_USER_ID` env vars (already in .env)
- Alert format: brief — platform name + error type + ISO timestamp (e.g. "LinkedIn scraper: 0 results — possible block — 2026-03-23T14:00:00Z")
- Cycle continues after partial failure: France Travail and LinkedIn run independently, one failure doesn't kill the other

### Claude's Discretion
- Exact patchright API calls (launch args, context options) — follow patchright docs/defaults
- France Travail API endpoint paths and OAuth token refresh logic — follow official API docs
- Internal scraper class structure (extend Scraper or new classes) — prefer extending existing Scraper class
- Error classification (what counts as "blocked" vs "transient timeout")

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `career_agent/src/scraper.py` — existing Scraper class with `search_linkedin_jobs()`, `get_linkedin_job_description()`, `_human_scroll()`. Extend this class, don't replace it.
- `career_agent/config/selectors.yaml` — externalized CSS selectors (linkedin + indeed). Add `france_travail` key if any DOM parsing is needed.
- `career_agent/src/client_factory.py` — singleton pattern for shared clients. Follow this pattern for a France Travail API client.
- `career_agent/src/app.py` — `run_cycle()` calls `scraper.search_linkedin_jobs()`. This call site will need updating to also call the France Travail scraper.

### Established Patterns
- Async/await throughout — all new scraper methods must be `async def`
- Random delays already used in `_human_scroll()` — extend this pattern to inter-request delays
- BRAIN_PATH env var for config files — `Target_Specs.json` is at `brain/Target_Specs.json`
- Pydantic models for all structured data — define a `JobListing` Pydantic model for unified output
- Error logging via `logger = logging.getLogger(__name__)` — follow this in all new code

### Integration Points
- `career_agent/src/app.py:run_cycle()` — where scrapers are called; will need France Travail call added
- `brain/Target_Specs.json` — add `rate_limits` key for daily caps
- `career_agent/requirements.txt` — add `python-telegram-bot>=22.7` back (removed in audit but needed for alerts)
- `docker-compose.yml` — add `FRANCE_TRAVAIL_CLIENT_ID`, `FRANCE_TRAVAIL_CLIENT_SECRET`, `NEMO_AUTH_USER_ID` to career-agent env

</code_context>

<specifics>
## Specific Ideas

- France Travail API: use `https://api.emploi-store.fr/partenaire/offresdemploi/v2/offres/search` endpoint (open API, no cost)
- patchright: use `patchright.chromium.launch()` — drop-in replacement for playwright chromium calls
- Telegram alerting: send via Bot API directly (no webhook needed) — simple `bot.send_message(chat_id, text)` call
- The `rate_limits` key in Target_Specs.json should look like: `{"france_travail_daily": 50, "linkedin_daily": 15}`

</specifics>

<deferred>
## Deferred Ideas

- Indeed scraper (selectors already in selectors.yaml) — deferred to Phase 6 multi-platform expansion
- Proxy rotation for LinkedIn — deferred, public search is the Phase 2 baseline
- LinkedIn login session for more results — deferred, requires credential management out of scope for Phase 2
- Cadremploi, WTTJ scrapers — Phase 6

</deferred>
