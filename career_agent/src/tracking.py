import aiosqlite
import os
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class TrackingService:
    """Diamond-Grade Relational State Machine.
    
    Manages job states and ensures cross-platform deduplication using content fingerprints.
    """
    
    def __init__(self, brain_path: str):
        self.db_path = os.path.join(brain_path, "tracking.db")
        self._initialized = False

    async def _ensure_db(self):
        """Lazy initialization of the SQLite schema."""
        if self._initialized:
            return
            
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id TEXT PRIMARY KEY,
                    fingerprint TEXT UNIQUE,
                    url TEXT,
                    title TEXT,
                    company TEXT,
                    status TEXT,
                    score REAL DEFAULT 0.0,
                    source TEXT,
                    timestamp TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT,
                    action TEXT,
                    details TEXT,
                    timestamp TEXT
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_fingerprint ON applications(fingerprint)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_audit_job ON audit_log(job_id)")
            await db.commit()
        
        self._initialized = True
        logger.info(f"Tracking DB Initialized at {self.db_path}")

    async def log_action(self, job_id: str, action: str, details: str = ""):
        """Phase 5: Append an action to the immutable audit log."""
        await self._ensure_db()
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO audit_log (job_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
                (job_id, action, details, now)
            )
            await db.commit()

    async def get_daily_count(self, source: str) -> int:
        """Get the number of APPLIED jobs today for a specific source."""
        await self._ensure_db()
        today = datetime.now().strftime("%Y-%m-%d")
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT count(*) FROM applications WHERE source = ? AND timestamp LIKE ? AND status = 'APPLIED'",
                (source, f"{today}%")
            ) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0

    @staticmethod
    def generate_fingerprint(title: str, company: str) -> str:
        """Normalized content fingerprint to detect same jobs on different platforms."""
        # EXPERT: Normalize strings (lowercase, strip, remove common noise)
        norm_title = "".join(filter(str.isalnum, title.lower()))
        norm_company = "".join(filter(str.isalnum, (company or "unknown").lower()))
        
        seed = f"{norm_title}|{norm_company}"
        return hashlib.sha256(seed.encode()).hexdigest()

    async def is_duplicate(self, fingerprint: str) -> bool:
        """Check if this specific job content has been seen before."""
        await self._ensure_db()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT 1 FROM applications WHERE fingerprint = ?", (fingerprint,)
            ) as cursor:
                return await cursor.fetchone() is not None

    async def upsert_application(self, job_id: str, fingerprint: str, status: str, 
                                 metadata: Dict, score: float = 0.0):
        """Update or insert application state with Diamond-Grade persistence."""
        await self._ensure_db()
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO applications (id, fingerprint, url, title, company, status, score, source, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status,
                    score=excluded.score,
                    timestamp=excluded.timestamp
            """, (
                job_id, 
                fingerprint, 
                metadata.get("url"), 
                metadata.get("title"), 
                metadata.get("company"), 
                status, 
                score, 
                metadata.get("source"),
                now
            ))
            await db.execute(
                "INSERT INTO audit_log (job_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
                (job_id, "STATUS_UPDATE", f"Status changed to {status}", now)
            )
            await db.commit()
        logger.info(f"Tracking UPSERT: {metadata.get('title')} -> {status}")

    async def get_ripe_for_followup(self, days: int = 10) -> List[Dict]:
        """Identify applications ready for a re-engagement follow-up."""
        await self._ensure_db()
        threshold = (datetime.now() - timedelta(days=days)).isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM applications WHERE status = 'APPLIED' AND timestamp < ?", 
                (threshold,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_stats(self) -> Dict:
        """Phase 5: Accurate relational stats for status reporting."""
        await self._ensure_db()
        stats = {"total": 0, "READY": 0, "SKIPPED": 0, "ABANDONED": 0, "SCORED": 0}
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT status, COUNT(*) FROM applications GROUP BY status") as cursor:
                async for row in cursor:
                    status, count = row
                    if status in stats:
                        stats[status] = count
                        stats["total"] += count
        return stats
