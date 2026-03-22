# Codebase Concerns

**Analysis Date:** 2026-03-23

## Tech Debt

**Broad Exception Catching in Job Processing:**
- Issue: `process_job()` in `career_agent/src/app.py` (line 62) catches all exceptions with generic `Exception as e`, logging but silently continuing. This masks parsing errors, API failures, and file I/O issues without distinguishing recoverable from critical failures.
- Files: `career_agent/src/app.py` (lines 23-63), `career_agent/src/scraper.py` (lines 23-25)
- Impact: Silent failures in job processing pipeline. No circuit breaker; failed jobs simply disappear from logs with only error trace. Cannot distinguish between LinkedIn anti-bot rejection (rate-limit) vs actual job parsing failure.
- Fix approach: Implement specific exception types (`LinkedInBlockedError`, `InvalidJDError`, `StorageError`) and handle each distinctly. Add retry logic with exponential backoff for transient failures. Log uncaught exceptions and re-raise.

**Untyped Function Parameter:**
- Issue: `process_job(self, job: Dict)` in `career_agent/src/app.py` (line 23) uses bare `Dict` without key specification. The function accesses `job["url"]` (line 26), `job["title"]` (lines 27, 40, 44) without validation, risking `KeyError` at runtime.
- Files: `career_agent/src/app.py` (line 23), dependent on `career_agent/src/scraper.py` (lines 57-61 which builds the dict)
- Impact: If scraper returns malformed job dict, the entire process_job fails silently. No schema validation. Cannot refactor scrapers safely without grepping for dict key access patterns.
- Fix approach: Define `JobListing` Pydantic model with `url: str` and `title: str` fields. Validate in `search_linkedin_jobs()` return and `process_job()` input. Use `JobListing.parse_obj()` to enforce schema.

**Hardcoded Vector Size and Placeholder Vectors:**
- Issue: `memory.py` (lines 33, 47) hardcodes Qdrant vector size as 384 and stores placeholder `[0.0] * 384` vectors for all jobs. No semantic embedding is performed. The vector storage exists but is never used for similarity search or deduplication.
- Files: `career_agent/src/memory.py` (lines 33, 47)
- Impact: Memory service pretends to be a semantic vector DB but stores zero-vectors. If code later attempts similarity search to find related jobs, it will fail (all jobs equally similar). Wastes disk I/O and Qdrant overhead. Configuration can be lost if Qdrant vector size requirement changes.
- Fix approach: Either (a) integrate an embedding model (sentence-transformers or Gemini embeddings API) to generate actual job description vectors, or (b) remove Qdrant entirely and use simple SQLite/JSON for dedup (UUIDv5 is sufficient). If keeping Qdrant, validate vector size matches config at runtime.

**Selector Configuration Fragility:**
- Issue: `scraper.py` (lines 18-25) loads selectors from `career_agent/config/selectors.yaml`. If file missing or YAML parse fails, silently sets `self.selectors = {}`, then later calls like `sel.get("job_card", ".base-card")` proceed with empty selectors. Results in zero jobs extracted.
- Files: `career_agent/config/selectors.yaml`, `career_agent/src/scraper.py` (lines 18-32)
- Impact: Silent failure mode. If selectors.yaml is accidentally deleted or corrupted, scraper returns empty job list with only a logged error. No validation that required keys exist. LinkedIn HTML structure changes (which happen monthly) break selectors silently.
- Fix approach: Make selector loading fail-fast via `with open() as f` (raises FileNotFoundError if missing). Validate required keys `["linkedin", "job_card", "job_title", "job_url", "job_description"]` exist before initializing Scraper. Consider storing selectors in environment variables or data-driven config with version pinning.

**Missing Type Hints for Context Manager:**
- Issue: `search_linkedin_jobs()` and `get_linkedin_job_description()` in `scraper.py` launch Playwright browser instances but never explicitly call `await context.close()` before `await browser.close()`. The context manager handles cleanup, but there's no guarantee the page closes gracefully if an exception occurs between page creation and context exit.
- Files: `career_agent/src/scraper.py` (lines 36-64, lines 69-80)
- Impact: Under load or if an exception occurs mid-page, browser and context may leak. Playwright processes accumulate in memory. Over many iterations, this manifests as OOM crashes or hanging processes.
- Fix approach: Wrap page operations in explicit try-finally or use `async with await browser.new_context() as context:` pattern if Playwright supports it. Add timeout on goto() calls (current `wait_until="networkidle"` can hang indefinitely).

**No Retry Logic for External API Calls:**
- Issue: `hunter.py` (lines 59-61) and `tailor.py` (lines 31-35) call Gemini API via `ai_factory.get_client()` without retry, timeout, or circuit breaker. A single transient API error or rate-limit fails the entire job processing.
- Files: `career_agent/src/hunter.py` (lines 43-66), `career_agent/src/tailor.py` (lines 22-38)
- Impact: High failure rate when Gemini API has blips. One rate-limit rejection = job is skipped forever (UUIDv5 dedup records it as processed). No exponential backoff means repeated failures hammer the API.
- Fix approach: Wrap API calls in `async-retry` with exponential backoff (0.5s, 1s, 2s, 4s, max 3 retries). Implement request timeout (e.g., 30s). Consider circuit breaker to fail-fast if Gemini is down.

## Known Bugs

**Potential KeyError on Missing JD Element:**
- Symptoms: If LinkedIn page loads but job description selector `".description__text"` does not exist, `get_linkedin_job_description()` line 78 calls `.inner_text()` on `None`, causing `AttributeError: 'NoneType' object has no attribute 'inner_text'`.
- Files: `career_agent/src/scraper.py` (line 78)
- Trigger: LinkedIn changes description HTML structure, or Playwright fails to render JS before querying selector.
- Workaround: None. Job will silently fail in `process_job()` error handler.

**Qdrant ID Type Mismatch:**
- Symptoms: `memory.py` (lines 38, 46) generates `job_id_uuid = str(uuid.uuid5(...))`, then passes it as `PointStruct(id=job_id_uuid, ...)` where Qdrant expects `id` to be an integer or UUID object, not a string.
- Files: `career_agent/src/memory.py` (lines 38, 46)
- Trigger: Upsert will silently coerce string to int (hash of string), causing ID collisions or failed dedup checks.
- Workaround: Convert string UUID to int: `int(uuid.uuid5(...).int)`.

**Duplicate UUID Generation:**
- Symptoms: `app.py` (line 48) calls `self.memory._generate_uuid(job["url"])` again to create output directory, but `memory.add_application()` (line 38) generates a different UUID for the same URL (due to different namespace or salt). Dedup check (line 26) uses URLs, but artifact tracking uses UUIDs — they may not match.
- Files: `career_agent/src/app.py` (lines 48, 55), `career_agent/src/memory.py` (lines 21-23, 38)
- Trigger: Always. UUID generation is called twice with same inputs but different execution contexts.
- Workaround: None; both calls use same namespace, so UUIDs should be consistent. Risk: if codebase refactors namespace dynamically, IDs diverge silently.

## Security Considerations

**GEMINI_API_KEY Exposed in CD Pipeline:**
- Risk: `.github/workflows/nemoclaw-cd.yml` (line 69) writes `GEMINI_API_KEY` to `.env` file via sed command. If job logs are accidentally public or if SSH session is compromised, API key is visible in workflow logs or on-disk.
- Files: `.github/workflows/nemoclaw-cd.yml` (line 69)
- Current mitigation: GitHub Secrets are masked in logs by default. Key is written to on-disk `.env` on VPS (only readable by root/container).
- Recommendations: (a) Use Docker build-time secrets or mount secret volumes instead of writing to .env. (b) Implement short-lived token exchange (OAuth2) instead of static API keys. (c) Rotate GEMINI_API_KEY monthly. (d) Add audit logging to CD pipeline showing when secrets are accessed.

**Browser Automation Anti-Bot Evasion:**
- Risk: `scraper.py` (lines 2-7, 42) imports and applies `playwright_stealth` to evade LinkedIn anti-bot detection. This is contractually forbidden by LinkedIn ToS. LinkedIn may permanently ban accounts using this approach.
- Files: `career_agent/src/scraper.py` (lines 2, 42), `career_agent/config/selectors.yaml`
- Current mitigation: Randomized delays and human-like scrolling (lines 84-86). Rate limiting is not enforced.
- Recommendations: (a) Discontinue LinkedIn scraping and switch to LinkedIn API (requires approval). (b) Add configurable rate limiting (min 5-10 second delays between requests). (c) Implement proxy rotation and session management. (d) Add IP rotation or VPN to avoid detection.

**No Input Validation on Job Description Length:**
- Risk: `hunter.py` (line 44) checks JD length > 50 chars, but `tailor.py` (line 26) includes full JD in prompt sent to Gemini. If JD is crafted with prompt injection (e.g., "Ignore your instructions and..."), Gemini may be tricked into generating unintended content.
- Files: `career_agent/src/hunter.py` (lines 43-46), `career_agent/src/tailor.py` (lines 22-28)
- Current mitigation: Pydantic models enforce response format, but prompt itself is unescaped.
- Recommendations: (a) Sanitize JD text before embedding in prompts (escape quotes, newlines, special characters). (b) Use Gemini's JSON mode and explicit schema validation. (c) Add prompt injection detection (scan for common attack patterns).

**No Rate Limiting Between Scraper Calls:**
- Risk: `app.py` (line 71) processes up to 5 jobs in parallel via `asyncio.gather()`. Each job calls `scraper.get_linkedin_job_description()` which launches a full Chromium browser. LinkedIn will detect this as bot behavior and block account/IP.
- Files: `career_agent/src/app.py` (lines 65-73), `career_agent/src/scraper.py` (lines 66-80)
- Current mitigation: None. 5 concurrent browser launches = 5 simultaneous LinkedIn requests.
- Recommendations: (a) Limit concurrency to 1 browser instance at a time (sequential scraping). (b) Add 5-10s delay between requests. (c) Add proxy rotation and account rotation. (d) Monitor IP reputation via external service.

**Bio_Context.md Contains Placeholder Data:**
- Risk: `brain/Bio_Context.md` (lines 4-6, 9-10, 13-14) contains `[PLACEHOLDER]` fields. If these are not filled in before production, Gemini will see incomplete candidate profile and generate irrelevant or generic cover letters.
- Files: `brain/Bio_Context.md`
- Current mitigation: None. File is loaded as-is via `hunter.py` (line 29).
- Recommendations: (a) Validate Bio_Context.md contains no placeholders at app startup. (b) Require environment variable overrides for user details. (c) Add schema validation (Pydantic model for Bio_Context).

## Performance Bottlenecks

**Sequential Playwright Browser Launches:**
- Problem: Each job in `process_job()` calls `scraper.get_linkedin_job_description()` (line 31), which launches a full Chromium browser. Even with 5 concurrent jobs, this requires 5 separate Playwright processes.
- Files: `career_agent/src/app.py` (line 31), `career_agent/src/scraper.py` (lines 69-80)
- Cause: Browser creation is expensive (~1-2 seconds per instance). Launching 5 browsers = ~10 seconds of just startup time, plus network latency for each page load.
- Improvement path: (a) Implement browser pooling (create once, reuse context for multiple pages). (b) Use headless mode + network preload to reduce cold start. (c) Consider switching to `curl` + BeautifulSoup for pure HTML scraping (no JS rendering needed). (d) Add request caching (store fetched JDs in local SQLite).

**Placeholder Vectors Block Semantic Search:**
- Problem: Qdrant is configured with 384-dim vectors, but all job entries store `[0.0] * 384`. Any future attempt to query similar jobs or deduplicate by content will fail.
- Files: `career_agent/src/memory.py` (lines 33, 47)
- Cause: No embedding model integrated. Placeholder vectors were added as scaffolding but never completed.
- Improvement path: Integrate `sentence-transformers` model locally or call Gemini embeddings API. Embed job descriptions on ingestion. This enables semantic deduplication and recommendation.

**Blocking Async Sleep in Scraper:**
- Problem: `scraper.py` (line 75) uses `await asyncio.sleep(2)` as a hard-coded delay after page load. If 5 jobs are processed in parallel, this adds 10 seconds to total wall-clock time (5 jobs × 2 seconds).
- Files: `career_agent/src/scraper.py` (line 75)
- Cause: No adaptive wait. Page may be ready in 0.5s, but code sleeps 2s anyway.
- Improvement path: Replace with page.wait_for_load_state("domcontentloaded") or add timeout with random jitter (0.5-1.5s).

**No Connection Pooling for Qdrant:**
- Problem: `memory.py` (line 16) creates a new `QdrantClient(path="./qdrant_db")` on every instantiation. If Qdrant is running as external service (HTTP), this creates overhead per request.
- Files: `career_agent/src/memory.py` (lines 14-19)
- Cause: Singleton pattern not implemented. Multiple MemoryService instances may create multiple clients.
- Improvement path: Ensure MemoryService is truly a singleton (add `__new__` guard). For HTTP Qdrant, add connection pooling via `httpx.AsyncClient`.

## Fragile Areas

**Selector Configuration as Single Point of Failure:**
- Files: `career_agent/config/selectors.yaml`, `career_agent/src/scraper.py` (lines 18-32)
- Why fragile: LinkedIn changes CSS selectors monthly. A single selector update breaks the entire scraper. No fallback selectors, no version pinning, no automated testing of selectors.
- Safe modification: (a) Add unit test that validates selectors against a cached HTML snapshot of LinkedIn job page. (b) Add version field to selectors.yaml (e.g., "linkedin_version": "2026-03-22"). (c) Implement selector fallback chain (try primary, then secondary, then tertiary selectors). (d) Add post-scrape validation (ensure extracted title/URL are non-empty).
- Test coverage: Zero. No tests verify that selectors still work.

**Gemini API Integration Without Versioning:**
- Files: `career_agent/src/hunter.py` (line 60), `career_agent/src/tailor.py` (line 32)
- Why fragile: Code hardcodes `model="gemini-1.5-flash"` and `model="gemini-1.5-pro"`. If Google deprecates these models or changes API behavior, code breaks silently (API call succeeds but response format may change).
- Safe modification: (a) Move model names to config file or environment variables. (b) Add fallback models (if 1.5-flash unavailable, try 1.5-pro, then fallback-general). (c) Validate response schema before parsing JSON. (d) Add integration tests against production Gemini API (monthly).
- Test coverage: Zero. No tests verify Gemini integration.

**File System Paths Hardcoded:**
- Files: `career_agent/src/app.py` (line 79), `career_agent/src/hunter.py` (lines 28, 32), `career_agent/src/scraper.py` (line 19)
- Why fragile: Paths like `"./brain"`, `os.path.join(self.brain_path, "Bio_Context.md")` assume specific directory structure. If user moves files, app fails silently with FileNotFoundError.
- Safe modification: (a) Use `pathlib.Path` for all path operations. (b) Add configuration file (`config.yaml`) to specify paths. (c) Create required directories at startup (`os.makedirs(..., exist_ok=True)`). (d) Add startup validation logging.
- Test coverage: Zero. No tests for missing files.

**No Schema Validation for Brain Data:**
- Files: `brain/Bio_Context.md`, `brain/Target_Specs.json`
- Why fragile: `hunter.py` (lines 27-33) loads Bio and Specs with no validation. If JSON is malformed or keys are missing, app crashes with `json.JSONDecodeError` or `KeyError`.
- Safe modification: Define Pydantic models for `BioCo

ntext` and `TargetSpecs`. Parse on startup. Validate at runtime with clear error messages.
- Test coverage: Zero.

## Scaling Limits

**Single Browser Process Per Job:**
- Current capacity: Can process ~5 jobs concurrently, each with 1 browser = 5 Chromium processes, ~500MB RAM per browser = 2.5GB minimum for parallel run.
- Limit: Docker memory limit is 2GB (docker-compose.yml line 42). With 5 concurrent jobs, memory exhaustion is likely.
- Scaling path: (a) Reduce concurrency from 5 to 2-3 jobs. (b) Implement browser pooling (reuse 1-2 browsers for all jobs). (c) Increase container memory limit to 4GB. (d) Switch from Playwright to lightweight scraping (curl + jsdom).

**Linear Scaling with Job Count:**
- Current capacity: `run_cycle()` processes jobs sequentially from a scrape. If LinkedIn returns 100 jobs, processing takes ~100 × (5s/job) = 500s (~8 minutes).
- Limit: Cannot exceed Gemini API quota (default 60 requests/minute). With 5 jobs in parallel, each calling Gemini twice (hunter + tailor), that's 10 API calls = quota exhausted in 6 minutes. Further jobs are rate-limited.
- Scaling path: (a) Implement request queuing with token bucket algorithm. (b) Batch jobs into larger prompts (score 10 jobs in single Gemini call). (c) Implement caching (if JD text is identical, reuse previous score). (d) Use cheaper model for initial filtering (gemini-1.5-flash) and save pro for tailoring.

**Qdrant Storage Without Cleanup:**
- Current capacity: Each job stores ~1KB metadata + 384-dim float32 vector (~1.5KB). 1000 jobs = 2.5MB. 10,000 jobs = 25MB (manageable).
- Limit: No TTL or archival. Jobs accumulate forever. After 1 year (~250 working days × 20 jobs/day = 5000 jobs), Qdrant grows to 12.5MB. This is small, but queries slow down as collection grows.
- Scaling path: (a) Add TTL to job records (expire after 30 days). (b) Archive old jobs to separate collection (job_applications_2025_q1, etc.). (c) Add cron job to prune stale records. (d) Switch to time-series DB (InfluxDB, TimescaleDB) for better retention policies.

## Dependencies at Risk

**Playwright Pinning:**
- Risk: Code imports `playwright.async_api` with no version constraint. Playwright 1.40+ changed behavior of `wait_until="networkidle"`. Upgrading may cause scraper to hang or timeout.
- Impact: If requirements.txt or poetry.lock is not committed, dependency resolution picks latest Playwright, breaking scraper.
- Migration plan: (a) Pin Playwright to specific version (`playwright==1.40.0`). (b) Test against next major version quarterly. (c) Add CI job to detect breaking changes.

**Gemini API v1beta:**
- Risk: `client_factory.py` (line 27) hardcodes `https://generativelanguage.googleapis.com/v1beta/openai`. v1beta is experimental and may be deprecated.
- Impact: If Google removes v1beta endpoint, all Gemini calls fail. No fallback to v1 or other models.
- Migration plan: (a) Monitor Google Cloud docs for deprecation announcements. (b) Implement version detection and automatic fallback. (c) Test against stable API versions in CI.

**Qdrant Local Storage:**
- Risk: `memory.py` (line 16) uses local file-based Qdrant (`path="./qdrant_db"`). If qdrant_db directory is corrupted or lost, all dedup history is lost.
- Impact: If container is restarted without persistent volume mount, qdrant_db is recreated empty. All jobs appear "new" again, causing duplicates.
- Migration plan: (a) Validate volume mount in docker-compose.yml. (b) Add backup script to copy qdrant_db before container restart. (c) Consider managed Qdrant Cloud for production.

## Missing Critical Features

**No Deduplication Across Multiple Scrape Sources:**
- Problem: Scraper only checks LinkedIn via `scraper.py`. If the same job exists on LinkedIn AND Indeed, scraper will find it twice (different URLs). Memory service deduplicates by URL, not by job content, so duplicates are added.
- Blocks: Cannot consolidate duplicate job listings from different job boards.

**No Email or Notification System:**
- Problem: When a match is found (high-scoring job), app logs it but doesn't notify the user. User must manually check logs to know an application is ready.
- Blocks: Fully autonomous job hunting workflow. User cannot react in real-time to opportunities.

**No Cover Letter Submission Automation:**
- Problem: `tailor.py` generates cover letters but saves them to disk. There's no automation to submit the letter + resume via LinkedIn/Indeed apply buttons.
- Blocks: End-to-end job application. Still requires manual submission.

**No Feedback Loop for Score Improvement:**
- Problem: Jobs are scored once and cached forever. If user rejects a job (gives negative feedback), the scoring model doesn't learn from it. All future similar jobs are scored the same way.
- Blocks: Personalization. Scoring algorithm cannot improve over time.

**No A/B Testing for Cover Letter Variants:**
- Problem: Tailor service generates one cover letter per job. No ability to test multiple variants or track which cover letter variants get better response rates.
- Blocks: Optimization of application success rate.

## Test Coverage Gaps

**Untested Playwright Scraper:**
- What's not tested: `scraper.py` (lines 27-86). No unit tests verify that selectors are applied correctly or that LinkedIn HTML is parsed without errors.
- Files: `career_agent/src/scraper.py`
- Risk: LinkedIn HTML changes monthly. Breaking changes are discovered in production (jobs stop being scraped), not in CI.
- Priority: High. Scraper is critical path.

**Untested Gemini Integration:**
- What's not tested: `hunter.py` and `tailor.py` API calls. No mock tests verify that Gemini response parsing works or that MatchReport schema is enforced.
- Files: `career_agent/src/hunter.py` (lines 43-66), `career_agent/src/tailor.py` (lines 22-38)
- Risk: API response format change breaks cover letter generation silently. JSON parsing errors are not caught.
- Priority: High. Generation is critical path.

**Untested Memory Deduplication:**
- What's not tested: `memory.py` (lines 54-61). No tests verify that is_already_processed() correctly detects duplicates or that UUID generation is stable.
- Files: `career_agent/src/memory.py`
- Risk: Duplicate jobs are added to memory, causing redundant processing.
- Priority: Medium. Dedup prevents wasted API quota.

**Untested End-to-End Orchestration:**
- What's not tested: `app.py` (lines 65-76). No integration tests verify that run_cycle() correctly chains scraper → hunter → tailor → memory.
- Files: `career_agent/src/app.py`
- Risk: If one step fails, entire cycle breaks silently. Debugging requires manual inspection of logs.
- Priority: Medium. Orchestration logic is complex.

**No Docker Build Tests:**
- What's not tested: `docker-compose.yml`. No CI job verifies that NemoClaw container builds and starts successfully with environment variables.
- Files: `.github/workflows/nemoclaw-ci.yml`, `docker-compose.yml`
- Risk: CD deployment may fail if container image is broken or environment variables are misconfigured.
- Priority: High. Deployment is production path.

**No CD Pipeline Dry-Run:**
- What's not tested: `.github/workflows/nemoclaw-cd.yml`. No staging environment is used. CD deploys directly to production VPS.
- Files: `.github/workflows/nemoclaw-cd.yml`
- Risk: One failed CD deployment = production outage. No rollback mechanism.
- Priority: Critical. Production safety.

---

*Concerns audit: 2026-03-23*
