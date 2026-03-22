# Project Research Summary

**Project:** NemoClaw / Project Phoenix — Autonomous Job-Hunting Agent
**Domain:** Agentic AI — LLM-orchestrated job scraping, scoring, tailoring, and auto-apply (French + global markets)
**Researched:** 2026-03-23
**Confidence:** MEDIUM-HIGH

## Executive Summary

NemoClaw / Project Phoenix is a brownfield autonomous job-hunting agent with a meaningful foundation already in place: Playwright-based LinkedIn scraping, Gemini-powered job scoring and cover letter generation, Qdrant deduplication, and a Telegram interface via the OpenClaw container. The research consensus is that this architecture is sound but incomplete — the existing codebase is a solid scoring and artifact-generation tool that stops short of actual autonomous operation. The critical gaps are: no auto-apply submission, no application state machine, no multi-platform scraping beyond LinkedIn, and no Telegram reporting. These gaps must all close for the agent to fulfil its core promise.

The recommended build approach is a sidecar pattern: a new FastAPI service wraps the existing `career_agent/` Python module and exposes HTTP endpoints that the OpenClaw LLM container calls as a skill. This gives clean process isolation (a crashed Playwright browser cannot destabilize the NemoClaw Telegram session), typed inter-service contracts, and a scheduling layer (APScheduler inside the sidecar lifespan) for daily autonomous cycles. The stack changes are minimal: replace `playwright-stealth` with `patchright` for enterprise-grade bot evasion, upgrade Gemini model IDs from deprecated 1.5 to `gemini-2.5-flash`, and add `python-telegram-bot[job-queue]` and `aiosqlite` for scheduling and application tracking. France Travail has an official OAuth2 REST API that eliminates scraping risk for the largest French public job board — use it first.

The primary risks are platform bans from scraping velocity, LLM hallucination in auto-submitted cover letters, and duplicate applications reaching the same employer across platforms. All three are preventable by design: randomized delays with per-platform rate configs, a post-generation validation step in `TailorService`, and a company+title fingerprint deduplication layer on top of the existing URL-based check. A legal review milestone must precede production auto-apply given the EU AI Act's high-risk classification of automated candidate screening tools and CNIL's active enforcement in France.

---

## Key Findings

### Recommended Stack

The existing Python + Playwright + Qdrant + Gemini stack is the correct foundation. The primary upgrades are a stealth layer swap and a model version bump. `playwright-stealth` only patches JavaScript surface properties and is defeated by 2025-era enterprise bot detection (DataDome, Cloudflare Turnstile, LinkedIn's WAF). `patchright 1.58.2` replaces it with CDP-level binary patching using an identical Playwright API — zero code rewrite required. Gemini `1.5-flash` and `1.5-pro` are deprecated as of March 2026; all services must migrate to `gemini-2.5-flash`. The `AsyncOpenAI` / OpenAI-compat layer in `client_factory.py` is unchanged.

New additions: `python-telegram-bot 22.7` with its `[job-queue]` extra provides both the Telegram bot framework and APScheduler-backed scheduling in a single dependency. `aiosqlite 0.22.1` provides async SQLite for structured application status queries (WHERE status='APPLIED' AND applied_at < 7 days ago) — Qdrant handles deduplication/vector work, SQLite handles relational tracking. `httpx` handles France Travail's OAuth2 REST API without Playwright overhead. `tenacity` wraps all Gemini and scraper calls with exponential-backoff retry.

**Core technologies:**
- `patchright 1.58.2`: stealth browser automation — replaces `playwright-stealth`; undetectable against LinkedIn/WTTJ/APEC bot detection in 2026
- `gemini-2.5-flash` (via existing `client_factory.py`): scoring and generation — `1.5-*` deprecated March 2026; same integration point, model ID string change only
- `python-telegram-bot 22.7 [job-queue]`: Telegram interface + scheduling — built-in APScheduler removes need for a second scheduler dependency
- `aiosqlite 0.22.1`: application status tracking — SQLite is correct for single-user pipeline (hundreds of rows); Qdrant stays for dedup only
- `httpx 0.27+`: France Travail official API — OAuth2 REST, no Playwright required, most reliable French platform integration
- `tenacity 8.x`: retry logic — mandatory for autonomous operation; Gemini free tier is 5 RPM (Dec 2025); single 429 must not abort a cycle

**Critical version constraint:** Do NOT install `playwright` alongside `patchright` — they conflict on Chromium binary management. `patchright` ships its own Chromium.

### Expected Features

The research distinguishes clearly between what makes the agent autonomous (table stakes) and what makes it competitive (differentiators). All table-stakes features are build prerequisites; without them, the agent is a cover-letter generator, not an autonomous agent.

**Must have (table stakes) — v1:**
- Multi-platform scraping: LinkedIn (existing) + France Travail API + Welcome to the Jungle + APEC — single platform misses most of the French cadre market
- Application status state machine: QUEUED → APPLIED → VIEWED → INTERVIEW → OFFER → REJECTED → GHOSTED — without this, auto-apply is a black box
- French-language cover letter (lettre de motivation): formal vouvoiement, three-paragraph structure, half-page, PDF — English letters to French employers trigger disqualification
- Telegram daily digest + real-time alerts: primary user interface; agent is silent without it
- Telegram command interface: `/search`, `/status`, `/pause`, `/resume` — autonomous system without a pause command is uncontrollable
- Per-platform stealth profiles: session persistence, rate limiting, per-platform browser contexts — LazyApply gets banned because it moves at machine speed
- Cross-platform deduplication: company+title fingerprint in addition to URL — same job on LinkedIn + WTTJ + company site produces three different URL hashes

**Should have (competitive) — v1.x:**
- Welcome to the Jungle + APEC scraping — French cadre/tech startup market; covers the roles that don't appear on LinkedIn
- Follow-up automation: one polite follow-up at day 7-10 for no-response applications (data shows Wednesday 10am local achieves best response rates)
- Salary benchmark context per offer: flag below-market offers before applying; Paris SE median ~55-65K EUR, AI/ML +10-12%
- Company research injection: 2-3 sentences of company context per cover letter; measurable quality improvement
- Gap analysis surfaced in Telegram: skill gaps per matched job in daily digest; no competitor offers this

**Defer (v2+):**
- Negotiation prep package: meaningful only when first offer arrives; build then
- Indeed/Glassdoor scraping: lower priority for French tech market; LinkedIn + WTTJ + APEC cover ~80% of target roles
- Conversational NemoClaw pipeline queries: NemoClaw already has the reasoning capability; wire pipeline state into brain/ context
- CV keyword patching (automated): high complexity, personal format; keep as suggested_edits list until v1 is validated

**Explicit anti-features (do not build):**
- Web dashboard: user's interface is Telegram; adding a frontend adds full-stack overhead for zero autonomy gain
- Bulk apply mode (100+ per day): proven account bans; quality degradation; the 0.85 scoring threshold enforces the right behaviour
- Email inbox parsing: GDPR surface area; OAuth to personal email; low reliability

### Architecture Approach

The recommended architecture is a two-container system: the existing OpenClaw container handles LLM reasoning and Telegram I/O, while a new `career-agent` sidecar container wraps `PhoenixApp` in a FastAPI HTTP service. OpenClaw invokes the sidecar via an OpenClaw Skill definition (SKILL.md), which maps natural-language tool calls to typed HTTP POST/GET requests. The sidecar runs its own APScheduler for daily autonomous cycles. Both containers share a single `./brain/` volume mount as the persistence layer — no inter-service sync required. The sidecar calls the Telegram Bot API directly for outbound-only push notifications; NemoClaw handles inbound commands. This split prevents a crashed Playwright browser from destabilizing the Telegram session.

**Major components:**
1. OpenClaw container (existing) — LLM reasoning, Telegram I/O, skill dispatch; invoke career agent via HTTP skill
2. Career Agent Sidecar (new `api.py`) — FastAPI wrapper around `PhoenixApp`; exposes `/cycle`, `/status`, `/pipeline`; runs APScheduler for autonomous daily cycles
3. Scraper (extend existing) — Playwright + patchright; one browser instance per cycle, one context per platform; session-cookie persistence per platform
4. HunterService (keep, upgrade model) — Gemini `2.5-flash` scoring; fast-fail exclusion check; MatchReport with gap analysis
5. TailorService (extend) — French lettre de motivation mode with language detection; validation step post-generation; `temperature=0.3`
6. ApplyService (new `apply.py`) — Playwright form-fill per platform; human-paced delays; ATS honeypot avoidance; confirmation receipt required
7. MemoryService (extend) — Qdrant for deduplication + status state machine; aiosqlite for structured status queries; company+title fingerprint dedup layer
8. Reporter (new `reporter.py`) — direct Telegram Bot API POST; outbound-only; daily digest + real-time match alerts; queue outbound at max 1 message/sec
9. FollowUpService (new `followup.py`) — state-machine-gated; status re-check before send; language-matched to original application
10. OpenClaw Skill (new `skills/career_agent/SKILL.md`) — YAML schema mapping NemoClaw tool calls to sidecar HTTP endpoints

### Critical Pitfalls

1. **Platform ban from scraping velocity** — Uniform-interval requests at machine speed are detected regardless of stealth patches. Prevention: randomize delays `sleep(random.uniform(3, 12))`, per-platform rate-limit configs in `career_agent/config/`, max 15-20 LinkedIn visits per session, staggered platform rotation. Address in scraping foundation phase before adding any new platforms.

2. **Cloudflare / Turnstile blocking `playwright-stealth`** — `playwright-stealth` fails against 2025-era WAFs (DataDome, Cloudflare Turnstile, LinkedIn's enterprise bot detection). Prevention: migrate to `patchright` immediately; design a loud-fail + Telegram alert fallback for any platform block; never return empty results silently. Address before any production scraping.

3. **Duplicate application to same employer across platforms** — The current UUIDv5-from-URL dedup misses the same job listed on LinkedIn + WTTJ + company site. Prevention: canonicalize URLs (strip UTM params), add company+title fingerprint as secondary dedup key, check both before any submission. Must be hardened before auto-apply is enabled — recovery cost is HIGH (cannot unsend).

4. **LLM hallucination in auto-submitted cover letters** — Gemini fills gaps with plausible-sounding fabrications (wrong company name, invented facts, skills the candidate doesn't have). Since there is no review gate, these go out as-is, causing reputational damage. Prevention: structured JSON output schema with explicit company name + role title variables, post-generation validation step, `temperature=0.3`, Telegram digest includes a summary of claims in each letter. Must be first-class concern, not post-MVP addition.

5. **GDPR / CNIL compliance — France-specific** — The EU AI Act (in force February 2025) classifies HR/recruitment AI as high-risk. CNIL actively enforces data minimisation and human oversight requirements. Prevention: store only minimum necessary fields in Qdrant (no recruiter PII, no full JD text), implement data retention auto-purge at 12 months, provide a user-retrievable audit log via `/history`, add encryption at rest for Qdrant data. A legal review milestone must gate production auto-apply.

---

## Implications for Roadmap

Research strongly suggests an 8-phase build order driven by two constraints: (1) each phase must not break CI, and (2) each new phase requires the prior phase's contracts to be stable. The architecture's build order section is explicit and matches the feature dependency graph.

### Phase 1: Foundation — Sidecar + Skill Integration
**Rationale:** All subsequent phases require a stable HTTP boundary between OpenClaw and the career agent. Building the sidecar first proves the integration path before any feature development begins. Zero changes to existing `career_agent/` code — just wraps `PhoenixApp` in FastAPI. Lowest risk phase, highest leverage.
**Delivers:** `career_agent/src/api.py` (FastAPI sidecar), `skills/career_agent/SKILL.md`, Docker Compose `career-agent` service entry, end-to-end: Telegram command → NemoClaw → sidecar → brain.
**Addresses:** Architecture anti-pattern 1 (subprocess via shell is wrong); establishes typed HTTP contract for all future features.
**Avoids:** Playwright crashing the NemoClaw Telegram session.
**Research flag:** Standard patterns — well-documented FastAPI + OpenClaw skill integration; skip deep research phase.

### Phase 2: Stealth Layer + Scraping Foundation
**Rationale:** The current `playwright-stealth` is confirmed broken against LinkedIn and other enterprise WAFs. All scraping depends on this layer; fixing it before expanding platform coverage prevents cascading failures. Rate-limiting architecture must be designed here before new platforms are added.
**Delivers:** `patchright` replacing `playwright-stealth` in `scraper.py`, per-platform rate-limit configs in `career_agent/config/`, session-cookie persistence for LinkedIn, France Travail `httpx`-based OAuth2 API integration (no Playwright), Telegram alert on scraper failure.
**Uses:** `patchright 1.58.2`, `httpx 0.27+`, `tenacity 8.x`, extended `selectors.yaml`.
**Avoids:** Platform ban from velocity (Pitfall 1), Cloudflare blocking (Pitfall 2), silent scraping failure (UX pitfall).
**Research flag:** Needs per-platform testing research. Detection behaviour varies; the patchright vs Camoufox decision for LinkedIn specifically may need a validation spike.

### Phase 3: APScheduler + Autonomous Daily Cycles
**Rationale:** Once the sidecar is live and scraping is reliable, the autonomous scheduling layer can be added. APScheduler inside FastAPI lifespan is the confirmed pattern. PTB `[job-queue]` provides this without a separate scheduler dependency.
**Delivers:** Sidecar runs daily cycles autonomously at configurable cron times with jitter. `python-telegram-bot[job-queue] 22.7` installed. Follow-up scheduling infrastructure (scheduler in place, FollowUpService deferred to Phase 7).
**Uses:** `python-telegram-bot 22.7 [job-queue]`, APScheduler `AsyncIOScheduler`.
**Avoids:** Tight Telegram polling loop (performance trap); blocking event loop.
**Research flag:** Standard patterns — APScheduler + FastAPI lifespan is a documented, well-understood pattern; skip deep research.

### Phase 4: Telegram Reporter + Command Interface
**Rationale:** The agent must have a communication channel before auto-apply is enabled. Reporting and command interface together because they share the bot instance; doing them separately creates integration overhead.
**Delivers:** `reporter.py` (direct Telegram Bot API push, max 1 msg/sec queue), daily digest, real-time match alerts, `/search`, `/status`, `/pause`, `/resume` commands wired into NemoClaw `agent.md`.
**Uses:** `python-telegram-bot 22.7`, direct `api.telegram.org` POST.
**Avoids:** Silent failures (UX pitfall), agent without pause/resume (UX pitfall), daily digest too long (UX pitfall — top 3 matches + summary stats, not 50-item list).
**Research flag:** Standard patterns — PTB and direct Telegram API are well-documented; skip deep research.

### Phase 5: Deduplication Hardening + Application State Machine
**Rationale:** Must be complete before auto-apply. Sending a duplicate application is unrecoverable (cannot unsend). The state machine is a prerequisite for follow-up logic, reporting, and negotiation prep — it is the backbone of all downstream features.
**Delivers:** Company+title fingerprint dedup layer in `memory.py`, URL canonicalization (strip UTM/tracking params), `aiosqlite`-backed status store, state machine: QUEUED → APPLIED → VIEWED → INTERVIEW → OFFER → REJECTED → GHOSTED, `scoring_threshold` read from `Target_Specs.json` at runtime, Telegram command to update threshold.
**Uses:** `aiosqlite 0.22.1`, `pydantic 2.x` extended models.
**Avoids:** Duplicate application (Pitfall 3 — HIGH recovery cost), no state machine = follow-up impossible (technical debt).
**Research flag:** Standard patterns — state machine and SQLite dedup are well-understood; skip deep research.

### Phase 6: Multi-Platform Scraping Expansion
**Rationale:** With the stealth layer hardened and the state machine in place, expanding platform coverage is safe and incremental. France Travail (API) should already be done in Phase 2; this phase adds WTTJ and APEC (both require Playwright stealth).
**Delivers:** WTTJ scraper (Algolia internal endpoint preferred over HTML parsing), APEC scraper (Playwright), `selectors.yaml` extended with WTTJ and APEC selector blocks, cross-platform dedup verified end-to-end (same job on 3 platforms → 1 application).
**Uses:** `patchright`, extended `selectors.yaml`, WTTJ Algolia endpoint (`httpx` where possible).
**Avoids:** Platform coverage gaps missing French cadre roles.
**Research flag:** Needs per-platform research during planning — WTTJ Algolia app ID and endpoint path need verification; APEC authentication flow needs documentation review before implementation.

### Phase 7: Cover Letter Hardening + French Lettre de Motivation
**Rationale:** Cover letter quality gates auto-apply. The current `tailor.py` produces English-format output and has no hallucination prevention. Both must be fixed before letters are submitted autonomously.
**Delivers:** French lettre de motivation mode in `TailorService` (language detection, formal vouvoiement, three-paragraph structure, half-page, PDF via reportlab/weasyprint), post-generation validation step (company name + role title cross-check, no fabricated facts), `temperature=0.3`, Telegram digest includes letter claim summary, model upgrade to `gemini-2.5-flash`.
**Uses:** `gemini-2.5-flash`, `reportlab` or `weasyprint` for PDF output.
**Avoids:** LLM hallucination in sent letters (Pitfall 4 — HIGH recovery cost, no recall possible).
**Research flag:** French lettre de motivation format is HIGH confidence (sourced from ADP France, France Travail official guidance); PDF library choice needs a quick evaluation spike (reportlab vs weasyprint); skip deep research.

### Phase 8: Auto-Apply Service + Legal Review Milestone
**Rationale:** The highest-risk phase. ApplyService depends on all prior phases being stable (dedup hardened, state machine in place, cover letters validated, reporting active). GDPR/CNIL legal review must gate this phase — EU AI Act high-risk classification requires documented human oversight.
**Delivers:** `apply.py` (Playwright form-fill for LinkedIn Easy Apply, WTTJ, France Travail forms), human-paced delays between form fields, ATS honeypot field avoidance, submission confirmation receipt required (not just "form filled"), application audit log via `/history` command, data minimisation audit (no recruiter PII in Qdrant), `DATA_PROCESSING.md` (GDPR Article 30 documentation), 12-month data retention auto-purge.
**Uses:** `patchright`, `aiosqlite` (audit log), `reporter.py` (submission confirmation push).
**Avoids:** Duplicate application (final check gate), GDPR/CNIL violation (Pitfall 5), auto-apply with no audit trail (security mistake).
**Research flag:** Needs per-platform research — LinkedIn Easy Apply form selectors, WTTJ application form flow, and France Travail apply endpoint all need platform-specific investigation before implementation; GDPR review is a hard milestone, not optional.

### Phase 9: Follow-Up Automation + v1.x Differentiators
**Rationale:** Follow-up requires APPLIED status records to exist (from Phase 8). Salary benchmarking and company research injection are low-complexity, high-value additions that improve application quality without structural changes.
**Delivers:** `followup.py` (state-machine-gated; status re-check before send; language-matched; one follow-up per application maximum; Wednesday 10am local timing), salary benchmark context per offer (hardcoded French tech market rates + Levels.fyi reference), company research injection (2-3 sentences per cover letter via Gemini search), gap analysis surfaced in Telegram daily digest.
**Uses:** Existing `TailorService` (follow-up generation), `reporter.py`, `aiosqlite` status store.
**Avoids:** Follow-up to wrong status (Pitfall 6 — state re-check before send), follow-up in wrong language (store `application_language` in metadata).
**Research flag:** Standard patterns for follow-up state machine; salary benchmark data is static and can be hardcoded initially; skip deep research.

### Phase Ordering Rationale

- Phases 1-3 build infrastructure with zero new logic in existing code — safe, CI-friendly, proves integration before features
- Phase 4 (reporting) must precede Phase 8 (auto-apply) so the user is never surprised by autonomous action
- Phase 5 (dedup + state machine) must precede Phase 8 (auto-apply) because duplicate application and status tracking are unrecoverable failures
- Phase 6 (platform expansion) is deliberately placed after Phase 5 so the dedup system is hardened before new platforms add volume
- Phase 7 (cover letter) must precede Phase 8 (auto-apply) because letters are submitted in Phase 8
- Phase 8 is a hard gate — no autonomous submissions until dedup is hardened, letters are validated, and legal review is done
- Phase 9 (follow-up + differentiators) is placed last because it requires APPLIED-status records that only exist after Phase 8

### Research Flags

Phases needing deeper research during planning:
- **Phase 2:** Per-platform detection behaviour validation; patchright effectiveness on LinkedIn/WTTJ/APEC should be confirmed with a scraping spike before committing to the approach
- **Phase 6:** WTTJ Algolia endpoint app ID and query schema; APEC authentication flow and apply mechanism; both need platform-specific investigation
- **Phase 8:** LinkedIn Easy Apply selectors (change frequently), WTTJ and France Travail form flows, GDPR/CNIL review is a mandatory milestone with legal input

Phases with standard, well-documented patterns (skip deep research):
- **Phase 1:** FastAPI + OpenClaw skill HTTP integration — documented in official OpenClaw docs
- **Phase 3:** APScheduler AsyncIOScheduler + FastAPI lifespan — official APScheduler docs cover this exactly
- **Phase 4:** PTB v22 + direct Telegram API — comprehensive official documentation
- **Phase 5:** State machine design + aiosqlite — standard patterns, no novel elements
- **Phase 7:** French lettre de motivation format — HIGH confidence from official French government and HR sources; PDF library is a narrow library-selection decision
- **Phase 9:** Follow-up state machine + digest enrichment — well-understood patterns

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core technology choices verified against official PyPI releases, official docs, and multiple independent sources. patchright effectiveness is MEDIUM (community-sourced, not independently verified in this research cycle). Gemini deprecation timeline is HIGH (official Google AI docs). |
| Features | MEDIUM-HIGH | Table-stakes features are well-established based on competitor analysis and the project's stated requirements. French market specifics (lettre de motivation format, France Travail API) are HIGH confidence (official French government sources). Auto-apply ban risk thresholds are MEDIUM (practitioner estimates, not official platform statements). |
| Architecture | HIGH | OpenClaw skill/HTTP integration verified against official OpenClaw docs. APScheduler + FastAPI lifespan pattern verified against official APScheduler docs. Shared-volume IPC pattern is standard Docker Compose practice. Sidecar pattern recommendation is based on solid rationale from existing code inspection. |
| Pitfalls | MEDIUM | Platform ban mechanics and detection techniques: MEDIUM (practitioner sources, no official LinkedIn anti-bot documentation). GDPR/EU AI Act applicability: HIGH (official CNIL guidelines, EU AI Act text, legal publications). LLM hallucination prevention: MEDIUM (EvidentlyAI, prompt engineering best practices). |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **patchright vs Camoufox decision for LinkedIn specifically:** Research confirms patchright is strong against DataDome and Cloudflare but does not independently verify against LinkedIn's specific 2026 detection stack. A validation spike (test real scraping session with patchright on LinkedIn) should precede Phase 2 implementation commitment.
- **WTTJ Algolia endpoint stability:** The Algolia internal search endpoint is not an official public API and could change without notice. Build a Playwright HTML fallback and design the scraper to switch automatically.
- **APEC authentication flow for apply:** APEC requires authentication for job applications; the exact apply form mechanism was not confirmed by research. Needs a manual session recording during Phase 6 planning.
- **EU AI Act high-risk classification applicability to personal-use agents:** The research flags this as a risk but the exact threshold for a personal single-user autonomous agent (vs an employer-facing system) is not definitively settled. Legal review in Phase 8 should confirm scope.
- **Gemini `2.5-flash` output quality for French prose:** The model upgrade is confirmed correct (deprecation), but the quality of French-language lettre de motivation generation at `temperature=0.3` has not been independently benchmarked. A prompt validation step in Phase 7 planning is recommended.

---

## Sources

### Primary (HIGH confidence)
- France Travail official API — `api.gouv.fr/les-api/api_offresdemplois`, `francetravail.io/data/api/offres-emploi` — REST, OAuth2, free, production-grade
- Google AI official docs — Gemini 1.5 deprecation, 2.5-flash recommendation (March 2026)
- python-telegram-bot official docs v22 — JobQueue, APScheduler integration, v22.7 release (March 16 2026)
- APScheduler official docs — AsyncIOScheduler + FastAPI lifespan pattern
- aiosqlite 0.22.1 — PyPI, December 2025 release confirmed
- qdrant-client 1.17.1 — PyPI, March 13 2026 release confirmed
- OpenClaw official docs — `docs.openclaw.ai/gateway/tools-invoke-http-api`, skills integration
- France Travail official guidance — lettre de motivation format, ADP France / France Travail.fr
- CNIL recommendations on AI systems — `cnil.fr/en/ai-system-development-cnils-recommendations-to-comply-gdpr`
- EU AI Act (in force February 2025) — high-risk AI classification for HR systems

### Secondary (MEDIUM confidence)
- patchright GitHub (`Kaliiiiiiiiii-Vinyzu/patchright`) — CDP leak patching mechanism, v1.58.2 current
- ZenRows patchright guide — detection capability vs DataDome/Cloudflare
- APEC Jobs Scraper — Apify actor confirming APEC is scrapable
- Welcome to the Jungle scraping — Mantiks blog, multiple Apify actors confirming viability
- LinkedIn automation safety guides 2025-2026 — Dux-Soup, Konnector, Bearconnect (practitioner sources; ~100-150 Easy Apply/day limit is estimate, not official)
- Cloudflare AI Labyrinth (March 2025) — multiple WebSearch sources confirming new defense defeating playwright-stealth
- LinkedIn URL normalisation dedup failures — n8n GitHub issues
- EDPB AI Guidelines April 2025 — GDPR Local
- LLM hallucination examples and prevention — EvidentlyAI

### Tertiary (LOW confidence / needs validation)
- WTTJ Algolia endpoint structure — inferred from DevTools observation patterns described in community sources; endpoint path and app ID need direct verification
- APEC internal JSON endpoint — mentioned in architecture research as possible alternative to Playwright; not confirmed by direct source; treat as Playwright-only until verified
- LinkedIn per-session Easy Apply limit (15-20 actions per session) — practitioner estimate; treat conservatively

---
*Research completed: 2026-03-23*
*Ready for roadmap: yes*
