---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
stopped_at: Completed 01-sidecar-foundation/01-05-PLAN.md (checkpoint pending VPS verification)
last_updated: "2026-03-23T11:08:46.000Z"
progress:
  total_phases: 9
  completed_phases: 1
  total_plans: 5
  completed_plans: 5
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-23)

**Core value:** NemoClaw must autonomously get the user to job interviews — from finding listings to submitted applications to tracked follow-ups — with zero manual effort required.
**Current focus:** Phase 01 — sidecar-foundation

## Current Position

Phase: 01 (sidecar-foundation) — CHECKPOINT (awaiting VPS verification)
Plan: 5 of 5 (tasks 1-2 complete; task 3 = checkpoint:human-verify)

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: — min
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01-sidecar-foundation P03 | 9 | 2 tasks | 5 files |
| Phase 01-sidecar-foundation P02 | 4 | 2 tasks | 6 files |
| Phase 01-sidecar-foundation P01 | 9 | 2 tasks | 6 files |
| Phase 01-sidecar-foundation P04 | 48 | 2 tasks | 2 files |
| Phase 01-sidecar-foundation P05 | 47 | 2 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- NemoClaw as orchestrating agent: keeps UX in Telegram, reuses existing bot
- Reuse career_agent/ as tool layer: extend don't rewrite
- Fully autonomous apply (no approval gate): user chose full autonomy
- Gemini as LLM: already integrated in both components
- [Phase 01-sidecar-foundation]: BRAIN_PATH env var resolves Qdrant DB path; brain_path arg takes priority for test isolation; default /app/brain matches docker-compose volume mount
- [Phase 01-sidecar-foundation]: Pre-install patchright and python-telegram-bot in Phase 1 to avoid docker image rebuild cycles in Phases 2 and 4
- [Phase 01-sidecar-foundation]: Use pytest.mark.skip stubs (not empty files) so stub intent is clear and activation is a one-line change
- [Phase 01-sidecar-foundation P03]: Use `from src.app import PhoenixApp` (not career_agent.src) — container WORKDIR=/app makes sidecar/ and src/ siblings
- [Phase 01-sidecar-foundation P03]: Patch PhoenixApp class (not _phoenix instance) in test fixture to prevent lifespan from calling real constructor
- [Phase 01-sidecar-foundation P03]: career_agent/conftest.py adds sys.path entry and patches playwright_stealth v2 for stealth_async compat
- [Phase 01-sidecar-foundation]: TELEGRAM_CHAT_ID set from NEMO_AUTH_USER_ID (same Telegram user ID) to avoid Phase 4 redeploy
- [Phase 01-sidecar-foundation]: career-agent has no Traefik labels — internal service only, reachable via docker DNS career-agent:8001
- [Phase 01-sidecar-foundation P05]: SKILL.md tools use career-agent:8001 Docker DNS; run_cycle keyword required, location optional (default France)
- [Phase 01-sidecar-foundation P05]: agent.md 202 async note prevents NemoClaw from reporting cycle completion prematurely

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 2: patchright effectiveness against LinkedIn's 2026 detection stack is not independently verified — a validation spike is recommended before committing to implementation
- Phase 6: WTTJ Algolia endpoint app ID and query schema need direct verification during Phase 6 planning; APEC authentication flow for apply needs manual session recording
- Phase 8: LinkedIn Easy Apply selectors change frequently and need platform-specific investigation during planning; GDPR legal review is a hard milestone requiring legal input

## Session Continuity

Last session: 2026-03-23T11:08:46.000Z
Stopped at: Checkpoint reached in 01-sidecar-foundation/01-05-PLAN.md (Task 3: CD verification — awaiting VPS confirmation)
Resume file: None
