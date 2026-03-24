"""Tests for MemoryService path resolution logic."""
import os
import pytest
from unittest.mock import patch, MagicMock
from src.config import config

def test_memory_service_uses_config_path(tmp_path):
    """MemoryService reads brain path from ProjectConfig."""
    brain_dir = tmp_path / "brain"
    qdrant_target = str(brain_dir / "qdrant_db")
    
    with patch("src.memory.QdrantClient") as mock_client:
        m = mock_client.return_value
        m.get_collections.return_value = MagicMock(collections=[])
        # Expert: mock the new count() method
        m.count.return_value = MagicMock(count=0)
        
        from src.memory import MemoryService
        svc = MemoryService()
        mock_client.assert_called_once_with(path=qdrant_target)

def test_memory_service_fallback_to_env(tmp_path):
    """MemoryService falls back to env if config has no brain_path."""
    original_path = config.brain_path
    config.brain_path = None
    expected_path = str(tmp_path / "qdrant_db")
    
    try:
        with patch.dict(os.environ, {"BRAIN_PATH": str(tmp_path)}):
            with patch("src.memory.QdrantClient") as mock_client:
                m = mock_client.return_value
                m.get_collections.return_value = MagicMock(collections=[])
                # Expert: mock the new count() method
                m.count.return_value = MagicMock(count=0)
                
                from src.memory import MemoryService
                svc = MemoryService()
                mock_client.assert_called_once_with(path=expected_path)
    finally:
        config.brain_path = original_path
