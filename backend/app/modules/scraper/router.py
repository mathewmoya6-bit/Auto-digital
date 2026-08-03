# app/modules/scraper/router.py

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
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

class RunScraperRequest(BaseModel):
    source: str = Field(default="all")
    pages: int = Field(default=3, ge=1, le=50)
    limit_per_page: int = Field(default=20, ge=1, le=100)
    parallel: bool = True
    max_concurrent: int = Field(default=4, ge=1, le=20)


# ============================================================
# STATUS
# ============================================================

@router.get("/status")
async def get_status(
    current_user=Depends(get_current_user),
):
    """
    Get scraper dashboard status.
    """
    try:
        return await service.get_status()

    except Exception:
        logger.exception("Unable to fetch scraper status")
        raise HTTPException(
            status_code=500,
            detail="Unable to fetch scraper status.",
        )


# ============================================================
# SOURCES
# ============================================================

@router.get("/sources")
async def get_sources(
    current_user=Depends(get_current_user),
):
    """
    List available scraper sources.
    """
    try:
        return await service.get_sources()

    except Exception:
        logger.exception("Unable to fetch scraper sources")
        raise HTTPException(
            status_code=500,
            detail="Unable to fetch scraper sources.",
        )


# ============================================================
# RUN SCRAPER
# ============================================================

@router.post("/run")
async def run_scraper(
    request: RunScraperRequest,
    current_user=Depends(get_current_admin),
):
    """
    Run one scraper or all scrapers.

    Source may be:
    - all
    - jiji
    - cheki
    - autochek
    - beepbeep

    Validation is handled by the worker.
    """
    try:
        return await service.run_scraper(
            source=request.source,
            pages=request.pages,
            limit_per_page=request.limit_per_page,
            parallel=request.parallel,
            max_concurrent=request.max_concurrent,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception:
        logger.exception("Failed to start scraper")
        raise HTTPException(
            status_code=500,
            detail="Failed to start scraper.",
        )


# ============================================================
# RUN SINGLE SOURCE
# ============================================================

@router.post("/{source}")
async def run_single_source(
    source: str,
    current_user=Depends(get_current_admin),
):
    """
    Convenience endpoint.

    Example:
        POST /scraper/jiji
    """
    try:
        return await service.run_scraper(source=source)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception:
        logger.exception("Failed running scraper %s", source)
        raise HTTPException(
            status_code=500,
            detail="Failed to start scraper.",
        )


# ============================================================
# RUN STATUS
# ============================================================

@router.get("/runs/{run_id}")
async def get_run_status(
    run_id: int,
    current_user=Depends(get_current_user),
):
    """
    Get a scraper run.
    """
    try:
        result = await service.get_run_status(run_id)

        if not result.get("found", False):
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "Run not found."),
            )

        return result

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unable to fetch run %s", run_id)
        raise HTTPException(
            status_code=500,
            detail="Unable to fetch run status.",
        )


# ============================================================
# RUN HISTORY
# ============================================================

@router.get("/runs")
async def get_run_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    source: Optional[str] = None,
    status: Optional[str] = None,
    current_user=Depends(get_current_admin),
):
    """
    List scraper runs.
    """
    try:
        return await service.get_run_history(
            limit=limit,
            offset=offset,
            source=source,
            status=status,
        )

    except Exception:
        logger.exception("Unable to fetch run history")
        raise HTTPException(
            status_code=500,
            detail="Unable to fetch run history.",
        )


# ============================================================
# RUNNING
# ============================================================

@router.get("/running")
async def get_running(
    current_user=Depends(get_current_user),
):
    """
    List currently running scraper jobs.
    """
    try:
        return await service.get_run_history(
            status="running",
            limit=100,
        )

    except Exception:
        logger.exception("Unable to fetch running jobs")
        raise HTTPException(
            status_code=500,
            detail="Unable to fetch running jobs.",
        )


# ============================================================
# HEALTH
# ============================================================

@router.get("/health")
async def health():
    """
    Worker health check.
    """
    try:
        return await service.health_check()

    except Exception:
        logger.exception("Health check failed")
        raise HTTPException(
            status_code=500,
            detail="Health check failed.",
        )


# ============================================================
# RECOVER STUCK RUNS
# ============================================================

@router.post("/recover")
async def recover_stuck_runs(
    max_age_minutes: int = Query(60, ge=1),
    current_user=Depends(get_current_admin),
):
    """
    Recover scraper runs stuck in 'running' state.
    """
    try:
        return await service.recover_stuck_jobs(
            max_age_minutes=max_age_minutes,
        )

    except Exception:
        logger.exception("Recovery failed")
        raise HTTPException(
            status_code=500,
            detail="Recovery failed.",
        )
