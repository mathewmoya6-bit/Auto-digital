"""
app/api/v1/scraper.py
========================
Endpoints (mounted by main.py at {api_prefix}/scraper):
    POST /run       - generic dispatch: body picks the source
    POST /autochek  - dedicated trigger for the AutoChek scraper
    POST /jiji      - dedicated trigger for the Jiji scraper
    POST /carapi    - dedicated trigger for the CarAPI reference-data sync
    GET  /status    - recent run history from the scraper_logs table

All triggers run as FastAPI BackgroundTasks (fire-and-forget from the
caller's perspective) since scraping 100-300 listings can take minutes -
far past any reasonable HTTP timeout. Swap for a real task queue
(Celery/RQ) if traffic grows past what one Render web dyno can handle;
scrapers/worker.py's run_job() was written queue-agnostic for exactly
that migration path.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel

from app.core.database import supabase
from scrapers.worker import run_job
from services.scraper_logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ScraperRunRequest(BaseModel):
    scraper: str  # "autochek" | "jiji" | "carapi"
    max_listings: int = 100
    kwargs: dict = {}


class AutochekRunRequest(BaseModel):
    country: str = "ke"
    max_listings: int = 100


class JijiRunRequest(BaseModel):
    category_path: str = "/cars"
    location: Optional[str] = None
    max_listings: int = 150


class CarApiRunRequest(BaseModel):
    years: list[int] = []
    makes: Optional[list[str]] = None


def _run_in_background(background_tasks: BackgroundTasks, job: dict) -> str:
    run_id = str(uuid.uuid4())

    def _run():
        logger.info("Background scraper run %s starting: %s", run_id, job)
        result = run_job(job)
        logger.info("Background scraper run %s finished: %s", run_id, result)

    background_tasks.add_task(_run)
    return run_id


@router.post("/run")
def trigger_run(payload: ScraperRunRequest, background_tasks: BackgroundTasks):
    """Generic dispatch - equivalent to calling one of the dedicated
    /autochek, /jiji, /carapi endpoints below, but source-agnostic for
    callers that just want to pass a source string (e.g. a scheduler)."""
    job = {"scraper": payload.scraper, "max_listings": payload.max_listings, "kwargs": payload.kwargs}
    run_id = _run_in_background(background_tasks, job)
    return {"run_id": run_id, "status": "started", "job": job}


@router.post("/autochek")
def trigger_autochek(payload: AutochekRunRequest, background_tasks: BackgroundTasks):
    job = {
        "scraper": "autochek",
        "max_listings": payload.max_listings,
        "kwargs": {"country": payload.country},
    }
    run_id = _run_in_background(background_tasks, job)
    return {"run_id": run_id, "status": "started", "job": job}


@router.post("/jiji")
def trigger_jiji(payload: JijiRunRequest, background_tasks: BackgroundTasks):
    kwargs = {"category_path": payload.category_path}
    if payload.location:
        kwargs["location"] = payload.location
    job = {"scraper": "jiji", "max_listings": payload.max_listings, "kwargs": kwargs}
    run_id = _run_in_background(background_tasks, job)
    return {"run_id": run_id, "status": "started", "job": job}


@router.post("/carapi")
def trigger_carapi(payload: CarApiRunRequest, background_tasks: BackgroundTasks):
    kwargs = {"years": payload.years} if payload.years else {}
    if payload.makes:
        kwargs["makes"] = payload.makes
    job = {"scraper": "carapi", "kwargs": kwargs}
    run_id = _run_in_background(background_tasks, job)
    return {"run_id": run_id, "status": "started", "job": job}


@router.get("/status")
def scraper_status(
    source: Optional[str] = Query(None, description="Filter by scraper source, e.g. 'jiji'"),
    limit: int = Query(20, le=100),
):
    """Recent run history from scraper_logs (see services/scraper_logger.py
    for the schema). Note this reports by source + start time, not by the
    run_id returned from the trigger endpoints above - scraper_logs doesn't
    have a run_id column yet. Add one and thread it through
    ScraperRunLogger.start() if you need per-run_id lookups."""
    query = supabase.table("scraper_logs").select("*").order("started_at", desc=True).limit(limit)
    if source:
        query = query.eq("source", source)
    resp = query.execute()
    return {"runs": resp.data or []}
