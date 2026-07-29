"""
Market Scraper Router
Auto-D Kenya
"""

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
import logging

router = APIRouter()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Background Jobs
# ---------------------------------------------------------------------

async def scrape_source(source: str):
    """Placeholder scraper function."""

    logger.info(f"Starting scraper: {source}")

    # TODO:
    # Call your real scraper service here.
    #
    # Example:
    # from app.services.market_scraper import scraper_service
    # await scraper_service.scrape(source)

    logger.info(f"Finished scraper: {source}")


async def scrape_all():
    """Run all enabled scrapers."""

    for source in ["autochek", "jiji", "carapi"]:
        try:
            await scrape_source(source)
        except Exception as e:
            logger.exception(f"{source} scraper failed: {e}")


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------

@router.post("/run")
async def run_scraper(
    background_tasks: BackgroundTasks,
    sources: Optional[List[str]] = Query(default=None),
):
    """
    Run scraper in the background.
    """

    if not sources:
        background_tasks.add_task(scrape_all)

        return {
            "success": True,
            "message": "All scrapers started",
            "sources": ["autochek", "jiji", "carapi"],
            "started_at": datetime.utcnow().isoformat(),
        }

    for source in sources:
        background_tasks.add_task(scrape_source, source)

    return {
        "success": True,
        "message": "Selected scrapers started",
        "sources": sources,
        "started_at": datetime.utcnow().isoformat(),
    }


@router.post("/autochek")
async def run_autochek(background_tasks: BackgroundTasks):

    background_tasks.add_task(scrape_source, "autochek")

    return {
        "success": True,
        "source": "autochek",
    }


@router.post("/jiji")
async def run_jiji(background_tasks: BackgroundTasks):

    background_tasks.add_task(scrape_source, "jiji")

    return {
        "success": True,
        "source": "jiji",
    }


@router.post("/carapi")
async def run_carapi(background_tasks: BackgroundTasks):

    background_tasks.add_task(scrape_source, "carapi")

    return {
        "success": True,
        "source": "carapi",
    }


@router.get("/status")
async def scraper_status():

    return {
        "status": "idle",
        "running": False,
        "last_run": None,
        "enabled_sources": [
            "autochek",
            "jiji",
            "carapi",
        ],
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/sources")
async def scraper_sources():

    return {
        "sources": [
            {
                "id": "autochek",
                "name": "Autochek Kenya",
                "enabled": True,
            },
            {
                "id": "jiji",
                "name": "Jiji Kenya",
                "enabled": True,
            },
            {
                "id": "carapi",
                "name": "CarAPI",
                "enabled": True,
            },
        ]
    }


@router.get("/health")
async def health():

    return {
        "status": "healthy",
        "service": "market_scraper",
        "timestamp": datetime.utcnow().isoformat(),
    }
