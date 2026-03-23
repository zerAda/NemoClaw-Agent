"""
Root conftest for career_agent test suite.

Adds career_agent/ to sys.path so that `from src.app import PhoenixApp`
resolves correctly when sidecar/main.py is imported during tests.
Also patches playwright_stealth to expose stealth_async (v2.x renamed it to stealth).
"""
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Make career_agent/ a path root so sidecar/main.py can do `from src.app import PhoenixApp`
_career_agent_dir = os.path.dirname(__file__)
if _career_agent_dir not in sys.path:
    sys.path.insert(0, _career_agent_dir)

# playwright_stealth v2.x removed stealth_async — patch it back in before any src import
import playwright_stealth as _ps
if not hasattr(_ps, "stealth_async"):
    _ps.stealth_async = AsyncMock(return_value=None)

# Also patch at the module attribute level for direct `from playwright_stealth import stealth_async`
import playwright_stealth.stealth as _ps_stealth
if not hasattr(_ps_stealth, "stealth_async"):
    _ps_stealth.stealth_async = AsyncMock(return_value=None)
