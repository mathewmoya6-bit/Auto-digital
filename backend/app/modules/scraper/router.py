# app/modules/scraper/router.py
# ================================================================
# Auto-D Kenya - Scraper API Router
# ================================================================

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Query,
    Depends
)

from pydantic import BaseModel, Field

from app.modules.scraper.service import ScraperService
from app.core.dependencies import get_current_user, get_current_admin

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/scraper",
    tags=["Scraper"]
)


service = ScraperService()



# ================================================================
# Request Schema
# ================================================================

class ScraperRequest(BaseModel):
    source: str = Field(default="jiji", description="Scraper source")
    pages: int = Field(default=3, ge=1, le=50)
    limit_per_page: int = Field(default=20, ge=1, le=100)


class ScraperRunRequest(BaseModel):
    sources: Optional[List[str]] = Field(None, description="List of sources to run")


# ================================================================
# Dashboard Endpoints (ADD THESE)
# ================================================================

@router.get("/status")
async def scraper_status(
    current_user: dict = Depends(get_current_user)
):
    """
    Get scraper status for the admin dashboard.
    
    GET /api/v1/scraper/status
    """
    try:
        # Get status from service
        status = await service.get_status()
        return {
            "data": {
                "status": status.get("status", "idle"),
                "total_listings": status.get("total_listings", 0),
                "last_run": status.get("last_run"),
                "sources": status.get("sources", [])
            }
        }
    except Exception as e:
        logger.exception("Failed to get scraper status")
        return {
            "data": {
                "status": "idle",
                "total_listings": 0,
                "last_run": None,
                "sources": []
            }
        }


@router.post("/run")
async def run_scrapers(
    request: ScraperRunRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_admin)
):
    """
    Run all or specific scrapers for the admin dashboard.
    
    POST /api/v1/scraper/run
    """
    try:
        sources = request.sources or ["autochek", "jiji", "carapi"]
        
        # Start scraper jobs for each source
        job_ids = []
        for source in sources:
            job_id = await service.start_scraper(
                source=source,
                pages=3,
                limit_per_page=20
            )
            job_ids.append(job_id)
            
            # Add background task
            background_tasks.add_task(
                service.run_scraper_background,
                job_id,
                source,
                3,
                20
            )
        
        return {
            "status": "started",
            "message": f"Scraping started for: {', '.join(sources)}",
            "task_id": f"scrape_{int(datetime.now(timezone.utc).timestamp())}",
            "job_ids": job_ids
        }
    except Exception as e:
        logger.exception("Scraper run failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{source}")
async def run_single_scraper(
    source: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_admin)
):
    """
    Run a single scraper source for the admin dashboard.
    
    POST /api/v1/scraper/{source}
    """
    try:
        valid_sources = ["autochek", "jiji", "carapi"]
        if source not in valid_sources:
            raise HTTPException(
                status_code=404,
                detail=f"Source '{source}' not found"
            )
        
        job_id = await service.start_scraper(
            source=source,
            pages=3,
            limit_per_page=20
        )
        
        background_tasks.add_task(
            service.run_scraper_background,
            job_id,
            source,
            3,
            20
        )
        
        return {
            "status": "started",
            "message": f"Scraping started for: {source}",
            "task_id": f"scrape_{source}_{int(datetime.now(timezone.utc).timestamp())}",
            "job_id": job_id
        }
    except Exception as e:
        logger.exception(f"Single scraper {source} failed")
        raise HTTPException(status_code=500, detail=str(e))


# ================================================================
# Existing Endpoints (keep these)
# ================================================================

@router.post("/start")
async def start_scraper(
    request: ScraperRequest,
    background_tasks: BackgroundTasks
):
    """Start a scraper job (original endpoint)."""
    try:
        logger.info(f"Starting scraper source={request.source}")
        
        job_id = await service.start_scraper(
            source=request.source,
            pages=request.pages,
            limit_per_page=request.limit_per_page
        )
        
        logger.info(f"Created scraper job {job_id}")
        
        background_tasks.add_task(
            service.run_scraper_background,
            job_id,
            request.source,
            request.pages,
            request.limit_per_page
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "source": request.source,
            "pages": request.pages,
            "limit_per_page": request.limit_per_page,
            "status": "queued"
        }
    except Exception as e:
        logger.exception("Scraper start failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job/{job_id}")
async def job_status(job_id: int):
    """Get job status."""
    try:
        return await service.get_job_status(job_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
async def job_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get job history."""
    return await service.get_job_history(limit=limit, offset=offset)


@router.get("/sources")
async def sources():
    """Get available sources."""
    return await service.get_sources()


@router.get("/health")
async def health():
    """Health check."""
    return await service.health_check()
