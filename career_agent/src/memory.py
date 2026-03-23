import logging
import os
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

class MemoryService:
    """The Memory module: Persistent tracking using Qdrant."""
    
    def __init__(self, collection_name: str = "job_applications", brain_path: str = None):
        # Resolve brain path from argument, env var, or container default
        _brain = brain_path or os.environ.get("BRAIN_PATH", "/app/brain")
        self.client = QdrantClient(path=os.path.join(_brain, "qdrant_db"))
        self.collection_name = collection_name
        self.namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8') # DNS Namespace
        self._ensure_collection()

    def _generate_uuid(self, job_url: str) -> str:
        """Expose UUIDv5 generation for URL-persistent identification."""
        return str(uuid.uuid5(self.namespace, job_url))

    def _ensure_collection(self):
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if not exists:
            logger.info(f"Creating Qdrant collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )

    def add_application(self, job_url: str, metadata: Dict):
        """Log a new application attempt using a persistent UUIDv5 based on URL."""
        job_id_uuid = str(uuid.uuid5(self.namespace, job_url))
        metadata["timestamp"] = datetime.now().isoformat()
        metadata["url"] = job_url
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=job_id_uuid,
                    vector=[0.0] * 384, # Placeholder
                    payload=metadata
                )
            ]
        )
        logger.info(f"Memory updated for Job: {metadata.get('title')} (ID: {job_id_uuid})")

    def is_already_processed(self, job_url: str) -> bool:
        """Check if we have seen this URL before."""
        results = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter={"must": [{"key": "url", "match": {"value": job_url}}]},
            limit=1
        )
        return len(results[0]) > 0

if __name__ == "__main__":
    # Test stub
    pass
