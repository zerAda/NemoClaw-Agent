# Coding Conventions

**Analysis Date:** 2026-03-23

## Naming Patterns

**Files:**
- Snake case: `app.py`, `client_factory.py`, `hunter.py`, `tailor.py`, `scraper.py`, `memory.py`
- Descriptive, service-oriented names matching class names (e.g., `HunterService` in `hunter.py`)

**Functions:**
- Snake case: `_load_bio()`, `_fast_fail_check()`, `score_job()`, `customize_letter()`, `is_already_processed()`
- Private methods prefixed with single underscore: `_load_selectors()`, `_ensure_collection()`, `_human_scroll()`, `_generate_uuid()`
- Async functions use `async def`: `score_job()`, `customize_letter()`, `process_job()`, `run_cycle()`, `search_linkedin_jobs()`, `get_linkedin_job_description()`

**Variables:**
- Snake case for all variables: `brain_path`, `jd_text`, `match_report`, `job_id_uuid`, `job_cards`, `scraped_jobs`
- Type-hinted parameters and return types throughout
- Constants: `collection_name`, `headless`, `namespace` (DNS Namespace UUID in `memory.py`)

**Types & Classes:**
- PascalCase for classes: `PhoenixApp`, `HunterService`, `TailorService`, `MemoryService`, `Scraper`, `ClientFactory`, `MatchReport`, `TailoredContent`
- Pydantic models for structured data: `MatchReport`, `TailoredContent` with validation via `Field()`

## Code Style

**Formatting:**
- No enforced formatter detected. Code follows implicit PEP 8 style with:
  - 4-space indentation
  - Max line length approximately 100-120 characters (observed in CI config: `--max-line-length=127`)
  - Blank lines between class definitions and between methods

**Linting:**
- **Tool:** Flake8
- **Config location:** CI pipeline in `.github/workflows/nemoclaw-ci.yml`
- **Key rules enforced:**
  - E9 (runtime errors)
  - F63 (assertion tests)
  - F7 (syntax errors in type comments)
  - F82 (undefined names)
  - Max complexity: 10
  - Max line length: 127 characters

**SAST Security:**
- **Tool:** Bandit
- **Config:** Run with `-f custom -ll -ii` (low-level, level II severity and above)
- **Execution:** Part of CI pipeline (`.github/workflows/nemoclaw-ci.yml`)

## Import Organization

**Order:**
1. Standard library: `asyncio`, `os`, `json`, `logging`, `random`, `uuid`, `yaml`, `datetime`
2. Third-party: `pydantic`, `openai`, `playwright`, `qdrant_client`
3. Local imports: Relative imports from `.` (e.g., `from .hunter import HunterService`)

**Observed Pattern in Files:**
```python
# Standard library first
import asyncio
import os
import logging
from typing import List, Dict
from datetime import datetime

# Third-party
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from playwright.async_api import async_playwright

# Local
from .hunter import HunterService
from .client_factory import ai_factory
```

**Path Aliases:**
- Relative imports used throughout: `.hunter`, `.scraper`, `.client_factory`, etc.
- No absolute path aliases configured

## Error Handling

**Patterns:**
- Try/except blocks for critical operations:
  - `app.py` `process_job()`: Catches all exceptions with `except Exception as e`, logs error, continues
  - `scraper.py` `_load_selectors()`: Catches exceptions on YAML load, logs error, sets empty dict fallback
  - `client_factory.py`: Raises `ValueError` explicitly when `GEMINI_API_KEY` not found
- Validation errors: Pydantic `BaseModel` used for automatic validation in `MatchReport` and `TailoredContent`
- Early returns: `hunter.py` `score_job()` returns early if JD is empty or excluded

**Error Logging:**
- All errors logged with `logger.error()` or `logger.warning()` at module level
- Contextual information included: job title, URL, missing config path

## Logging

**Framework:** Python `logging` module

**Patterns:**
- **Setup:** Module-level logger creation: `logger = logging.getLogger(__name__)` or specific name like `"PhoenixApp"`
- **Configuration:** Centralized in `app.py`:
  ```python
  logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
  logger = logging.getLogger("PhoenixApp")
  ```
- **Levels:**
  - `logger.info()`: Normal operation, processing steps, completion (e.g., "Skipping already seen job", "MATCH FOUND")
  - `logger.warning()`: Recoverable issues (e.g., "Invalid JD content", "Empty or short JD received")
  - `logger.error()`: Exceptions and critical failures (e.g., "CRITICAL ERROR processing", "Failed to load selectors")
- **Logging points:**
  - Service initialization and configuration
  - Processing start/completion
  - Important decisions (fast-fail, skip vs. apply)
  - External API calls
  - Error conditions with context

## Comments

**When to Comment:**
- Descriptive docstrings for classes and public methods (observed in all service classes)
- Inline comments for non-obvious logic or external integration details
- Comments used sparingly; code is generally self-documenting via naming

**DocStrings (docstring pattern):**
- Single-line docstrings for classes: `"""Diamond Grade Hunter: Scoring with Gemini & Centralized Clients."""`
- Single-line docstrings for methods: `"""Standardized single-job processing atom with error isolation."""`
- No formal JSDoc/TSDoc (Python project)

## Function Design

**Size:**
- Functions range from 5-25 lines
- Single responsibility: scoring, tailoring, scraping, memory operations are separate services
- Async functions used for I/O-bound operations

**Parameters:**
- Type hints on all parameters: `job: Dict`, `brain_path: str`, `headless: bool = True`, `jd_text: str`
- Default parameters used: `location: str = "United States"`, `headless: bool = True`, `provider: str = "gemini"`
- Complex types wrapped in Pydantic models for validation

**Return Values:**
- Type-hinted returns: `-> str`, `-> Dict`, `-> MatchReport`, `-> TailoredContent`, `-> bool`
- Async functions return Coroutines: `async def` methods return awaitable types
- Early returns on validation failures common in processing pipelines

## Module Design

**Exports:**
- Services exported as classes meant for instantiation: `HunterService`, `TailorService`, `MemoryService`, `Scraper`
- Singleton pattern used for `ClientFactory` via `__new__` override
- Global instance created: `ai_factory = ClientFactory()` for shared Gemini client access

**Organization:**
- Each service is a standalone class in its own module
- Entry point `app.py` (`PhoenixApp`) orchestrates all services
- Factories and utilities (e.g., `client_factory.py`) used for initialization

**Configuration:**
- Configuration loaded from files: `Bio_Context.md`, `Target_Specs.json`, `selectors.yaml`
- Environment variables for secrets: `GEMINI_API_KEY` via `os.getenv()`
- Paths are relative to `brain_path` parameter passed to services

---

*Convention analysis: 2026-03-23*
