"""
Career Agent sidecar — Elite-Grade FastAPI boundary for PhoenixApp.
Diamond Grade Security: Authenticated orchestration.
"""
import os
import uuid
import logging
import traceback
from contextlib import asynccontextmanager
from typing import Optional, Dict
from datetime import datetime, timezone

from fastapi import FastAPI, BackgroundTasks, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from src.app import PhoenixApp
from src.logger import configure_logging, get_logger

# Initialize root logging
configure_logging()
logger = get_logger("SidecarAPI")

# Diamond Security: API Key Verification
security = HTTPBearer()

def verify_nemo_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Expert: Verify X-Nemo-Key against environment secret."""
    expected = os.getenv("NEMO_API_KEY")
    # If no key is set in ENV, we block everything to be safe
    if not expected:
        logger.critical("NEMO_API_KEY is NOT set in environment. Blocking all requests.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server security misconfiguration."
        )
    if credentials.credentials != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key."
        )
    return True

class SidecarState:
    """Shared state for the API boundary with Diamond-Grade observability."""
    def __init__(self):
        self.active_cycles: Dict[str, str] = {} # cycle_id -> keyword
        self.last_run: Optional[str] = None
        self.last_error: Optional[str] = None
        self.last_run_id: Optional[str] = None

state = SidecarState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure brain path exists
    brain_path = os.environ.get("BRAIN_PATH", "/app/brain")
    os.makedirs(brain_path, exist_ok=True)
    yield
    state.active_cycles.clear()

app = FastAPI(
    title="Career Agent Sidecar",
    description="Diamond Orchestrator for Project Phoenix",
    version="1.4.0",
    lifespan=lifespan
)

class ScrapeRequest(BaseModel):
    """Validated scraping request with optional trace ID."""
    keyword: str = Field(..., min_length=2, max_length=100)
    location: str = Field("France", min_length=2, max_length=100)
    cycle_id: Optional[str] = Field(None, description="Optional custom correlation ID")

async def _wrapped_run(cycle_id: str, keyword: str, location: str):
    """Execution wrapper with logging context and Diamond-Grade error capture."""
    # EXPERT: Use brain_path from env or default
    brain_path = os.environ.get("BRAIN_PATH", "/app/brain")
    state.active_cycles[cycle_id] = keyword
    state.last_run_id = cycle_id
    
    try:
        phoenix = PhoenixApp(brain_path=brain_path, cycle_id=cycle_id)
        await phoenix.run_cycle(keyword, location)
        state.last_error = None
    except Exception as e:
        error_msg = f"Cycle {cycle_id} CRASHED: {type(e).__name__}: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        state.last_error = error_msg
    finally:
        state.active_cycles.pop(cycle_id, None)
        state.last_run = datetime.now(timezone.utc).isoformat()

@app.get("/health")
async def health() -> Dict:
    """Standard health endpoint with Diamond-Grade status reporting."""
    return {
        "status": "ok",
        "active_cycles": len(state.active_cycles),
        "last_run": state.last_run,
        "last_run_id": state.last_run_id,
        "last_error": state.last_error[-500:] if state.last_error else None,
        "mode": "DIAMOND",
        "secure": True
    }

@app.post("/run-cycle", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(verify_nemo_key)])
async def run_cycle(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """Trigger a cycle with full traceability. Authenticated."""
    cycle_id = request.cycle_id or f"CYC-{uuid.uuid4().hex[:8].upper()}"
    
    if len(state.active_cycles) >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="System-wide cycle limit reached (3 max). Please wait."
        )

    logger.info(f"Accepted Authenticated Cycle: {cycle_id} for '{request.keyword}'")
    background_tasks.add_task(_wrapped_run, cycle_id, request.keyword, request.location)
    
    return {
        "status": "accepted",
        "cycle_id": cycle_id,
        "message": f"Cycle {cycle_id} initiated."
    }
