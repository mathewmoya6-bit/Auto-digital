# app/modules/scraper/router.py
# ================================================================
# Auto-D Kenya - Scraper Router
# ================================================================

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
)
from pydantic import BaseModel, Field

from app.core.dependencies import (
    get_current_admin,
    get_current_user,
)
from app.modules.scraper.service import ScraperService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/scraper",
    tags=["Scraper"],
)

service = ScraperService()


# ============================================================
# REQUEST MODELS
# ============================================================

class ScraperRequest(BaseModel):
    source: str = Field(default="all")
    pages: int = Field(default=3, ge=1, le=50)
    limit_per_page: int = Field(default=20, ge=1, le=100)


class RunScrapersRequest(BaseModel):
    sources: Optional[List[str]] = None
    pages: int = Field(default=3, ge=1, le=50)
    limit_per_page: int = Field(default=20, ge=1, le=100)


# ============================================================
# VALID SOURCES
# ============================================================

VALID_SOURCES = [
    "all",
    "jiji",
    "cheki",
    "autochek",
    "beepbeep",
]


# ============================================================
# STATUS
# ============================================================

@router.get("/status")
async def scraper_status(
    current_user=Depends(get_current_user),
):
    try:
        return await service.get_status()

    except Exception:

        logger.exception(
            "Unable to fetch scraper status"
        )

        return {
            "status": "idle",
            "running": False,
            "last_run": None,
            "total_listings": 0,
            "sources": [],
        }


# ============================================================
# STATS
# ============================================================

@router.get("/stats")
async def scraper_stats(
    current_user=Depends(get_current_admin),
):
    return await service.get_status()


# ============================================================
# SOURCES
# ============================================================

@router.get("/sources")
async def scraper_sources():

    result = await service.get_sources()

    return {
        "sources": result["sources"],
        "count": len(result["sources"]),
    }


# ============================================================
# RUN ALL
# ============================================================

@router.post("/run")
async def run_scrapers(
    request: RunScrapersRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_admin),
):

    try:

        sources = request.sources or VALID_SOURCES[1:]

        valid_sources = [
            s for s in sources
            if s in VALID_SOURCES
            and s != "all"
        ]

        invalid_sources = [
            s for s in sources
            if s not in VALID_SOURCES
        ]

        if invalid_sources:

            logger.warning(
                "Ignoring invalid sources: %s",
                invalid_sources,
            )

        if not valid_sources:

            raise HTTPException(
                status_code=400,
                detail="No valid scraper sources supplied.",
            )

        jobs = []
        failed = []

        for source in valid_sources:

            try:

                logger.info(
                    "Starting scraper %s",
                    source,
                )

                job_id = await service.start_scraper(
                    source=source,
                    pages=request.pages,
                    limit_per_page=request.limit_per_page,
                )

                logger.info(
                    "Created job %s for %s",
                    job_id,
                    source,
                )

                jobs.append({
                    "source": source,
                    "job_id": job_id,
                })

                background_tasks.add_task(
                    service.run_scraper_background,
                    job_id,
                    source,
                    request.pages,
                    request.limit_per_page,
                )

            except Exception as exc:

                logger.exception(
                    "Unable to start %s",
                    source,
                )

                failed.append({
                    "source": source,
                    "error": str(exc),
                })

        return {
            "success": len(jobs) > 0,
            "status": (
                "running"
                if jobs
                else "failed"
            ),
            "jobs": jobs,
            "failed": failed,
            "job_count": len(jobs),
            "pages": request.pages,
            "limit_per_page": request.limit_per_page,
            "started_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "Run scraper failed"
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to start scrapers",
                "error": str(exc),
            },
        )


# ============================================================
# RUN SINGLE SOURCE
# ============================================================

@router.post("/{source}")
async def run_single_source(
    source: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_admin),
):

    if source not in VALID_SOURCES or source == "all":

        raise HTTPException(
            status_code=404,
            detail=f"Unknown source '{source}'",
        )

    try:

        logger.info(
            "Starting %s scraper",
            source,
        )

        job_id = await service.start_scraper(
            source=source,
            pages=3,
            limit_per_page=20,
        )

        background_tasks.add_task(
            service.run_scraper_background,
            job_id,
            source,
            3,
            20,
        )

        return {
            "success": True,
            "status": "running",
            "job_id": job_id,
            "source": source,
            "started_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    except Exception as exc:

        logger.exception(
            "Failed starting %s",
            source,
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# START (Legacy Endpoint)
# ============================================================

@router.post("/start")
async def start_scraper(
    request: ScraperRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_admin),
):

    if request.source == "all":

        request = RunScrapersRequest(
            sources=None,
            pages=request.pages,
            limit_per_page=request.limit_per_page,
        )

        return await run_scrapers(
            request,
            background_tasks,
            current_user,
        )

    return await run_single_source(
        request.source,
        background_tasks,
        current_user,
    )


# ============================================================
# JOB STATUS
# ============================================================

@router.get("/job/{job_id}")
async def job_status(
    job_id: int,
    current_user=Depends(get_current_user),
):

    job = await service.get_job_status(
        job_id
    )

    if "error" in job:

        raise HTTPException(
            status_code=404,
            detail=job["error"],
        )

    return job


# ============================================================
# JOB HISTORY
# ============================================================

@router.get("/jobs")
async def job_history(
    limit: int = Query(
        20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        0,
        ge=0,
    ),
    current_user=Depends(get_current_admin),
):

    return await service.get_job_history(
        limit=limit,
        offset=offset,
    )


# ============================================================
# RUNNING JOBS
# ============================================================

@router.get("/running")
async def running_jobs(
    current_user=Depends(get_current_user),
):

    history = await service.get_job_history(
        limit=100
    )

    running = [
        job
        for job in history["jobs"]
        if job.get("status") == "running"
    ]

    return {
        "count": len(running),
        "jobs": running,
    }


# ============================================================
# HEALTH
# ============================================================

@router.get("/health")
async def scraper_health():

    return await service.health_check()
