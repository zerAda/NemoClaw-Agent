# NemoClaw Job Hunter

## What This Is

An autonomous job-hunting system powered by the NemoClaw Telegram agent. NemoClaw runs the full job search cycle end-to-end — scraping listings from French and international platforms, scoring fit, generating tailored cover letters and CVs, auto-applying, tracking responses, following up, and reporting everything back to the user via Telegram. The user interacts via Telegram and the agent does the rest.

## Core Value

NemoClaw must autonomously get the user to job interviews — from finding listings to submitted applications to tracked follow-ups — with zero manual effort required.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Scrape job listings from French platforms (Welcome to the Jungle, APEC, Pôle Emploi, Cadremploi) and global platforms (LinkedIn, Indeed, Glassdoor, company career pages, remote boards)
- [ ] Score each listing for fit against user's CV and target criteria (Gemini scoring, existing hunter.py logic)
- [ ] Generate tailored cover letters and CV edits per job (Gemini, existing tailor.py logic)
- [ ] Auto-apply to matching jobs across all supported platforms
- [ ] Deduplicate already-processed/applied jobs (Qdrant memory, existing memory.py logic)
- [ ] Track application status (applied, viewed, rejected, interview, offer)
- [ ] Auto-follow-up on applications with no response after configurable delay
- [ ] Report activity to user via Telegram (daily digest + real-time alerts for responses)
- [ ] Telegram command interface: trigger a search cycle, view pipeline, pause/resume
- [ ] Support full negotiation prep: provide salary benchmarks and talking points when offer received

### Out of Scope

- Manual application review per job before submission — user wants fully autonomous mode
- Web dashboard or email reporting — Telegram is the interface
- Non-tech job categories — focus is software/data/engineering roles in France

## Context

- **Existing career_agent/**: `career_agent/` (Project Phoenix) is already in this repo and implements scraping (Playwright + stealth), scoring (Gemini via OpenAI-compat API), cover letter generation, and Qdrant deduplication. This is the toolset NemoClaw will orchestrate.
- **NemoClaw bot**: The root `docker-compose.yml` runs `ghcr.io/openclaw/openclaw:latest` — a Telegram bot with Gemini inference, already deployed to VPS behind Traefik. Target identity/persona defined in `agent.md`.
- **Brain files**: `brain/Bio_Context.md` holds the candidate persona; `brain/Target_Specs.json` holds search criteria and scoring threshold (default 0.85).
- **CI/CD**: GitHub Actions pipeline (CI lint/SAST + CD to VPS via SSH). All new components must pass the existing gates.
- **Location**: User is in France — French job platforms are first-class targets alongside global boards.
- **Inference**: Gemini API via OpenAI-compatible layer, shared across career_agent and NemoClaw.

## Constraints

- **Tech stack**: Must extend the existing NemoClaw + career_agent codebase. No greenfield rewrites.
- **Agent runtime**: NemoClaw is the orchestrating agent — career tooling is invoked as capabilities.
- **Reporting channel**: Telegram only — no web UI, no email.
- **Deployment**: Must deploy via existing CD pipeline to VPS.
- **Stealth**: Scrapers must avoid bot detection (Playwright stealth already in place for LinkedIn).
- **French market**: French-language job listings and French application conventions (lettre de motivation format) must be supported.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| NemoClaw as orchestrating agent | User specified NemoClaw is the agent — keeps UX in Telegram, reuses existing bot | — Pending |
| Reuse career_agent/ as tool layer | Scraping, scoring, tailoring, memory already implemented — extend don't rewrite | — Pending |
| Fully autonomous apply (no approval gate) | User explicitly chose full autonomy — no confirmation before applications | — Pending |
| Gemini as LLM for scoring + generation | Already integrated in both NemoClaw and career_agent, API key provisioned | — Pending |

---
*Last updated: 2026-03-22 after initialization*
