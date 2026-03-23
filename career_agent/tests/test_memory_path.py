import pytest


@pytest.mark.skip(reason="Plan 02 fixes MemoryService to accept brain_path")
def test_memory_service_uses_brain_path_env():
    """MemoryService reads BRAIN_PATH env var for qdrant_db location"""
    pass


@pytest.mark.skip(reason="Plan 02 fixes MemoryService to accept brain_path")
def test_memory_service_default_path_is_brain_subdir():
    """Without BRAIN_PATH env, MemoryService defaults to /app/brain/qdrant_db"""
    pass
