---
phase: 2
slug: stealth-layer-and-scraping-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23.x |
| **Config file** | `career_agent/conftest.py` (root) + `career_agent/tests/conftest.py` |
| **Quick run command** | `cd career_agent && python -m pytest tests/test_scraper_ft.py tests/test_alerter.py -x -q` |
| **Full suite command** | `cd career_agent && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd career_agent && python -m pytest tests/test_scraper_ft.py tests/test_alerter.py -x -q`
- **After every plan wave:** Run `cd career_agent && python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-W0-models | W0 | 0 | INFRA-05, SCRAPE-01 | unit | `pytest tests/test_scraper_ft.py tests/test_scraper_li.py -x -q` | ❌ W0 | ⬜ pending |
| 2-W0-alerter | W0 | 0 | SCRAPE-05 | unit | `pytest tests/test_alerter.py -x -q` | ❌ W0 | ⬜ pending |
| 2-W0-ft-stubs | W0 | 0 | SCRAPE-01, SCRAPE-07 | unit stub | `pytest tests/test_scraper_ft.py -x -q` | ❌ W0 | ⬜ pending |
| 2-W0-li-stubs | W0 | 0 | INFRA-05, SCRAPE-04, SCRAPE-06 | unit stub | `pytest tests/test_scraper_li.py -x -q` | ❌ W0 | ⬜ pending |
| 2-infra05 | dep-swap | 1 | INFRA-05 | unit | `pytest tests/test_scraper_li.py::test_patchright_import tests/test_scraper_li.py::test_no_stealth_call -x` | ❌ W0 | ⬜ pending |
| 2-scrape01-auth | FT scraper | 1 | SCRAPE-01 | unit (respx) | `pytest tests/test_scraper_ft.py::test_token_request -x` | ❌ W0 | ⬜ pending |
| 2-scrape01-search | FT scraper | 1 | SCRAPE-01 | unit (respx) | `pytest tests/test_scraper_ft.py::test_search_returns_listings -x` | ❌ W0 | ⬜ pending |
| 2-scrape01-401 | FT scraper | 1 | SCRAPE-01 | unit (respx) | `pytest tests/test_scraper_ft.py::test_search_401_returns_empty -x` | ❌ W0 | ⬜ pending |
| 2-scrape04 | LI scraper | 2 | SCRAPE-04 | unit (route mock) | `pytest tests/test_scraper_li.py::test_linkedin_returns_listings -x` | ❌ W0 | ⬜ pending |
| 2-scrape05-format | alerter | 1 | SCRAPE-05 | unit (mock Bot) | `pytest tests/test_alerter.py::test_alert_message_format -x` | ❌ W0 | ⬜ pending |
| 2-scrape05-swallow | alerter | 1 | SCRAPE-05 | unit (mock Bot) | `pytest tests/test_alerter.py::test_alert_swallows_exception -x` | ❌ W0 | ⬜ pending |
| 2-scrape06 | LI scraper | 2 | SCRAPE-06 | unit (patchright mock) | `pytest tests/test_scraper_li.py::test_context_reuse -x` | ❌ W0 | ⬜ pending |
| 2-scrape07-delay | rate limits | 1 | SCRAPE-07 | unit (mock sleep) | `pytest tests/test_scraper_ft.py::test_human_delay_range -x` | ❌ W0 | ⬜ pending |
| 2-scrape07-config | rate limits | 1 | SCRAPE-07 | unit | `pytest tests/test_scraper_ft.py::test_rate_limits_from_specs -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `career_agent/src/models.py` — `JobListing` Pydantic model (needed by all scraper tests)
- [ ] `career_agent/src/alerter.py` — `AlertService` stub class (needed by test_alerter.py before implementation)
- [ ] `career_agent/tests/test_scraper_ft.py` — stubs for SCRAPE-01, SCRAPE-07 (France Travail unit tests with respx mock)
- [ ] `career_agent/tests/test_scraper_li.py` — stubs for INFRA-05, SCRAPE-04, SCRAPE-06 (LinkedIn unit tests with patchright route mock)
- [ ] `career_agent/tests/test_alerter.py` — stubs for SCRAPE-05 (AlertService unit tests with mock Bot)
- [ ] `career_agent/requirements.txt` updated: add `patchright==1.58.2`, `python-telegram-bot==22.7`, `respx>=0.22.0`; remove `playwright-stealth==2.0.2`
- [ ] `career_agent/conftest.py` — remove playwright_stealth shim (migration landmine; must be removed together with INFRA-05 implementation)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LinkedIn public search returns real listings without bot block | SCRAPE-04 | Requires live LinkedIn; can't be mocked reliably | Run `python -m career_agent.src.app` and check logs for LinkedIn results; confirm > 0 listings returned |
| France Travail API returns real listings for configured keywords | SCRAPE-01 | Requires valid FRANCE_TRAVAIL_CLIENT_ID/SECRET credentials | Run cycle with valid creds; confirm listings in output |
| Telegram alert delivered when 0 results | SCRAPE-05 | Requires live Telegram Bot and user chat | Manually trigger empty return scenario; verify message received |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
