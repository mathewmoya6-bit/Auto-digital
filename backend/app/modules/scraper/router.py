# app/modules/scraper/router.py

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


# =====================================================
# MODELS
# =====================================================

class ScraperRequest(BaseModel):
    source: str = Field(default="jiji")
    pages: int = Field(default=3, ge=1, le=50)
    limit_per_page: int = Field(default=20, ge=1, le=100)


class RunScrapersRequest(BaseModel):
    sources: Optional[List[str]] = None
    pages: int = 3
    limit_per_page: int = 20


# =====================================================
# VALID SOURCES
# =====================================================

VALID_SOURCES = ["autochek", "jiji", "cheki", "beepbeep"]


# =====================================================
# DASHBOARD STATUS
# =====================================================

@router.get("/status")
async def status(
    current_user=Depends(get_current_user),
):
    try:
        return await service.get_status()
    except Exception:
        logger.exception("Unable to fetch scraper status")

        return {
            "status": "idle",
            "running": False,
            "sources": [],
            "last_run": None,
            "total_listings": 0,
        }


# =====================================================
# RUN ALL SCRAPERS
# =====================================================

@router.post("/run")
async def run_all_scrapers(
    request: RunScrapersRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_admin),
):
    try:
        # Use provided sources or default to all valid sources
        sources = request.sources or VALID_SOURCES
        
        # Filter to only valid sources
        valid_sources = [s for s in sources if s in VALID_SOURCES]
        
        if not valid_sources:
            raise HTTPException(
                400,
                f"No valid sources. Available: {', '.join(VALID_SOURCES)}"
            )
        
        # Log warning for any invalid sources
        invalid_sources = [s for s in sources if s not in VALID_SOURCES]
        if invalid_sources:
            logger.warning(f"Skipping invalid sources: {', '.join(invalid_sources)}")

        jobs = []

        for source in valid_sources:
            job_id = await service.start_scraper(
                source=source,
                pages=request.pages,
                limit_per_page=request.limit_per_page,
            )

            jobs.append(job_id)

            background_tasks.add_task(
                service.run_scraper_background,
                job_id,
                source,
                request.pages,
                request.limit_per_page,
            )

        return {
            "success": True,
            "status": "started",
            "job_ids": jobs,
            "sources": valid_sources,
            "started_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Run scraper failed")
        raise HTTPException(500, str(e))


# =====================================================
# RUN SINGLE SOURCE
# =====================================================

@router.post("/{source}")
async def run_single_source(
    source: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_admin),
):
    try:
        # Validate source
        if source not in VALID_SOURCES:
            raise HTTPException(
                404,
                f"Source '{source}' not found. Available: {', '.join(VALID_SOURCES)}"
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
            "job_id": job_id,
            "source": source,
            "status": "started",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Single scraper failed")
        raise HTTPException(500, str(e))


# =====================================================
# ORIGINAL START ENDPOINT
# =====================================================

@router.post("/start")
async def start_scraper(
    request: ScraperRequest,
    background_tasks: BackgroundTasks,
):
    try:
        # Validate source
        if request.source not in VALID_SOURCES:
            raise HTTPException(
                400,
                f"Invalid source '{request.source}'. Available: {', '.join(VALID_SOURCES)}"
            )

        job_id = await service.start_scraper(
            source=request.source,
            pages=request.pages,
            limit_per_page=request.limit_per_page,
        )

        background_tasks.add_task(
            service.run_scraper_background,
            job_id,
            request.source,
            request.pages,
            request.limit_per_page,
        )

        return {
            "success": True,
            "job_id": job_id,
            "status": "queued",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Start scraper failed")
        raise HTTPException(500, str(e))


# =====================================================
# JOB STATUS
# =====================================================

@router.get("/job/{job_id}")
async def job_status(job_id: int):
    return await service.get_job_status(job_id)


# =====================================================
# JOB HISTORY
# =====================================================

@router.get("/jobs")
async def jobs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return await service.get_job_history(
        limit=limit,
        offset=offset,
    )


# =====================================================
# SOURCES
# =====================================================

@router.get("/sources")
async def sources():
    return await service.get_sources()


# =====================================================
# HEALTH
# =====================================================

@router.get("/health")
async def health():
    return await service.health_check()
