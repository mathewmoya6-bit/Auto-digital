# backend/app/api/v1/market.py
"""
Market Data API Routes
Handles market scraping, insights, and location factors
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional, List, Dict
from datetime import datetime
import logging

from app.services.market_scraper import MarketScraper
from app.services.supabase_service import SupabaseService
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["Market Data"])

# Initialize services
supabase_service = SupabaseService()
market_scraper = MarketScraper(supabase_service)


@router.post("/scrape")
async def trigger_scrape(background_tasks: BackgroundTasks) -> Dict:
    """
    Trigger market price scraping from all sources.
    
    Sources:
    1. Jiji Kenya (Primary - highest volume)
    2. Cheki Kenya (Dealer pricing)
    3. Autochek Kenya (Premium market)
    4. BeepBeep Kenya (Secondary dealer)
    5. PigiaMe Kenya (Additional listings)
    """
    try:
        # Run in background to avoid timeout
        background_tasks.add_task(market_scraper.scrape_all_sources)
        return {
            "status": "started",
            "message": "Market scraping started in background",
            "timestamp": datetime.now().isoformat(),
            "sources": ["Jiji", "Cheki", "Autochek", "BeepBeep", "PigiaMe"]
        }
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        raise HTTPException(status_code=500, detail="Scraping failed")


@router.post("/scrape/sync")
async def trigger_scrape_sync() -> Dict:
    """
    Trigger market price scraping synchronously (admin only).
    
    Warning: This may take several minutes to complete.
    """
    try:
        count = await market_scraper.scrape_all_sources()
        return {
            "status": "success",
            "message": f"Scraped {count} new prices",
            "count": count,
            "timestamp": datetime.now().isoformat(),
            "sources_used": ["Jiji", "Cheki", "Autochek", "BeepBeep", "PigiaMe"]
        }
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        raise HTTPException(status_code=500, detail="Scraping failed")


@router.get("/insights")
async def get_market_insights(
    make: Optional[str] = Query(None, description="Filter by make"),
    body_type: Optional[str] = Query(None, description="Filter by body type")
) -> Dict:
    """
    Get market insights and trends.
    
    Returns:
    - Overall market statistics (total listings, average price, etc.)
    - Trending vehicles
    - Price distribution across brackets
    """
    try:
        # Get overall market statistics
        stats = await supabase_service.get_market_statistics(make, body_type)
        
        # Get top trending vehicles
        trending = await supabase_service.get_trending_vehicles(limit=10)
        
        # Get price distribution
        distribution = await supabase_service.get_price_distribution(make, body_type)
        
        return {
            "status": "success",
            "statistics": stats,
            "trending_vehicles": trending,
            "price_distribution": distribution,
            "last_updated": datetime.now().isoformat(),
            "filters_applied": {
                "make": make,
                "body_type": body_type
            }
        }
    except Exception as e:
        logger.error(f"Error fetching market insights: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sources/status")
async def get_source_status() -> Dict:
    """
    Get status of all market data sources.
    """
    sources = {
        "jiji": {
            "name": "Jiji Kenya",
            "status": "active",
            "priority": 1,
            "description": "Largest volume of private listings",
            "type": "private_dealer"
        },
        "cheki": {
            "name": "Cheki Kenya",
            "status": "active",
            "priority": 2,
            "description": "Dealer-focused listings with detailed specs",
            "type": "dealer"
        },
        "autochek": {
            "name": "Autochek Kenya",
            "status": "active",
            "priority": 3,
            "description": "Quality-inspected premium vehicles",
            "type": "premium_dealer"
        },
        "beepbeep": {
            "name": "BeepBeep Kenya",
            "status": "active",
            "priority": 4,
            "description": "Secondary dealer listings",
            "type": "dealer"
        },
        "pigiame": {
            "name": "PigiaMe Kenya",
            "status": "active",
            "priority": 5,
            "description": "Additional private listings",
            "type": "private"
        }
    }
    
    return {
        "status": "success",
        "sources": sources,
        "total_sources": len(sources),
        "last_scrape": await _get_last_scrape_time()
    }


async def _get_last_scrape_time() -> Optional[str]:
    """Get the last scrape time from the database"""
    try:
        logs = await supabase_service.get_latest_scrape_log()
        if logs:
            return logs.get('scraped_at')
        return None
    except Exception:
        return None


@router.get("/location/factors")
async def get_location_factors() -> Dict:
    """
    Get all location price factors.
    
    Location factors adjust prices based on county:
    - Nairobi: 5% premium (highest demand)
    - Mombasa: 2% premium (coastal market)
    - Other counties: baseline
    """
    try:
        factors = await supabase_service.get_location_factors()
        return {
            "status": "success",
            "factors": factors,
            "count": len(factors),
            "description": "Location factors adjust prices based on county demand"
        }
    except Exception as e:
        logger.error(f"Error fetching location factors: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/location/factors")
async def update_location_factor(
    county: str = Query(..., description="County name"),
    factor: float = Query(..., description="Price factor", ge=0.5, le=2.0)
) -> Dict:
    """
    Update location price factor (admin only).
    
    Factors range from 0.5 to 2.0 where:
    - 1.0 = baseline
    - 1.05 = 5% premium
    - 0.95 = 5% discount
    """
    try:
        result = await supabase_service.update_location_factor(county, factor)
        return {
            "status": "success",
            "county": county,
            "factor": factor,
            "message": f"Location factor for {county} updated to {factor}"
        }
    except Exception as e:
        logger.error(f"Error updating location factor: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/makes")
async def get_makes() -> Dict:
    """
    Get all vehicle makes.
    """
    try:
        makes = await supabase_service.get_all_makes()
        return {
            "status": "success",
            "makes": makes,
            "count": len(makes)
        }
    except Exception as e:
        logger.error(f"Error fetching makes: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/models/{make_id}")
async def get_models_by_make(
    make_id: str = Query(..., description="Make ID")
) -> Dict:
    """
    Get all models for a specific make.
    """
    try:
        models = await supabase_service.get_models_by_make(make_id)
        return {
            "status": "success",
            "models": models,
            "count": len(models)
        }
    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
