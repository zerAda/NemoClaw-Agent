"""Shared test configuration and fixtures."""
import pytest
import os
import sys
from src.config import config

# Add the project root to sys.path for absolute imports in tests
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

@pytest.fixture
def tmp_brain_path(tmp_path):
    """Temporary brain directory with required files."""
    brain = tmp_path / "brain"
    brain.mkdir(exist_ok=True)
    (brain / "Bio_Context.md").write_text("Test candidate bio.")
    (brain / "Target_Specs.json").write_text(
        '{"target_roles": ["AI Engineer"], "exclusions": ["intern"], "scoring_threshold": 0.85}'
    )
    return str(brain)

@pytest.fixture(autouse=True)
def setup_test_config(tmp_path):
    """Automatically initialize ProjectConfig for every test using a temp brain."""
    brain_dir = tmp_path / "brain"
    brain_dir.mkdir(exist_ok=True)
    
    # Create required files for config to load without error logs
    if not (brain_dir / "Bio_Context.md").exists():
        (brain_dir / "Bio_Context.md").write_text("# Test Bio")
    if not (brain_dir / "Target_Specs.json").exists():
        (brain_dir / "Target_Specs.json").write_text("{}")
    
    config.initialize(brain_path=str(brain_dir))
    yield config
    config._initialized = False
