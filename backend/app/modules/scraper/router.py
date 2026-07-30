# app/modules/scraper/router.py
# Auto-D Kenya - Scraper Routes
# ================================================================
# TYPE: MODULE - Scraper API routes

import logging
from typing import Optional
from fastapi import APIRouter, Depends, BackgroundTasks, Query

from app.core.dependencies import get_current_user
from app.modules.scraper.service import ScraperService
from app.modules.scraper.schemas import (
    ScraperRunRequest,
    ScraperRunResponse,
    ScraperStatusResponse,
    ScraperSourceResponse,
    ScraperHealthResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()
scraper_service = ScraperService()


@router.post("/scraper/run", response_model=ScraperRunResponse)
async def run_scraper(
    background_tasks: BackgroundTasks,
    request: ScraperRunRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Run the scraper for a specific source or all sources.
    
    Args:
        background_tasks: FastAPI background tasks
        request: Scraper run request with source and options
        current_user: Authenticated user
        
    Returns:
        ScraperRunResponse: Response with job ID and status
    """
    # Start scraper in background
    job_id = await scraper_service.start_scraper(
        source=request.source,
        pages=request.pages,
        limit_per_page=request.limit_per_page,
        user_id=current_user["id"]
    )
    
    # Add to background tasks
    background_tasks.add_task(
        scraper_service.run_scraper_background,
        job_id,
        request.source,
        request.pages,
        request.limit_per_page
    )
    
    return ScraperRunResponse(
        job_id=job_id,
        source=request.source,
        status="started",
        message=f"Scraper started for source: {request.source}"
    )


@router.get("/scraper/status", response_model=ScraperStatusResponse)
async def get_scraper_status(
    job_id: Optional[str] = Query(None, description="Specific job ID to check"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get scraper status.
    
    Args:
        job_id: Optional specific job ID
        current_user: Authenticated user
        
    Returns:
        ScraperStatusResponse: Current scraper status
    """
    if job_id:
        return await scraper_service.get_job_status(job_id)
    return await scraper_service.get_status()


@router.get("/scraper/sources", response_model=ScraperSourceResponse)
async def get_scraper_sources(current_user: dict = Depends(get_current_user)):
    """
    Get available scraper sources.
    
    Args:
        current_user: Authenticated user
        
    Returns:
        ScraperSourceResponse: List of available sources
    """
    return await scraper_service.get_sources()


@router.get("/scraper/health", response_model=ScraperHealthResponse)
async def scraper_health():
    """
    Check scraper health.
    
    Returns:
        ScraperHealthResponse: Health status
    """
    return await scraper_service.health_check()


@router.get("/scraper/history")
async def get_scraper_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    Get scraper job history.
    
    Args:
        limit: Number of jobs to return
        offset: Pagination offset
        current_user: Authenticated user
        
    Returns:
        List of scraper jobs
    """
    return await scraper_service.get_job_history(limit, offset)
