# app/modules/scraper/router.py
# ================================================================
# Auto-D Kenya - Scraper API Router
# ================================================================

import logging
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Query
)

from pydantic import BaseModel


from app.modules.scraper.service import ScraperService


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/scraper",
    tags=["Scraper"]
)


service = ScraperService()



# ================================================================
# Schemas
# ================================================================


class ScraperRequest(BaseModel):

    source: str = "jiji"

    pages: int = 3

    limit_per_page: int = 20




# ================================================================
# Start scraper
# ================================================================


@router.post("/start")
async def start_scraper(
    request: ScraperRequest,
    background_tasks: BackgroundTasks
):

    try:

        job_id = await service.start_scraper(
            source=request.source,
            pages=request.pages,
            limit_per_page=request.limit_per_page
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

            "job_id":
                job_id,

            "source":
                request.source,

            "status":
                "started"

        }


    except Exception as e:


        logger.exception(
            "Failed starting scraper"
        )


        raise HTTPException(
            status_code=500,
            detail=str(e)
        )





# ================================================================
# Job status
# ================================================================


@router.get("/job/{job_id}")
async def get_job_status(
    job_id: int
):


    result = await service.get_job_status(
        job_id
    )


    return result




# ================================================================
# Job history
# ================================================================


@router.get("/jobs")
async def get_jobs(
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
        limit,
        offset
    )




# ================================================================
# Available sources
# ================================================================


@router.get("/sources")
async def get_sources():


    return await service.get_sources()




# ================================================================
# Health
# ================================================================


@router.get("/health")
async def health():


    return await service.health_check()
