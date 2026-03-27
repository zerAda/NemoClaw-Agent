import os
import pytest
import tempfile
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def tmp_brain_path(tmp_path):
    """Temporary brain directory with required files."""
    brain = tmp_path / "brain"
    brain.mkdir(parents=True, exist_ok=True)
    (brain / "Bio_Context.md").write_text("Test candidate bio.")
    (brain / "Target_Specs.json").write_text(
        '{"target_roles": ["AI Engineer"], "exclusions": ["intern"], "scoring_threshold": 0.85}'
    )
    return str(brain)


@pytest.fixture
def mock_phoenix_app():
    """Mock PhoenixApp that avoids real Playwright/Qdrant/Gemini I/O."""
    mock = MagicMock()
    mock.run_cycle = AsyncMock(return_value=None)
    mock.memory = MagicMock()
    mock.memory.client = MagicMock()
    mock.memory.client.scroll = MagicMock(return_value=([], None))
    return mock
