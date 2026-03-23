import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

from src.app import PhoenixApp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("SidecarAPI")

_phoenix: Optional[PhoenixApp] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _phoenix
    brain_path = os.environ.get("BRAIN_PATH", "/app/brain")
    logger.info(f"Initializing PhoenixApp with brain_path={brain_path}")
    _phoenix = PhoenixApp(brain_path=brain_path)
    logger.info("Career Agent sidecar ready")
    yield
    _phoenix = None


app = FastAPI(title="Career Agent Sidecar", version="1.0.0", lifespan=lifespan)


class CycleRequest(BaseModel):
    keyword: str = "AI Engineer"
    location: str = "France"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/run-cycle", status_code=202)
async def run_cycle(request: CycleRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        _phoenix.run_cycle,
        keyword=request.keyword,
        location=request.location,
    )
    return {"status": "accepted", "message": "Cycle started"}
