# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repo has two independent components:

1. **NemoClaw deployment** — The root-level `docker-compose.yml` deploys the `ghcr.io/openclaw/openclaw:latest` pre-built image. It is a Telegram-based AI agent using Gemini as its inference backend, routed through an OpenAI-compatible API layer.

2. **Career Agent (Project Phoenix)** — A Python async sub-project in `career_agent/` that automates job hunting: LinkedIn scraping → Gemini scoring → cover letter generation → Qdrant memory tracking.

## Key Commands

### NemoClaw (Docker)
```bash
docker compose up -d              # start the agent
docker compose down               # stop
docker compose down -v            # stop and wipe volumes (full reset)
docker logs openclaw --tail=50    # check runtime logs
docker compose ps                 # verify container health
```

### Career Agent (Python)
```bash
# From repo root, activate venv first
source .venv/Scripts/activate     # Windows Git Bash

# Run the career agent cycle
python -m career_agent.src.app

# Lint
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# SAST scan
bandit -r . -f custom -ll -ii
```

## Architecture

### NemoClaw (Docker Compose)
- `docker-compose.yml` — Pulls the pre-built `openclaw` image. Configuration is purely via environment variables.
- `agent.md` — Injected into the container at `/app/agent.md` (read-only). Defines the agent's identity, personality, and guardrails.
- `brain/` — Mounted into the container at `/app/brain`. Holds persistent memory and data the agent reads/writes across restarts.
- The container exposes port `8080`, sits behind a Traefik reverse proxy on the `traefik-net` external Docker network, and serves `nemoclaw.resto-bot.com`.

### Career Agent (`career_agent/`)
- `src/app.py` (`PhoenixApp`) — Orchestrator. Runs `run_cycle()` which scrapes jobs, scores them, and generates artifacts in parallel (up to 5 concurrent jobs via `asyncio.gather`).
- `src/hunter.py` (`HunterService`) — Loads `brain/Bio_Context.md` + `brain/Target_Specs.json`, does a fast-fail exclusion check, then calls Gemini to produce a `MatchReport` (score 0–1, recommendation: APPLY/SKIP/TAILOR_REQUIRED).
- `src/tailor.py` (`TailorService`) — Calls `gemini-1.5-pro` to write a tailored cover letter as `TailoredContent` (subject, body, suggested_edits).
- `src/scraper.py` (`Scraper`) — Playwright + `playwright_stealth` headless browser. Selectors are externalized in `career_agent/config/selectors.yaml` so they can be updated without touching code.
- `src/memory.py` (`MemoryService`) — Local Qdrant vector DB at `./qdrant_db`. Uses UUIDv5 (URL-derived) as stable point IDs to deduplicate already-processed jobs.
- `src/client_factory.py` (`ClientFactory`) — Singleton that wraps Gemini behind an `AsyncOpenAI` client pointed at `https://generativelanguage.googleapis.com/v1beta/openai`. All services share one instance via `ai_factory`.

### Brain Data (`brain/`)
- `Bio_Context.md` — Candidate persona/skills/experience injected into LLM prompts. Fill in the `[PLACEHOLDER]` fields before use.
- `Target_Specs.json` — Job search criteria: target roles, location, salary, keywords, `scoring_threshold` (default 0.85). The `exclusions` array drives `HunterService._fast_fail_check()`.

## CI/CD

- **CI** (`nemoclaw-ci.yml`) — Runs on every push/PR to `master`. Steps: Flake8 lint → Bandit SAST → verify `.env.example` exists.
- **CD** (`nemoclaw-cd.yml`) — Triggers after CI passes. SSHes into VPS, SCPs the repo to `/opt/nemoclaw`, writes secrets to `.env`, recreates containers via `docker compose up -d --force-recreate`.

## Required Secrets / Environment

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Google Gemini inference (both NemoClaw container and Career Agent) |
| `TELEGRAM_BOT_TOKEN` | NemoClaw Telegram gateway |
| `NEMO_AUTH_USER_ID` | NemoClaw user whitelist |
| `NEMO_PAIRING_CODE` | NemoClaw pairing secret |
| `VPS_HOST` / `VPS_SSH_KEY` | CD deployment (GitHub vars/secrets) |

Copy `.env.example` to `.env` and populate before running locally.
