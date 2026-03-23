---
phase: 01-sidecar-foundation
plan: "04"
subsystem: infra
tags: [docker-compose, career-agent, sidecar, brain-volume, env-config]
dependency_graph:
  requires: [01-02, 01-03]
  provides: [INFRA-03]
  affects: [docker-compose.yml, .env.example]
tech_stack:
  added: []
  patterns:
    - "Two-service docker-compose with shared host volume mount"
    - "Internal-only service — no Traefik labels, only traefik-net for docker DNS"
    - "BRAIN_PATH env var controls brain directory in all services"
key_files:
  created: []
  modified:
    - docker-compose.yml
    - .env.example
decisions:
  - "TELEGRAM_CHAT_ID set from NEMO_AUTH_USER_ID (same Telegram numeric user ID) to avoid Phase 4 redeploy"
  - "No depends_on on career-agent to avoid service_healthy startup issues"
  - "career-agent has no Traefik labels — internal service only, reachable via docker DNS career-agent:8001"
  - "skills volume mounted read-only (./skills:/app/skills:ro) — agent only reads, never writes skill definitions"
metrics:
  duration_min: 48
  completed_date: "2026-03-23"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 01 Plan 04: Docker Compose Two-Service Sidecar Setup Summary

**One-liner:** Extended docker-compose.yml with career-agent sidecar sharing ./brain volume on traefik-net, plus complete .env.example template with all 6 required variables.

## What Was Built

- `docker-compose.yml` updated with two sets of changes:
  1. Added `./skills:/app/skills:ro` volume mount and `OPENCLAW_SKILLS_PATH=/app/skills` env var to the existing nemoclaw service
  2. Appended complete `career-agent` service block building from `./career_agent`, with `./brain:/app/brain` volume, traefik-net network membership, BRAIN_PATH env, and healthcheck on port 8001

- `.env.example` replaced from a 3-line stub to a complete template documenting all 4 required secrets (GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, NEMO_AUTH_USER_ID, NEMO_PAIRING_CODE) plus VPS deployment variables and legacy compatibility entries

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add career-agent service and skills volume | f245c11 | docker-compose.yml |
| 2 | Update .env.example with all required variables | 529caf3 | .env.example |

## Verification Results

- `grep "career-agent:" docker-compose.yml` — PASS (service definition present)
- `grep "build: ./career_agent" docker-compose.yml` — PASS
- `grep "./brain:/app/brain" docker-compose.yml` — PASS (2 matches: nemoclaw + career-agent)
- `grep "BRAIN_PATH=/app/brain" docker-compose.yml` — PASS
- `grep -c "traefik-net" docker-compose.yml` — PASS (3 matches)
- `grep "traefik.enable" docker-compose.yml | grep "career-agent"` — PASS (0 matches — no public exposure)
- `grep "MODEL_ID=gemini-2.5-flash" docker-compose.yml` — PASS (Plan 02 model upgrade intact)
- `grep "skills:/app/skills" docker-compose.yml` — PASS
- `grep "OPENCLAW_SKILLS_PATH=/app/skills" docker-compose.yml` — PASS
- `grep -c "GEMINI_API_KEY|TELEGRAM_BOT_TOKEN|NEMO_AUTH_USER_ID|NEMO_PAIRING_CODE" .env.example` — PASS (4)
- `python -m pytest career_agent/tests/ -x -q` — PASS (9/9 tests)

## Deviations from Plan

### Out-of-Scope Pre-existing Issue (Not Fixed)

**[Pre-existing from Plan 03] /brain" pattern in career_agent source**
- **Found during:** Task 1 acceptance criteria check
- **Issue:** `grep -r '/brain"' career_agent/src/ career_agent/sidecar/` returns 3 matches instead of 0:
  - `career_agent/sidecar/main.py:31` — `os.environ.get("BRAIN_PATH", "/app/brain")` (correct default)
  - `career_agent/src/memory.py:17` — `os.environ.get("BRAIN_PATH", "/app/brain")` (correct default)
  - `career_agent/src/app.py:79` — `brain_path = "./brain"` (CLI entry point local dev path)
- **Assessment:** The sidecar and memory.py occurrences are correct patterns (env var with fallback). The app.py `./brain` is the CLI `main()` function for local dev. All container paths use BRAIN_PATH env var properly.
- **Action:** Deferred — pre-existing condition from Plan 03, not introduced by Plan 04 changes, and all container runtime paths correctly use BRAIN_PATH.

## Self-Check: PASSED

- docker-compose.yml exists and contains career-agent service — CONFIRMED
- .env.example exists with all 4 required variables — CONFIRMED
- Task 1 commit f245c11 exists — CONFIRMED
- Task 2 commit 529caf3 exists — CONFIRMED
- pytest 9/9 pass — CONFIRMED
