import logging
import os
import uuid
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from datetime import datetime

logger = logging.getLogger(__name__)

class MemoryService:
    """Diamond Grade Memory: Persistent tracking with O(1) retrieval.
    
    Supports brain_path injection for multi-user/multi-brain isolation.
    """
    
    def __init__(self, brain_path: str = "", collection_name: str = "job_applications"):
        # EXPERT: Prefer injected path over global environment fallback
        brain = brain_path or os.environ.get("BRAIN_PATH", "/app/brain")
        self.client = QdrantClient(path=os.path.join(brain, "qdrant_db"))
        self.collection_name = collection_name
        self.namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8') # DNS Namespace
        self._ensure_collection()

    def _generate_uuid(self, job_url: str) -> str:
        """Deterministic UUIDv5 generation for URL-persistent identification."""
        return str(uuid.uuid5(self.namespace, job_url))

    def _ensure_collection(self) -> None:
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            
            if not exists:
                logger.info(f"Creating Diamond-Grade collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                )
        except Exception as e:
            logger.error(f"Failed to ensure Qdrant collection: {e}")

    def add_application(self, job_url: str, metadata: Dict) -> None:
        """Log a new application or update existing with persistent metadata."""
        job_id_uuid = self._generate_uuid(job_url)
        metadata["timestamp"] = datetime.now().isoformat()
        metadata["url"] = job_url
        
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=job_id_uuid,
                        vector=[0.0] * 384, # Structural foundation for RAG
                        payload=metadata
                    )
                ]
            )
            logger.info(f"Memory updated for: {metadata.get('title')} (ID: {job_id_uuid})")
        except Exception as e:
            logger.error(f"Failed to upsert memory for {job_id_uuid}: {e}")

    def is_already_processed(self, job_url: str) -> bool:
        """Diamond-Grade O(1) primary key retrieval check."""
        job_id_uuid = self._generate_uuid(job_url)
        try:
            # EXPERT: retrieve() is the fastest way to check existence by point ID
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[job_id_uuid],
                with_payload=False,
                with_vectors=False
            )
            return len(points) > 0
        except Exception as e:
            logger.warning(f"Qdrant retrieve failed for {job_id_uuid}: {e}. Falling back to scroll...")
            # Fallback to scroll if retrieve fails (e.g. storage inconsistency)
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter={"must": [{"key": "url", "match": {"value": job_url}}]},
                limit=1
            )
            return len(results[0]) > 0

    def get_stats(self) -> Dict:
        """Phase 4: Aggregate counts of job statuses for reporting."""
        try:
            # EXPERT: Aggregating counts via scroll (suitable for small/medium DBs)
            # In a production "Master" grade system, we might maintain counters in SQLite
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000, # Large batch for summarization
                with_payload=True,
                with_vectors=False
            )
            
            points = scroll_result[0]
            stats = {
                "total": len(points),
                "READY": 0,
                "SKIPPED": 0,
                "SCORED": 0,
                "ABANDONED": 0,
                "APPLIED": 0 # For future phases
            }
            
            for p in points:
                status = p.payload.get("status")
                if status in stats:
                    stats[status] += 1
            
            return stats
        except Exception as e:
            logger.error(f"Failed to fetch stats from Qdrant: {e}")
            return {"error": "Stats unavailable", "total": 0}
