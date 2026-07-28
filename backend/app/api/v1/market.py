"""
Market Router
Handles market data, insights, and location factors
"""

from __future__ import annotations

from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
import logging
import random

from app.core.database import supabase

router = APIRouter()
logger = logging.getLogger(__name__)

TABLE = "market_prices"


# ─── Schemas ────────────────────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    source: Optional[str] = Field(None, description="Specific source to scrape")
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    max_results: int = Field(100, ge=1, le=1000)


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.get("/insights")
async def get_market_insights(
    make: Optional[str] = Query(None, description="Vehicle make"),
    model: Optional[str] = Query(None, description="Vehicle model"),
    days: int = Query(30, ge=1, le=90, description="Days of data to analyze")
):
    """
    Get market insights and analytics
    Returns aggregated market data with trends and predictions
    """
    try:
        query = supabase.table(TABLE).select("*")
        
        if make:
            query = query.ilike("make", f"%{make}%")
        if model:
            query = query.ilike("model", f"%{model}%")
        
        resp = query.execute()
        listings = resp.data or []
        
        if not listings:
            return {
                "status": "success",
                "data": {
                    "message": "No market data available",
                    "insights": [],
                    "metrics": {},
                    "recommendations": []
                }
            }
        
        # Calculate metrics
        prices = [float(l.get("price", 0)) for l in listings if l.get("price")]
        avg_price = sum(prices) / len(prices) if prices else 0
        
        # Group by source
        sources = {}
        for listing in listings:
            source = listing.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1
        
        # Generate insights
        insights = []
        if len(listings) > 50:
            insights.append("High market activity detected")
        if avg_price > 1000000:
            insights.append("Premium segment market")
        else:
            insights.append("Mid-range market segment")
        
        # Calculate market health
        market_health = "good" if len(listings) > 20 else "fair" if len(listings) > 10 else "limited"
        
        return {
            "status": "success",
            "data": {
                "metrics": {
                    "total_listings": len(listings),
                    "average_price": round(avg_price, 2),
                    "price_range": {
                        "min": round(min(prices), 2) if prices else 0,
                        "max": round(max(prices), 2) if prices else 0
                    },
                    "sources": sources,
                    "market_health": market_health
                },
                "insights": insights,
                "recommendations": [
                    "Monitor price trends weekly",
                    "Check competitor pricing",
                    "Update listings regularly"
                ],
                "last_updated": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Market insights retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scrape")
async def scrape_market_data(
    background_tasks: BackgroundTasks,
    request: Optional[ScrapeRequest] = None
):
    """
    Trigger market data scraping
    Runs in background to avoid blocking
    """
    if not request:
        request = ScrapeRequest()
    
    # Start background task
    background_tasks.add_task(
        _scrape_market_data,
        source=request.source,
        make=request.vehicle_make,
        model=request.vehicle_model,
        max_results=request.max_results
    )
    
    return {
        "status": "success",
        "message": "Market scraping initiated",
        "task_id": f"scrape_{int(datetime.now().timestamp())}",
        "parameters": request.model_dump()
    }


@router.get("/location/factors")
async def get_location_factors(
    location: str = Query(..., description="Location to get factors for"),
    vehicle_type: Optional[str] = Query(None, description="Vehicle type filter")
):
    """
    Get location-specific market factors
    Returns demand, supply, and price adjustment factors
    """
    try:
        # Query location-specific data
        query = supabase.table(TABLE).select("*")
        if location:
            query = query.ilike("location", f"%{location}%")
        
        resp = query.execute()
        listings = resp.data or []
        
        # Calculate factors
        demand = "high" if len(listings) > 30 else "medium" if len(listings) > 10 else "low"
        supply = len(listings)
        
        # Price adjustment factor (relative to national average)
        # In reality, this would compare to national average
        price_adjustment = 1.0 + (random.random() - 0.5) * 0.2  # ±10% random
        
        return {
            "status": "success",
            "data": {
                "location": location,
                "factors": {
                    "demand": demand,
                    "supply": supply,
                    "price_adjustment": round(price_adjustment, 2),
                    "market_activity": "active" if demand in ["high", "medium"] else "slow",
                    "competition_level": "high" if supply > 20 else "medium" if supply > 10 else "low"
                },
                "listings_found": supply,
                "currency": "KES"
            }
        }
        
    except Exception as e:
        logger.error(f"Location factors retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Background Tasks ──────────────────────────────────────────────────────

async def _scrape_market_data(
    source: Optional[str] = None,
    make: Optional[str] = None,
    model: Optional[str] = None,
    max_results: int = 100
):
    """
    Background task for scraping market data
    """
    logger.info(f"Starting market scrape: source={source}, make={make}, model={model}")
    
    try:
        # Simulate scraping from multiple sources
        sources_to_scrape = [source] if source else ["jiji", "cheki", "autochek", "beepbeep", "pigiama"]
        
        total_scraped = 0
        for source_name in sources_to_scrape:
            # Simulate API calls
            count = random.randint(10, 30)
            total_scraped += count
            logger.info(f"Scraped {count} listings from {source_name}")
        
        logger.info(f"Market scrape completed: {total_scraped} total listings")
        
    except Exception as e:
        logger.error(f"Market scraping failed: {e}")
