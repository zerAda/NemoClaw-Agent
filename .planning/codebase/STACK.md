# Technology Stack

**Analysis Date:** 2026-03-23

## Languages

**Primary:**
- Python 3.11+ - Career Agent async services (`career_agent/src/`)
- YAML - Selectors configuration (`career_agent/config/selectors.yaml`)
- Markdown - Agent identity and documentation (`agent.md`, `CLAUDE.md`)

**Secondary:**
- Shell/Bash - CI/CD workflows (`.github/workflows/`)
- Docker Compose - Infrastructure orchestration (`docker-compose.yml`)

## Runtime

**Environment:**
- Docker + Docker Compose - NemoClaw container orchestration
- Python 3.11 venv - Career Agent virtual environment at `.venv/`

**Package Manager:**
- pip - Python package management
- Lockfile: Not detected (no requirements.txt or pyproject.toml found)

## Frameworks

**Core:**
- OpenClaw - Pre-built AI agent framework (`ghcr.io/openclaw/openclaw:latest`)
- Pydantic 2.12.5 - Data validation and serialization models in `career_agent/src/`
- Playwright 1.58.0 - Headless browser automation for scraping in `career_agent/src/scraper.py`

**Async/Concurrency:**
- asyncio - Python standard async library used throughout Career Agent
- Playwright Stealth 2.0.2 - Anti-detection plugin for headless browser in `career_agent/src/scraper.py`

**Testing:**
- No testing framework detected

**Build/Dev:**
- Flake8 - Python linting in CI (`nemoclaw-ci.yml`)
- Bandit - SAST security scanning in CI (`nemoclaw-ci.yml`)
- Docker - Containerization and deployment

## Key Dependencies

**Critical:**
- openai (AsyncOpenAI) - OpenAI-compatible API client wrapping Google Gemini in `career_agent/src/client_factory.py`
- qdrant-client - Vector database for deduplication and memory in `career_agent/src/memory.py`
- pyyaml 6.0.3 - YAML parsing for selectors in `career_agent/src/scraper.py`

**Infrastructure:**
- Playwright 1.58.0 - Headless browser with JavaScript execution for LinkedIn scraping
- Traefik - Reverse proxy for NemoClaw container (external network `traefik-net` in `docker-compose.yml`)

## Configuration

**Environment:**
- `.env` file - Secrets management (template: `.env.example`)
- Docker environment variables injected via `docker-compose.yml` (lines 6-24)
- Brain data files in `brain/` directory mounted into NemoClaw container

**Key Configuration Files:**
- `docker-compose.yml` - NemoClaw container setup with Traefik labels, volumes, health checks, memory limits
- `career_agent/config/selectors.yaml` - Externalized CSS selectors for LinkedIn and Indeed scraping (lines 1-12)
- `brain/Target_Specs.json` - Job search criteria and scoring thresholds

**Build:**
- CI Pipeline: `.github/workflows/nemoclaw-ci.yml` (Flake8 lint, Bandit SAST, .env.example validation)
- CD Pipeline: `.github/workflows/nemoclaw-cd.yml` (SSH deployment, Docker Compose recreation)

## Platform Requirements

**Development:**
- Docker and Docker Compose
- Python 3.11+
- Git
- SSH client (for VPS deployment)

**Production:**
- Docker-enabled VPS
- Domain configured for Traefik reverse proxy (`nemoclaw.resto-bot.com`)
- External Traefik network (`traefik-net`) already configured on VPS
- Minimum 512M memory reservation, 2G limit per `docker-compose.yml` lines 40-44

---

*Stack analysis: 2026-03-23*
