"""
Market Scraper Router
Handles web scraping operations for market data
"""

from __future__ import annotations

from typing import Optional, Dict, List, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
import logging
import random

from app.core.database import supabase

router = APIRouter()
logger = logging.getLogger(__name__)

TABLE = "market_prices"


# ─── Schemas ────────────────────────────────────────────────────────────────

class ScraperConfig(BaseModel):
    source: str
    enabled: bool = True
    frequency_hours: int = Field(24, ge=1, le=168)
    max_pages: int = Field(10, ge=1, le=100)
    user_agent: Optional[str] = None
    proxy: Optional[str] = None


class ScrapeResult(BaseModel):
    source: str
    status: str
    items_scraped: int
    duration_seconds: float
    timestamp: datetime
    errors: List[str] = []


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.post("/run")
async def run_scraper(
    background_tasks: BackgroundTasks,
    sources: Optional[List[str]] = Query(None, description="Specific sources to scrape")
):
    """
    Run the market scraper for specified sources
    If no sources specified, scrapes all configured sources
    """
    # Start background task
    background_tasks.add_task(
        _run_scraper_task,
        sources=sources or ["all"]
    )
    
    return {
        "status": "success",
        "message": f"Scraper started for {', '.join(sources or ['all'])}",
        "task_id": f"scrape_{int(datetime.now().timestamp())}",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/autochek")
async def scrape_autochek(background_tasks: BackgroundTasks):
    """Scrape Autochek specifically"""
    background_tasks.add_task(_scrape_autochek)
    return {
        "status": "success",
        "message": "Autochek scraping started",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/jiji")
async def scrape_jiji(background_tasks: BackgroundTasks):
    """Scrape Jiji specifically"""
    background_tasks.add_task(_scrape_jiji)
    return {
        "status": "success",
        "message": "Jiji scraping started",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/carapi")
async def scrape_carapi(background_tasks: BackgroundTasks):
    """Scrape CarAPI specifically"""
    background_tasks.add_task(_scrape_carapi)
    return {
        "status": "success",
        "message": "CarAPI scraping started",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/status")
async def get_scraper_status():
    """
    Get the current scraper status
    Returns last run time, status, and statistics
    """
    try:
        # Query recent scrapes from market_prices
        query = supabase.table(TABLE).select("source, created_at").order("created_at", desc=True).limit(100)
        resp = query.execute()
        listings = resp.data or []
        
        if not listings:
            return {
                "status": "success",
                "data": {
                    "status": "idle",
                    "last_run": None,
                    "sources": [],
                    "total_listings": 0,
                    "last_24h_count": 0
                }
            }
        
        # Calculate statistics
        sources = list(set(l.get("source", "unknown") for l in listings))
        last_run = listings[0].get("created_at") if listings else None
        
        # Count last 24h
        cutoff = datetime.now() - timedelta(days=1)
        recent = [
            l for l in listings 
            if l.get("created_at") and datetime.fromisoformat(l.get("created_at")) > cutoff
        ]
        
        return {
            "status": "success",
            "data": {
                "status": "idle",  # Could also be "running" if tracking in memory
                "last_run": last_run,
                "sources": sources,
                "total_listings": len(listings),
                "last_24h_count": len(recent),
                "scraper_version": "1.0.0"
            }
        }
        
    except Exception as e:
        logger.error(f"Scraper status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources")
async def get_scraper_sources():
    """
    Get list of available scraper sources
    """
    return {
        "status": "success",
        "data": {
            "sources": [
                {"id": "autochek", "name": "Autochek Kenya", "enabled": True},
                {"id": "jiji", "name": "Jiji Kenya", "enabled": True},
                {"id": "carapi", "name": "CarAPI", "enabled": True},
                {"id": "beepbeep", "name": "BeepBeep Kenya", "enabled": False},
                {"id": "pigiama", "name": "PigiaMe", "enabled": False},
            ]
        }
    }


@router.get("/config")
async def get_scraper_config():
    """
    Get current scraper configuration
    """
    # In production, this would read from database or config
    return {
        "status": "success",
        "data": {
            "config": {
                "concurrent_scrapers": 3,
                "request_timeout": 30,
                "retry_attempts": 3,
                "rate_limit": 10,  # requests per minute
                "default_max_pages": 10,
                "sources": {
                    "autochek": {"enabled": True, "frequency_hours": 24, "max_pages": 10},
                    "jiji": {"enabled": True, "frequency_hours": 24, "max_pages": 15},
                    "carapi": {"enabled": True, "frequency_hours": 48, "max_pages": 5},
                }
            }
        }
    }


@router.put("/config")
async def update_scraper_config(config: Dict[str, Any]):
    """
    Update scraper configuration
    """
    # In production, save to database
    logger.info(f"Scraper config updated: {config}")
    
    return {
        "status": "success",
        "message": "Configuration updated",
        "config": config
    }


# ─── Background Tasks ──────────────────────────────────────────────────────

async def _run_scraper_task(sources: List[str]):
    """Main scraper background task"""
    logger.info(f"Running scraper for sources: {sources}")
    
    try:
        if "all" in sources:
            sources = ["autochek", "jiji", "carapi"]
        
        results = []
        for source in sources:
            try:
                result = await _scrape_source(source)
                results.append(result)
                logger.info(f"✅ {source} scrape completed: {result['items_scraped']} items")
            except Exception as e:
                logger.error(f"❌ {source} scrape failed: {e}")
                results.append({"source": source, "error": str(e)})
        
        logger.info(f"Scraper task completed: {len(results)} sources processed")
        
    except Exception as e:
        logger.error(f"Scraper task failed: {e}")


async def _scrape_source(source: str) -> Dict[str, Any]:
    """Scrape a specific source"""
    # Simulate scraping
    start_time = datetime.now()
    
    # Simulate random delays and results
    import asyncio
    await asyncio.sleep(random.uniform(1, 5))
    
    # Generate mock data
    items_scraped = random.randint(5, 50)
    errors = []
    
    # Simulate occasional errors
    if random.random() < 0.1:
        errors.append("Rate limit exceeded")
        items_scraped = 0
    
    return {
        "source": source,
        "status": "success" if not errors else "partial",
        "items_scraped": items_scraped,
        "duration_seconds": (datetime.now() - start_time).total_seconds(),
        "errors": errors
    }


async def _scrape_autochek():
    """Scrape Autochek"""
    logger.info("Scraping Autochek...")
    await _scrape_source("autochek")


async def _scrape_jiji():
    """Scrape Jiji"""
    logger.info("Scraping Jiji...")
    await _scrape_source("jiji")


async def _scrape_carapi():
    """Scrape CarAPI"""
    logger.info("Scraping CarAPI...")
    await _scrape_source("carapi")
