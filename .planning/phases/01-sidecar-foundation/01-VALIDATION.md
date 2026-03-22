---
phase: 1
slug: sidecar-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `career_agent/tests/conftest.py` (Wave 0 creates) |
| **Quick run command** | `pytest career_agent/tests/ -x -q` |
| **Full suite command** | `pytest career_agent/tests/ -v && flake8 career_agent/sidecar/ --max-line-length=127` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest career_agent/tests/ -x -q`
- **After every plan wave:** Run `pytest career_agent/tests/ -v && flake8 career_agent/sidecar/ --max-line-length=127`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | INFRA-01 | unit | `pytest career_agent/tests/test_sidecar.py -x -q` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | INFRA-06 | grep | `grep -r "gemini-2.5-flash" career_agent/ docker-compose.yml` | ✅ | ⬜ pending |
| 1-02-01 | 02 | 1 | INFRA-02 | manual | Docker exec + HTTP call | ✅ | ⬜ pending |
| 1-02-02 | 02 | 1 | INFRA-03 | integration | `pytest career_agent/tests/test_volume.py -x -q` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 2 | INFRA-04 | manual | Push to master, verify CD run | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `career_agent/tests/__init__.py` — test package marker
- [ ] `career_agent/tests/conftest.py` — shared fixtures (mock brain path, mock Gemini client)
- [ ] `career_agent/tests/test_sidecar.py` — stubs: test FastAPI app starts, /health returns 200, /run-cycle returns 202
- [ ] `career_agent/tests/test_volume.py` — stubs: test BRAIN_PATH env var is read, qdrant_db path resolves under BRAIN_PATH
- [ ] `career_agent/requirements.txt` — must exist with fastapi, uvicorn, pytest listed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| NemoClaw Telegram command invokes sidecar HTTP endpoint end-to-end | INFRA-02 | Requires live Docker network + running OpenClaw container | Send `/cycle` via Telegram, check sidecar logs for incoming HTTP request |
| Both containers share ./brain/ read/write | INFRA-03 | Requires running Docker Compose stack | Write test file in sidecar container at $BRAIN_PATH/test.txt, verify readable from openclaw container at /app/brain/test.txt |
| CI/CD deploys sidecar without manual steps | INFRA-04 | Requires push to master + live VPS | Push a trivial change, verify GitHub Actions deploys both containers and sidecar responds at VPS |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
