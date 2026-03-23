# Requirements: NemoClaw Job Hunter

**Defined:** 2026-03-23
**Core Value:** NemoClaw must autonomously get the user to job interviews — from finding listings to submitted applications to tracked follow-ups — with zero manual effort required.

## v1 Requirements

### Infrastructure & Integration

- [x] **INFRA-01**: career_agent/ Python module is wrapped in a FastAPI sidecar service deployable as a second Docker Compose service alongside the OpenClaw container
- [x] **INFRA-02**: NemoClaw (OpenClaw LLM) can invoke career_agent capabilities via HTTP skill endpoint (SKILL.md + /tools/invoke)
- [x] **INFRA-03**: Sidecar and OpenClaw container share the ./brain volume (Bio_Context.md, Target_Specs.json, qdrant_db)
- [x] **INFRA-04**: Existing CI/CD pipeline (GitHub Actions lint → SAST → VPS deploy) covers the new sidecar service
- [ ] **INFRA-05**: playwright-stealth is replaced with patchright for CDP-level bot detection bypass
- [x] **INFRA-06**: Gemini model IDs are upgraded from gemini-1.5-* to gemini-2.5-flash across all services

### Scraping — Platform Coverage

- [ ] **SCRAPE-01**: Agent scrapes tech job listings from France Travail via official OAuth2 REST API (no Playwright)
- [ ] **SCRAPE-02**: Agent scrapes tech job listings from Welcome to the Jungle (Playwright + patchright)
- [ ] **SCRAPE-03**: Agent scrapes tech job listings from APEC (Playwright + patchright)
- [ ] **SCRAPE-04**: Agent scrapes tech job listings from LinkedIn Jobs (Playwright + patchright, discovery only — apply separately)
- [ ] **SCRAPE-05**: Each scraper fails loudly with a Telegram alert rather than silently returning empty results
- [ ] **SCRAPE-06**: Browser context is reused across URLs within a platform batch (not opened/closed per URL)
- [ ] **SCRAPE-07**: Per-platform rate limits and human-paced delays are enforced to avoid account/IP bans

### Scoring & Filtering

- [ ] **SCORE-01**: Agent scores each listing against brain/Bio_Context.md and brain/Target_Specs.json using Gemini
- [ ] **SCORE-02**: Fast-fail exclusion check runs before Gemini scoring (keyword-based, from Target_Specs.json exclusions array)
- [ ] **SCORE-03**: Jobs below scoring_threshold (default 0.85) are marked SKIPPED and not queued for application
- [ ] **SCORE-04**: Score, recommendation (APPLY/SKIP/TAILOR_REQUIRED), and reasoning are stored per job record

### Application Materials Generation

- [ ] **APPLY-01**: Agent detects job listing language (French vs English) to select the correct cover letter template
- [ ] **APPLY-02**: Agent generates French-format lettre de motivation for French jobs (vouvoiement, 3-paragraph accroche→parcours→motivation structure, formal closing formula, PDF output)
- [ ] **APPLY-03**: Agent generates English-format cover letter for international/English-language job listings
- [ ] **APPLY-04**: Generated cover letter is validated before submission: company name present, no hallucinated skills not in Bio_Context.md, language matches job listing
- [ ] **APPLY-05**: CV edits/tailoring suggestions are generated alongside the cover letter (suggested_edits field)

### Auto-Apply Submission

- [ ] **SUBMIT-01**: Agent auto-submits applications on France Travail via API (no Playwright)
- [ ] **SUBMIT-02**: Agent auto-submits applications on Welcome to the Jungle via Playwright form-fill
- [ ] **SUBMIT-03**: Agent auto-submits applications on APEC via Playwright form-fill
- [ ] **SUBMIT-04**: Agent uses LinkedIn Easy Apply for LinkedIn jobs, strictly limited to 20 applications/day maximum with human-paced random delays between submissions
- [ ] **SUBMIT-05**: Agent stops all LinkedIn submissions immediately on any warning signal (captcha, rate-limit page, account warning) and sends Telegram alert
- [ ] **SUBMIT-06**: Application submission is only attempted after deduplication check confirms the job has not been applied to before (cross-platform)

### Application Tracking & Deduplication

- [ ] **TRACK-01**: Every job processed (scraped, scored, applied, skipped) is persisted in aiosqlite with a stable compound ID (platform + company name + normalized job title) — not raw URL
- [ ] **TRACK-02**: Cross-platform deduplication uses company+title fingerprint so the same job posted on multiple boards is not applied to more than once
- [ ] **TRACK-03**: Application status follows a state machine: SCRAPED → SCORED → TAILORED → APPLYING → APPLIED → VIEWED → INTERVIEW / REJECTED / SKIPPED
- [ ] **TRACK-04**: Agent detects status changes (reply emails forwarded via Gmail/IMAP or Telegram forwarding) and updates the state machine accordingly
- [ ] **TRACK-05**: An audit log records every action taken (what was sent, to whom, when) for user review

### Telegram Interface & Reporting

- [ ] **TELE-01**: Agent sends a daily digest via Telegram: applications sent, responses received, pipeline summary
- [ ] **TELE-02**: Agent sends real-time Telegram alerts for significant events: new interview invite, application rejected, scraper failure, rate-limit warning
- [ ] **TELE-03**: User can send /status to NemoClaw via Telegram to get current pipeline state (active applications, pending follow-ups)
- [ ] **TELE-04**: User can send /pause and /resume to NemoClaw via Telegram to halt or restart the autonomous cycle
- [ ] **TELE-05**: User can send /cycle to NemoClaw via Telegram to trigger an immediate scrape+score+apply cycle outside the daily schedule
- [ ] **TELE-06**: Autonomous daily cycle runs on APScheduler AsyncIOScheduler (cron trigger) inside the sidecar FastAPI lifespan

### Follow-Up Automation

- [ ] **FOLLOW-01**: Agent automatically sends one follow-up message to applications with no response after a configurable delay (default: 10 days)
- [ ] **FOLLOW-02**: Follow-up message is generated by Gemini, referencing the original application and role
- [ ] **FOLLOW-03**: Follow-up is recorded in the tracking state machine (FOLLOWED_UP state)
- [ ] **FOLLOW-04**: No second follow-up is sent — one per application maximum

### Negotiation Support

- [ ] **NEGO-01**: When the agent detects an interview invite or offer in the pipeline, it sends a Telegram message with: salary benchmarks for the role/level in France, suggested talking points, company research summary
- [ ] **NEGO-02**: Salary benchmark data is sourced from public datasets (Levels.fyi, APEC salary survey, LinkedIn Salary) and injected via Gemini at offer-detection time

### Legal & Compliance Gate

- [ ] **LEGAL-01**: A named legal review milestone is completed before auto-apply goes live in production: assess GDPR Article 22 applicability, CNIL high-risk AI classification, and EU AI Act obligations for the specific personal-agent use case
- [ ] **LEGAL-02**: User has /pause command available and tested before autonomous apply is enabled
- [ ] **LEGAL-03**: Qdrant local storage and aiosqlite database do not persist any third-party personal data beyond what is strictly necessary for job tracking

## v2 Requirements

### Extended Platform Coverage

- **PLATV2-01**: Cadremploi scraping (French generalist platform)
- **PLATV2-02**: Indeed France scraping
- **PLATV2-03**: Glassdoor France scraping
- **PLATV2-04**: Direct company career page scraping (configurable target list)
- **PLATV2-05**: Remote job boards (We Work Remotely, Remote.co)

### Advanced Materials

- **MATV2-01**: CV is auto-tailored per application (not just suggestions — actual PDF generation)
- **MATV2-02**: LinkedIn profile update suggestions based on target role patterns
- **MATV2-03**: Multi-language support beyond French/English (German, Spanish for international roles)

### Enhanced Tracking

- **TRKV2-01**: Email inbox parsing via IMAP for automatic response detection without forwarding
- **TRKV2-02**: Application timeline visualisation (exported report, not a web dashboard)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web dashboard / admin UI | User explicitly chose Telegram as sole interface; dashboard adds disproportionate complexity |
| Per-application approval gate | User explicitly chose full autonomy; approval gate negates the autonomous design |
| Email digest reporting | Telegram is the chosen interface; email adds a second channel with no benefit |
| Bulk apply without quality gates | Research confirms this causes account bans and reputation damage; 0.85 threshold is non-negotiable |
| Seeking jobs outside tech/engineering | User's target domain is fixed; generalist support adds scraping/scoring complexity |
| Email inbox parsing (v1) | IMAP integration is complex and fragile; defer to v2 — Telegram forwarding covers v1 |
| Cadremploi, Indeed, Glassdoor (v1) | Research confirmed anti-bot tier unknown; defer until core platforms validated |
| Automated salary negotiation | Agent prepares materials; negotiation itself requires human judgment |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |
| INFRA-04 | Phase 1 | Complete |
| INFRA-06 | Phase 1 | Complete |
| INFRA-05 | Phase 2 | Pending |
| SCRAPE-01 | Phase 2 | Pending |
| SCRAPE-04 | Phase 2 | Pending |
| SCRAPE-05 | Phase 2 | Pending |
| SCRAPE-06 | Phase 2 | Pending |
| SCRAPE-07 | Phase 2 | Pending |
| SCORE-01 | Phase 3 | Pending |
| SCORE-02 | Phase 3 | Pending |
| SCORE-03 | Phase 3 | Pending |
| SCORE-04 | Phase 3 | Pending |
| TELE-01 | Phase 4 | Pending |
| TELE-02 | Phase 4 | Pending |
| TELE-03 | Phase 4 | Pending |
| TELE-04 | Phase 4 | Pending |
| TELE-05 | Phase 4 | Pending |
| TELE-06 | Phase 4 | Pending |
| TRACK-01 | Phase 5 | Pending |
| TRACK-02 | Phase 5 | Pending |
| TRACK-03 | Phase 5 | Pending |
| TRACK-04 | Phase 5 | Pending |
| TRACK-05 | Phase 5 | Pending |
| SUBMIT-06 | Phase 5 | Pending |
| SCRAPE-02 | Phase 6 | Pending |
| SCRAPE-03 | Phase 6 | Pending |
| APPLY-01 | Phase 7 | Pending |
| APPLY-02 | Phase 7 | Pending |
| APPLY-03 | Phase 7 | Pending |
| APPLY-04 | Phase 7 | Pending |
| APPLY-05 | Phase 7 | Pending |
| SUBMIT-01 | Phase 8 | Pending |
| SUBMIT-02 | Phase 8 | Pending |
| SUBMIT-03 | Phase 8 | Pending |
| SUBMIT-04 | Phase 8 | Pending |
| SUBMIT-05 | Phase 8 | Pending |
| LEGAL-01 | Phase 8 | Pending |
| LEGAL-02 | Phase 8 | Pending |
| LEGAL-03 | Phase 8 | Pending |
| FOLLOW-01 | Phase 9 | Pending |
| FOLLOW-02 | Phase 9 | Pending |
| FOLLOW-03 | Phase 9 | Pending |
| FOLLOW-04 | Phase 9 | Pending |
| NEGO-01 | Phase 9 | Pending |
| NEGO-02 | Phase 9 | Pending |

**Coverage:**
- v1 requirements: 48 total (note: REQUIREMENTS.md footer previously said 41 — actual count by enumeration is 48)
- Mapped to phases: 48
- Unmapped: 0

---
*Requirements defined: 2026-03-23*
*Last updated: 2026-03-23 after roadmap creation — traceability table populated*
