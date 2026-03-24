import logging
import json
from datetime import datetime, timezone
from typing import Optional

class StructuredLogger(logging.LoggerAdapter):
    """Diamond Grade Logger Adapter for cycle-aware traceability."""
    
    def process(self, msg, kwargs):
        cycle_id = self.extra.get('cycle_id', 'SYSTEM')
        return f"[{cycle_id}] {msg}", kwargs

def get_logger(name: str, cycle_id: Optional[str] = None):
    logger = logging.getLogger(name)
    return StructuredLogger(logger, {"cycle_id": cycle_id or "SYSTEM"})

# Configure root logger for production
def configure_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
