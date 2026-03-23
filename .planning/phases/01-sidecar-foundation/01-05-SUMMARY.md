---
phase: 01-sidecar-foundation
plan: 05
subsystem: infra
tags: [openclaw, skill, yaml, ci, fastapi, career-agent, agent-identity]

# Dependency graph
requires:
  - phase: 01-sidecar-foundation/01-03
    provides: career_agent/sidecar/main.py with /health and /run-cycle endpoints
  - phase: 01-sidecar-foundation/01-04
    provides: docker-compose.yml with career-agent service and skills volume mount
provides:
  - skills/career_agent/SKILL.md — OpenClaw skill definition for career agent HTTP integration
  - agent.md update — NemoClaw identity extended with career_agent skill reference
  - .github/workflows/nemoclaw-ci.yml update — CI installs career_agent deps before linting
affects:
  - NemoClaw runtime (reads SKILL.md to discover career_agent tool dispatch)
  - CI pipeline (flake8 now resolves all imports in sidecar/main.py)
  - CD deployment gate: Task 3 checkpoint gates INFRA-04 on VPS verification

# Tech tracking
tech-stack:
  added:
    - PyYAML (used in test_skill_md.py to validate SKILL.md schema)
  patterns:
    - OpenClaw SKILL.md schema: name, description, tools[] with name/description/method/url/parameters
    - TDD RED-GREEN cycle for YAML schema validation
    - CI dependency layering: install career_agent/requirements.txt alongside root requirements.txt

key-files:
  created:
    - skills/career_agent/SKILL.md
    - career_agent/tests/test_skill_md.py (activated from skip stubs)
  modified:
    - agent.md (Available Skills section appended)
    - .github/workflows/nemoclaw-ci.yml (career_agent/requirements.txt install added)

key-decisions:
  - "SKILL.md tools use career-agent:8001 Docker service DNS — matches docker-compose service name exactly"
  - "run_cycle marked keyword as required:true, location as required:false with default France"
  - "agent.md gets explicit when-to-use guidance and 202 async note to prevent NemoClaw from reporting cycle completion prematurely"
  - "CI fix adds one line after existing requirements.txt check — minimal, non-breaking change"

# Metrics
duration: 47min
completed: 2026-03-23
---

# Phase 01 Plan 05: SKILL.md Registration + CI Fix Summary

**OpenClaw skill definition (skills/career_agent/SKILL.md) registers career-agent HTTP endpoints with NemoClaw, agent.md updated with usage guidance, and CI fixed to install career_agent/requirements.txt before linting**

## Performance

- **Duration:** 47 min
- **Started:** 2026-03-23T10:21:21Z
- **Completed:** 2026-03-23T11:08:46Z
- **Tasks:** 2 of 3 complete (Task 3 is checkpoint:human-verify — awaiting VPS verification)
- **Files modified:** 4

## Accomplishments
- skills/career_agent/SKILL.md: valid YAML with run_cycle (POST) and health_check (GET) tools pointing to career-agent:8001
- 4 schema validation tests passing: valid YAML, top-level fields, tool required fields, correct URL DNS name
- agent.md extended with Available Skills section: career_agent with run_cycle/health_check, when-to-use guidance, and 202 async note
- nemoclaw-ci.yml: pip install career_agent/requirements.txt added so flake8 resolves all imports in sidecar/main.py without F821 errors
- Full test suite: 9 passed (test_sidecar: 3, test_memory_path: 2, test_skill_md: 4), 0 failed, 0 skipped

## Task Commits

Each task was committed atomically:

1. **Task 1: Create skills/career_agent/SKILL.md + activate tests (TDD)**
   - `c2c91c1` test(01-05): activate failing skill_md tests (RED)
   - `27049bc` feat(01-05): create skills/career_agent/SKILL.md (GREEN — 4 tests pass)

2. **Task 2: Update agent.md + fix CI** - `35e9eac` (feat)

3. **Task 3: CD verification checkpoint** — AWAITING human verification (see below)

## Files Created/Modified
- `skills/career_agent/SKILL.md` — OpenClaw skill: run_cycle POST /run-cycle + health_check GET /health
- `career_agent/tests/test_skill_md.py` — 4 real tests replacing skip stubs (TDD RED-GREEN)
- `agent.md` — Available Skills section appended with career_agent guidance
- `.github/workflows/nemoclaw-ci.yml` — career_agent/requirements.txt install step added

## Decisions Made
- SKILL.md `method` values use uppercase POST/GET to match OpenClaw schema expectation
- `run_cycle` parameters include explicit `required: true/false` and `default: France` for location
- agent.md note "returns 202 immediately" prevents NemoClaw from mis-reporting job cycle as complete
- CI line added after root requirements.txt check to preserve existing behavior while extending it

## Checkpoint Status

**Task 3 is a `checkpoint:human-verify` gate for INFRA-04.**

The automation tasks (1 and 2) are fully complete and committed. Task 3 gates INFRA-04 completion on actual VPS deployment verification:

1. Wait for CD workflow (nemoclaw-cd.yml) to pass after push to master
2. SSH into VPS: `docker ps --filter name=career-agent --format "table {{.Names}}\t{{.Status}}"`
3. Confirm `career-agent` shows `Up ... (healthy)`
4. Optional smoke: `curl -s http://localhost:8001/health` returns `{"status":"ok"}`
5. Send Telegram "run a health check on the career agent" and verify `docker logs career-agent --tail=20` shows `GET /health HTTP/1.1" 200`

Resume signals: "verified" | "cd-failed [error]" | "container-unhealthy [logs]" | "skill-not-loading [env/logs]"

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
Push commits to master to trigger CD workflow. Then follow Task 3 verification steps above.

## Next Phase Readiness
- Phase 01 fully complete once Task 3 checkpoint is verified
- All 9 tests pass, zero gemini-1.5-* strings in repo
- INFRA-04 deployment gate pending VPS confirmation

---
*Phase: 01-sidecar-foundation*
*Completed: 2026-03-23 (partial — checkpoint pending)*
