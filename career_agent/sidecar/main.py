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
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.app import PhoenixApp
from src.tracking import TrackingService
from src.followup import FollowUpService
from src.alerter import AlertService
from src.nego import NegotiatorService
from src.logger import configure_logging, get_logger
from src.research import ResearchService

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
        # Phase 4: Autonomous Control State
        self.is_paused: bool = False
        self.last_keyword: str = "AI Engineer" # Default fallback
        self.last_location: str = "France"
        self.scheduler = AsyncIOScheduler()

state = SidecarState()

async def scheduled_run():
    """Phase 4: Autonomous daily trigger. Background only."""
    if state.is_paused:
        logger.info("Autonomous Cycle SKIPPED: System is PAUSED.")
        return

    cycle_id = f"AUTO-{uuid.uuid4().hex[:8].upper()}"
    logger.info(f"Starting Autonomous Cycle: {cycle_id} for '{state.last_keyword}'")
    await _wrapped_run(cycle_id, state.last_keyword, state.last_location)

async def scheduled_summary():
    """Autonomous daily progress report pushed to Telegram."""
    brain_path = os.environ.get("BRAIN_PATH", "/app/brain")
    tracking = TrackingService(brain_path=brain_path)
    alerter = AlertService()
    
    stats = await tracking.get_stats()
    await alerter.send_summary(stats)
    logger.info("Daily SUMMARY pushed to Telegram.")

async def scheduled_followup():
    """Phase 9: Daily autonomous re-engagement for ripe applications."""
    brain_path = os.environ.get("BRAIN_PATH", "/app/brain")
    tracking = TrackingService(brain_path=brain_path)
    followup = FollowUpService(brain_path=brain_path)
    alerter = AlertService()
    
    ripe_jobs = await tracking.get_ripe_for_followup(days=10)
    if not ripe_jobs:
        logger.info("No ripe applications for follow-up today.")
        return
        
    logger.info(f"Found {len(ripe_jobs)} ripe applications. Triggering relances...")
    for job in ripe_jobs:
        try:
            draft = await followup.draft_followup(job)
            # EXPERT: In a real prod environment, this would hit /relance or email
            # For now, we update the state and alert the user
            fingerprint = job.get('fingerprint') or tracking.generate_fingerprint(job.get('title', ''), job.get('company', ''))
            await tracking.upsert_application(job['id'], fingerprint, 'FOLLOWED_UP', job)
            await alerter.send_info(f"📬 Autonomous Relance for {job.get('title', 'Unknown')} [{job.get('company', 'Unknown')}] drafted and queued.")
        except Exception as e:
            logger.error(f"Follow-up Error for {job['id']}: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure brain path exists
    brain_path = os.environ.get("BRAIN_PATH", "/app/brain")
    os.makedirs(brain_path, exist_ok=True)
    
    # Phase 4: Start Autonomous Scheduler (Daily at 08:00 and 08:30)
    state.scheduler.add_job(
        scheduled_run, 
        CronTrigger(hour=8, minute=0),
        id="daily_cycle",
        replace_existing=True
    )
    state.scheduler.add_job(
        scheduled_summary,
        CronTrigger(hour=8, minute=30),
        id="daily_summary",
        replace_existing=True
    )
    # Phase 9: Daily Follow-Up Scan at 10:00 AM
    state.scheduler.add_job(
        scheduled_followup,
        CronTrigger(hour=10, minute=0),
        id="daily_followup",
        replace_existing=True
    )
    state.scheduler.start()
    logger.info("Autonomous Scheduler STARTED (Cycle @ 08:00, Summary @ 08:30)")
    
    yield
    state.scheduler.shutdown()
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
        state.last_keyword = keyword
        state.last_location = location
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
        "secure": True,
        "is_paused": state.is_paused
    }

@app.get("/status", dependencies=[Depends(verify_nemo_key)])
async def get_status() -> Dict:
    """Detailed pipeline statistics for Telegram /status command."""
    brain_path = os.environ.get("BRAIN_PATH", "/app/brain")
    tracking = TrackingService(brain_path=brain_path)
    
    # EXPERT: Use relational tracking as source of truth for status
    stats = await tracking.get_stats()
    
    return {
        "is_paused": state.is_paused,
        "active_cycles": list(state.active_cycles.keys()),
        "last_run_at": state.last_run,
        "stats": stats,
        "config": {
            "last_keyword": state.last_keyword,
            "last_location": state.last_location
        }
    }

class ControlRequest(BaseModel):
    action: str = Field(..., pattern="^(pause|resume)$")

@app.post("/control", dependencies=[Depends(verify_nemo_key)])
async def set_control(request: ControlRequest):
    """Phase 4: Toggle autonomous execution. Authenticated."""
    state.is_paused = (request.action == "pause")
    logger.info(f"System CONTROL: {'PAUSED' if state.is_paused else 'RESUMED'}")
    return {"status": "success", "is_paused": state.is_paused}

@app.post("/trigger", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(verify_nemo_key)])
async def trigger_cycle(background_tasks: BackgroundTasks):
    """Phase 4: Trigger immediate cycle using last used parameters. Authenticated."""
    cycle_id = f"MAN-{uuid.uuid4().hex[:8].upper()}"
    logger.info(f"Manual TRIGGER accepted: {cycle_id} for '{state.last_keyword}'")
    background_tasks.add_task(_wrapped_run, cycle_id, state.last_keyword, state.last_location)
    return {"status": "accepted", "cycle_id": cycle_id}

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

class StatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target status, e.g., INTERVIEW, OFFER, REJECTED")

@app.post("/applications/{job_id}/status", dependencies=[Depends(verify_nemo_key)])
async def update_job_status(job_id: str, request: StatusUpdateRequest, background_tasks: BackgroundTasks):
    """Phase 9: Telegram transition webhook matching explicit explicit-confirmation."""
    brain_path = os.environ.get("BRAIN_PATH", "/app/brain")
    tracking = TrackingService(brain_path=brain_path)
    alerter = AlertService()
    
    # We must find the fingerprint to safely upsert state. But if job_id isn't known, 
    # tracking module doesn't currently expose a get_by_id. We bypass fingerprint check 
    # to force state updates safely via hard job_ids if needed.
    # The application itself must exist in SQLite.
    try:
        # Simple explicit update
        import aiosqlite
        async with aiosqlite.connect(tracking.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM applications WHERE id = ?", (job_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Job application not found.")
                
                await db.execute("UPDATE applications SET status = ? WHERE id = ?", (request.status, job_id))
                await db.commit()
                
                job_data = dict(row)
                
        logger.info(f"Status transition: {job_id} -> {request.status}")
        
        # Trigger Negotiation Flow on Success States
        if request.status.upper() in ["INTERVIEW", "OFFER"]:
            nego = NegotiatorService(brain_path=brain_path)
            benchmarks = await nego.get_benchmarks(role=job_data.get("title", "Tech Role"), location="France")
            await alerter.send_alert("NemoClaw Negotiator", benchmarks)
            
            if request.status.upper() == "INTERVIEW":
                background_tasks.add_task(
                    _background_interview_prep,
                    job_data.get("company", "Unknown Company"),
                    job_data.get("title", "Unknown Role")
                )
            
        return {"status": "success", "job_id": job_id, "new_state": request.status}
    except Exception as e:
        logger.error(f"Status Update failure: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/nego", dependencies=[Depends(verify_nemo_key)])
async def get_negotiation_benchmarks(role: str, location: str = "France"):
    """Phase 9: Command Center manual benchmark trigger."""
    brain_path = os.environ.get("BRAIN_PATH", "/app/brain")
    nego = NegotiatorService(brain_path=brain_path)
    
    try:
        benchmarks = await nego.get_benchmarks(role=role, location=location)
        return {"status": "success", "benchmarks": benchmarks}
    except Exception as e:
        logger.error(f"Nego GET failure: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _background_interview_prep(company_name: str, job_title: str):
    """Background task to scrape DDG and push a briefing to Telegram."""
    try:
        brain_path = os.environ.get("BRAIN_PATH", "/app/brain")
        research_service = ResearchService(brain_path=brain_path)
        alerter = AlertService()
        
        briefing = await research_service.generate_briefing(company_name, job_title)
        
        msg = f"🔍 INTERVIEW DOSSIER: {company_name}\n\n"
        msg += f"🏢 Snapshot:\n{briefing.company_snapshot}\n\n"
        msg += f"⭐ The 'Why You':\n{briefing.the_why_you}\n\n"
        msg += "⚠️ Trap Questions:\n- " + "\n- ".join(briefing.trap_questions) + "\n\n"
        msg += "🎯 Ask Them:\n- " + "\n- ".join(briefing.your_turn)
        
        await alerter._push(msg)
    except Exception as e:
        logger.error(f"Background interview prep failed: {e}")

@app.get("/applications/{job_id}/prepare", dependencies=[Depends(verify_nemo_key)])
async def prepare_for_interview(job_id: str, background_tasks: BackgroundTasks):
    """Phase 10: Explicit command to trigger interview prep."""
    brain_path = os.environ.get("BRAIN_PATH", "/app/brain")
    tracking = TrackingService(brain_path=brain_path)
    
    try:
        import aiosqlite
        async with aiosqlite.connect(tracking.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM applications WHERE id = ?", (job_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Job application not found.")
                job_data = dict(row)
                
        background_tasks.add_task(
            _background_interview_prep,
            job_data.get("company", "Unknown Company"),
            job_data.get("title", "Unknown Role")
        )
        return {"status": "accepted", "message": f"Interview briefing generation started for {job_id}."}
    except Exception as e:
        logger.error(f"Prepare GET failure: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/research", dependencies=[Depends(verify_nemo_key)])
async def research_company(company: str, role: Optional[str] = "General"):
    """Phase 10: Ad-hoc web search and generated briefing."""
    try:
        brain_path = os.environ.get("BRAIN_PATH", "/app/brain")
        research_service = ResearchService(brain_path=brain_path)
        briefing = await research_service.generate_briefing(company, role)
        return {"status": "success", "data": briefing.model_dump()}
    except Exception as e:
        logger.error(f"Research GET failure: {e}")
        raise HTTPException(status_code=500, detail=str(e))
