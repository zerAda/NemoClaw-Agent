import os
import pytest
from unittest.mock import patch, MagicMock


def test_memory_service_uses_brain_path_env(tmp_path):
    """MemoryService reads BRAIN_PATH env var for qdrant_db location."""
    expected_path = str(tmp_path / "qdrant_db")
    with patch.dict(os.environ, {"BRAIN_PATH": str(tmp_path)}):
        with patch("career_agent.src.memory.QdrantClient") as mock_client:
            mock_client.return_value = MagicMock()
            mock_client.return_value.get_collections.return_value = MagicMock(collections=[])
            import career_agent.src.memory as mem_module
            # Force re-init by instantiating directly
            svc = mem_module.MemoryService.__new__(mem_module.MemoryService)
            svc.__init__()
            mock_client.assert_called_once_with(path=expected_path)


def test_memory_service_default_path_is_brain_subdir():
    """Without BRAIN_PATH, MemoryService defaults to /app/brain/qdrant_db."""
    env_copy = {k: v for k, v in os.environ.items() if k != "BRAIN_PATH"}
    with patch.dict(os.environ, env_copy, clear=True):
        with patch("career_agent.src.memory.QdrantClient") as mock_client:
            mock_client.return_value = MagicMock()
            mock_client.return_value.get_collections.return_value = MagicMock(collections=[])
            import career_agent.src.memory as mem_module
            svc = mem_module.MemoryService.__new__(mem_module.MemoryService)
            svc.__init__()
            call_args = mock_client.call_args
            assert call_args[1]["path"].endswith("qdrant_db")
            assert "brain" in call_args[1]["path"]
