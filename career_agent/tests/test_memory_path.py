"""Tests for MemoryService path resolution logic."""
import os
import pytest
from unittest.mock import patch, MagicMock

def test_memory_service_uses_injected_path(tmp_path):
    """MemoryService reads brain path from injected argument."""
    brain_dir = tmp_path / "brain"
    qdrant_target = os.path.join(str(brain_dir), "qdrant_db")
    
    with patch("src.memory.QdrantClient") as mock_client:
        m = mock_client.return_value
        m.get_collections.return_value = MagicMock(collections=[])
        # Expert: mock the new count() method
        m.count.return_value = MagicMock(count=0)
        
        from src.memory import MemoryService
        svc = MemoryService(brain_path=str(brain_dir))
        mock_client.assert_called_once_with(path=qdrant_target)

def test_memory_service_fallback_to_env(tmp_path):
    """MemoryService falls back to env if no brain_path is injected."""
    expected_path = os.path.join(str(tmp_path), "qdrant_db")
    
    with patch.dict(os.environ, {"BRAIN_PATH": str(tmp_path)}):
        with patch("src.memory.QdrantClient") as mock_client:
            m = mock_client.return_value
            m.get_collections.return_value = MagicMock(collections=[])
            # Expert: mock the new count() method
            m.count.return_value = MagicMock(count=0)
            
            from src.memory import MemoryService
            svc = MemoryService()
            mock_client.assert_called_once_with(path=expected_path)

