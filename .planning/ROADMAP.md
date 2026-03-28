# Roadmap: NemoClaw Job Hunter

## Overview

NemoClaw Job Hunter transforms an existing Telegram bot and career agent toolset into a fully autonomous job-hunting system. The build order is dependency-driven: the sidecar integration boundary comes first, then a reliable scraping foundation, then scoring, then the Telegram interface that gives the user visibility and control before any autonomous action begins. Deduplication and the application state machine are hardened next — duplicate applications cannot be unsent. Platform coverage then expands safely onto a proven foundation. Cover letter quality is validated before any letter is submitted autonomously. Auto-apply ships last, gated by a mandatory legal review. Follow-up automation and negotiation support close out v1 once the application pipeline is producing APPLIED-status records.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Sidecar Foundation** - Wrap career_agent in FastAPI sidecar, wire OpenClaw skill integration, share brain volume, extend CI/CD (completed 2026-03-23)
- [ ] **Phase 2: Stealth Layer and Scraping Foundation** - Replace playwright-stealth with patchright, integrate France Travail OAuth2 API, add LinkedIn scraping, enforce rate limits and loud-fail alerting
- [ ] **Phase 3: Scoring Pipeline** - Upgrade to gemini-2.5-flash, run fast-fail exclusion, score all listings against Bio_Context and Target_Specs, persist score records
- [ ] **Phase 4: Telegram Interface and Autonomous Scheduling** - Daily digest, real-time alerts, /status /pause /resume /cycle commands, APScheduler cron cycle inside sidecar lifespan
- [ ] **Phase 5: Deduplication Hardening and Application State Machine** - Company+title fingerprint dedup, aiosqlite-backed state machine, status detection, audit log, dedup gate before any submission
- [ ] **Phase 6: Multi-Platform Scraping Expansion** - Add Welcome to the Jungle and APEC scrapers on hardened stealth layer with cross-platform dedup verified end-to-end
- [ ] **Phase 7: Cover Letter Hardening and French Lettre de Motivation** - Language detection, French vouvoiement format, PDF output, post-generation hallucination validation, gemini-2.5-flash prose quality
- [ ] **Phase 8: Auto-Apply Service and Legal Gate** - Legal review milestone, France Travail API apply, WTTJ/APEC/LinkedIn form-fill, rate limits, Telegram apply confirmation, GDPR data minimisation
- [ ] **Phase 9: Follow-Up Automation and Negotiation Support** - One follow-up per application after configurable delay, salary benchmarks on offer detection, negotiation talking points via Telegram

## Phase Details

### Phase 1: Sidecar Foundation

**Goal**: The career_agent module is accessible to NemoClaw via a stable HTTP boundary with both containers sharing the brain volume and the CI/CD pipeline covering the new service
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-06
**Success Criteria** (what must be TRUE):

1. Sending a Telegram command to NemoClaw causes it to invoke a career agent skill endpoint via HTTP and return a response — the full path is exercised end-to-end
2. The sidecar container starts alongside the OpenClaw container via docker compose up and both containers can read and write to ./brain/
3. A push to master triggers the existing GitHub Actions pipeline, which lints, runs SAST, and deploys the sidecar alongside OpenClaw to the VPS without manual steps
4. All Gemini model references across career_agent and NemoClaw resolve to gemini-2.5-flash (no 1.5-* strings remain)

**Plans**: 5 plans

Plans:

- [x] 01-01-PLAN.md — Test scaffold: requirements.txt + pytest stubs for INFRA-01/02/03
- [x] 01-02-PLAN.md — Gemini model ID upgrade to gemini-2.5-flash + MemoryService BRAIN_PATH fix
- [x] 01-03-PLAN.md — FastAPI sidecar (career_agent/sidecar/main.py) + Dockerfile
- [x] 01-04-PLAN.md — docker-compose.yml career-agent service + .env.example
- [x] 01-05-PLAN.md — SKILL.md + agent.md skill reference + CI requirements install

### Phase 2: Stealth Layer and Scraping Foundation

**Goal**: The scraper operates without playwright-stealth, survives 2026-era bot detection, and retrieves real job listings from France Travail (via API) and LinkedIn (via patchright) with rate limiting enforced and failures surfaced as Telegram alerts
**Depends on**: Phase 1
**Requirements**: INFRA-05, SCRAPE-01, SCRAPE-04, SCRAPE-05, SCRAPE-06, SCRAPE-07
**Success Criteria** (what must be TRUE):

1. A scrape cycle against LinkedIn returns real job listings without triggering a bot block — patchright is installed and playwright-stealth is removed
2. France Travail job listings are retrieved via OAuth2 REST API calls (no browser, no Playwright) and returned to the scoring pipeline
3. When a scraper encounters a block, captcha, or empty result, NemoClaw sends a Telegram alert naming the platform and the error — no silent failure
4. Browser context is opened once per platform batch and reused across all URLs in that batch — not opened and closed per URL
5. Per-platform delay configs exist in career_agent/config/ and are enforced between requests — scraping does not run at machine speed

**Plans**: 5 plans

Plans:

- [ ] 02-01-PLAN.md — Wave 0: Dependencies, models, test scaffolds, conftest fix, Dockerfile update
- [ ] 02-02-PLAN.md — patchright migration + context reuse + rate limiting in scraper.py
- [ ] 02-03-PLAN.md — France Travail OAuth2 API scraper methods
- [ ] 02-04-PLAN.md — AlertService implementation (Telegram one-shot alerts)
- [ ] 02-05-PLAN.md — App integration: dual scraper in run_cycle + docker env vars

### Phase 3: Scoring Pipeline

**Goal**: Every scraped listing is scored against the candidate's Bio_Context and Target_Specs using gemini-2.5-flash, with fast-fail exclusion running first, and score records persisted for every job regardless of outcome
**Depends on**: Phase 2
**Requirements**: SCORE-01, SCORE-02, SCORE-03, SCORE-04
**Success Criteria** (what must be TRUE):

1. A job listing containing an exclusion keyword from Target_Specs.json is marked SKIPPED without a Gemini API call being made
2. A job listing passing the exclusion check is scored by Gemini and receives a numeric score, a recommendation (APPLY/SKIP/TAILOR_REQUIRED), and a reasoning string
3. Jobs scoring below the scoring_threshold (default 0.85) are marked SKIPPED and not queued for application
4. Score, recommendation, and reasoning are persisted per job record and visible in the pipeline state

**Plans**: 3 plans

Plans:

- [ ] 03-01-PLAN.md — Wave 0: Extend models.py with ScoreRecord + MatchReport.reasoning; scaffold test_hunter.py stubs
- [ ] 03-02-PLAN.md — Rewrite HunterService: brain_path injection, JobListing input, fast-fail, gemini-2.5-flash, ScoreRecord output, activate tests
- [ ] 03-03-PLAN.md — Wire scoring into app.py: process_job accepts JobListing, persists ScoreRecord fields, SKIP gate

### Phase 4: Telegram Interface and Autonomous Scheduling

**Goal**: The user has full visibility and control over NemoClaw via Telegram — daily digests arrive automatically, real-time alerts fire on significant events, and commands (/status, /pause, /resume, /cycle) work reliably — and the autonomous daily cycle runs on a cron schedule without user intervention
**Depends on**: Phase 3
**Requirements**: TELE-01, TELE-02, TELE-03, TELE-04, TELE-05, TELE-06
**Success Criteria** (what must be TRUE):

1. Once per day, NemoClaw sends a Telegram message summarising applications sent, responses received, and pipeline counts — without the user asking
2. When a scraper fails or a rate-limit warning fires, a Telegram alert arrives within seconds identifying the event
3. Sending /status returns the current pipeline state (active applications, pending follow-ups) as a Telegram message
4. Sending /pause halts the autonomous cycle and /resume restarts it — both commands take effect immediately and are confirmed via Telegram
5. Sending /cycle triggers an immediate scrape+score cycle outside the daily schedule and NemoClaw confirms it started

**Plans**: 4 plans

Plans:

- [ ] 04-01-PLAN.md — Telegram handlers (/status, /pause, /resume, /cycle) + FastAPI status/control endpoints
- [ ] 04-02-PLAN.md — AsyncIOScheduler in Sidecar lifespan + daily run_cycle trigger
- [ ] 04-03-PLAN.md — AlertService: surface scraper/block failures to user in real-time
- [ ] 04-04-PLAN.md — Daily digest: automated cron-triggered summary message at 20:00

### Phase 5: Deduplication Hardening and Application State Machine

**Goal**: Every job processed is tracked in aiosqlite with a compound identity that survives URL changes, cross-platform duplicates are caught by company+title fingerprint before any submission attempt, and application status transitions follow a defined state machine that is the backbone for all downstream automation
**Depends on**: Phase 4
**Requirements**: TRACK-01, TRACK-02, TRACK-03, TRACK-04, TRACK-05, SUBMIT-06
**Success Criteria** (what must be TRUE):

1. The same job posted on LinkedIn and Welcome to the Jungle is stored as one record and will not be applied to twice — the company+title fingerprint catches the duplicate even if the URLs differ
2. Every job moves through the state machine (SCRAPED → SCORED → TAILORED → APPLYING → APPLIED → VIEWED → INTERVIEW / REJECTED / SKIPPED) and the current status is queryable
3. A status change detected from an incoming email or Telegram forward updates the job's state machine entry automatically
4. An audit log entry is written for every action taken (what was sent, to whom, when) and is retrievable via a Telegram command
5. No application submission is attempted until the deduplication check confirms the job has not been applied to before across all platforms

**Plans**: 3 plans

Plans:

- [ ] 05-01-PLAN.md — aiosqlite implementation: tracking.db schema + TrackingService
- [ ] 05-02-PLAN.md — Deduplication logic: Normalized Title + Company fingerprinting
- [ ] 05-03-PLAN.md — Pipeline gate: enforce fingerprint de-dup + update status states

### Phase 6: Multi-Platform Scraping Expansion

**Goal**: Welcome to the Jungle and APEC scrapers are live, feeding listings into the scoring pipeline, with cross-platform deduplication verified across all three platforms end-to-end
**Depends on**: Phase 5
**Requirements**: SCRAPE-02, SCRAPE-03
**Success Criteria** (what must be TRUE):

1. A scrape cycle retrieves real job listings from Welcome to the Jungle and passes them through the scoring pipeline
2. A scrape cycle retrieves real job listings from APEC and passes them through the scoring pipeline
3. The same tech job posted on LinkedIn, Welcome to the Jungle, and APEC produces exactly one record in the tracking database — not three separate application attempts

**Plans**: 2 plans

Plans:

- [ ] 06-01-PLAN.md — Welcome to the Jungle scraper (Playwright-based)
- [ ] 06-02-PLAN.md — APEC scraper (Playwright-based)

### Phase 7: Cover Letter Hardening and French Lettre de Motivation

**Goal**: Every cover letter generated is validated before it could ever be submitted — company name is present, no skills appear that are not in Bio_Context.md, the language matches the job listing — and French-language jobs receive a properly formatted lettre de motivation in PDF format
**Depends on**: Phase 6
**Requirements**: APPLY-01, APPLY-02, APPLY-03, APPLY-04, APPLY-05
**Success Criteria** (what must be TRUE):

1. A French-language job listing produces a lettre de motivation with vouvoiement, three-paragraph accroche-parcours-motivation structure, and formal closing formula, exported as a PDF
2. An English-language job listing produces a standard English-format cover letter
3. A cover letter referencing a skill not present in Bio_Context.md is rejected by the validation step and triggers a Telegram alert before any submission occurs
4. A cover letter missing the company name or role title is rejected by the validation step — it does not proceed to submission
5. CV tailoring suggestions (suggested_edits) are generated alongside every cover letter

**Plans**: 3 plans

Plans:

- [ ] 07-01-PLAN.md — French "Lettre de Motivation" (Vouvoiement + structural prompt refactor)
- [ ] 07-02-PLAN.md — PDF Service: professional cover letter output generation
- [ ] 07-03-PLAN.md — Post-generation validation: catch hallucinations + missing mandatory fields

### Phase 8: Auto-Apply Service and Legal Gate

**Goal**: NemoClaw autonomously submits applications on France Travail, Welcome to the Jungle, APEC, and LinkedIn Easy Apply — after a named legal review milestone confirms GDPR/CNIL compliance — with human-paced delays, rate limits, Telegram confirmation of every submission, and a full audit trail
**Depends on**: Phase 7
**Requirements**: SUBMIT-01, SUBMIT-02, SUBMIT-03, SUBMIT-04, SUBMIT-05, LEGAL-01, LEGAL-02, LEGAL-03
**Success Criteria** (what must be TRUE):

1. The GDPR Article 22 / CNIL / EU AI Act legal review is documented as complete before any autonomous submission goes to production — this milestone is a hard gate
2. NemoClaw submits an application on France Travail via the official API, receives a confirmation receipt, and records it in the state machine as APPLIED
3. NemoClaw submits an application on Welcome to the Jungle and APEC via Playwright form-fill with human-paced delays between fields, and records confirmation
4. LinkedIn Easy Apply submissions are capped at 20 per day with randomised human-paced delays, and any captcha, rate-limit page, or account warning causes all LinkedIn submissions to stop immediately with a Telegram alert
5. The /pause command is tested and confirmed to halt all autonomous submissions before any production apply is enabled
6. The Qdrant and aiosqlite stores contain no third-party personal data beyond the minimum fields required for job tracking

**Plans**: 3 plans

Plans:

- [ ] 08-01-PLAN.md — France Travail official candidate API submission (OAuth2)
- [ ] 08-02-PLAN.md — Multi-platform form-fillers (WTTJ + APEC) with human-mimicry
- [ ] 08-03-PLAN.md — LinkedIn Easy Apply automation + rate-limit circuit breakers

### Phase 9: Follow-Up Automation and Negotiation Support

**Goal**: Applications with no response after a configurable delay receive exactly one Gemini-generated follow-up message in the language of the original application, and when an interview invite or offer is detected the user receives salary benchmarks and negotiation talking points via Telegram
**Depends on**: Phase 8
**Requirements**: FOLLOW-01, FOLLOW-02, FOLLOW-03, FOLLOW-04, NEGO-01, NEGO-02
**Success Criteria** (what must be TRUE):

1. An application with no response after the configured delay (default 10 days) automatically receives one follow-up message generated by Gemini referencing the original role
2. A French-language application receives a French follow-up; an English-language application receives an English follow-up
3. No application receives more than one follow-up — the state machine enforces a one-follow-up maximum
4. When an interview invite or offer is detected in the pipeline, NemoClaw sends a Telegram message containing salary benchmarks for the role/level in France and suggested negotiation talking points

**Plans**: 2 plans

Plans:

- [ ] 09-01-PLAN.md — Autonomous 10-day follow-up logic (one-shot per app)
- [ ] 09-02-PLAN.md — Nego-Service: Detect interview/offer and push salary benchmarks

## Progress

**Execution Order:**

Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Sidecar Foundation | 5/5 | Complete   | 2026-03-23 |
| 2. Stealth Layer and Scraping Foundation | 5/5 | Complete | 2026-03-24 |
| 3. Scoring Pipeline | 3/3 | Complete | 2026-03-25 |
| 4. Telegram Interface and Autonomous Scheduling | 4/4 | Complete | 2026-03-27 |
| 5. Deduplication Hardening and Application State Machine | 3/3 | Complete | 2026-03-27 |
| 6. Multi-Platform Scraping Expansion | 2/2 | Complete | 2026-03-27 |
| 7. Cover Letter Hardening and French Lettre de Motivation | 3/3 | Complete | 2026-03-28 |
| 8. Auto-Apply Service and Legal Gate | 3/3 | Complete | 2026-03-28 |
| 9. Follow-Up Automation and Negotiation Support | 2/2 | Complete | 2026-03-28 |
