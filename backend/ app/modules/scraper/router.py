# app/modules/scraper/router.py
# Auto-D Kenya - Scraper Routes
# ================================================================
# TYPE: MODULE - Scraper API routes

from fastapi import APIRouter, Depends, BackgroundTasks

from app.core.dependencies import get_current_user
from app.modules.scraper.service import ScraperService

router = APIRouter()
scraper_service = ScraperService()


@router.post("/scraper/run")
async def run_scraper(
    background_tasks: BackgroundTasks,
    source: str = "all",
    current_user: dict = Depends(get_current_user)
):
    """Run the scraper for a specific source or all sources."""
    background_tasks.add_task(scraper_service.run_scraper, source)
    return {"message": f"Scraper started for source: {source}"}


@router.get("/scraper/status")
async def get_scraper_status(current_user: dict = Depends(get_current_user)):
    """Get scraper status."""
    return await scraper_service.get_status()


@router.get("/scraper/sources")
async def get_scraper_sources(current_user: dict = Depends(get_current_user)):
    """Get available scraper sources."""
    return scraper_service.get_sources()


@router.get("/scraper/health")
async def scraper_health():
    """Check scraper health."""
    return {"status": "healthy"}
