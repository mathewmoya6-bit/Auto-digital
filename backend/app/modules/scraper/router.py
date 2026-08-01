# app/modules/scraper/router.py
# ================================================================
# Auto-D Kenya - Scraper API Router
# ================================================================

import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Query
)

from pydantic import BaseModel, Field

from app.modules.scraper.service import ScraperService


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

    source: str = Field(
        default="jiji",
        description="Scraper source"
    )

    pages: int = Field(
        default=3,
        ge=1,
        le=50
    )

    limit_per_page: int = Field(
        default=20,
        ge=1,
        le=100
    )



# ================================================================
# Start Scraper
# ================================================================

@router.post("/start")
async def start_scraper(
    request: ScraperRequest,
    background_tasks: BackgroundTasks
):

    try:

        logger.info(
            f"Starting scraper source={request.source}"
        )


        job_id = await service.start_scraper(
            source=request.source,
            pages=request.pages,
            limit_per_page=request.limit_per_page
        )


        logger.info(
            f"Created scraper job {job_id}"
        )


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

        logger.exception(
            "Scraper start failed"
        )


        raise HTTPException(
            status_code=500,
            detail=str(e)
        )



# ================================================================
# Get Job Status
# ================================================================

@router.get("/job/{job_id}")
async def job_status(
    job_id: int
):

    try:

        return await service.get_job_status(
            job_id
        )


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )



# ================================================================
# Job History
# ================================================================

@router.get("/jobs")
async def job_history(
    limit: int = Query(
        20,
        ge=1,
        le=100
    ),

    offset: int = Query(
        0,
        ge=0
    )
):

    return await service.get_job_history(
        limit=limit,
        offset=offset
    )



# ================================================================
# Available Sources
# ================================================================

@router.get("/sources")
async def sources():

    return await service.get_sources()



# ================================================================
# Health Check
# ================================================================

@router.get("/health")
async def health():

    return await service.health_check()
