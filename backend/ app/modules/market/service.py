# app/modules/market/service.py
# Auto-D Kenya - Market Service
# ================================================================
# TYPE: MODULE - Market business logic

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.core.database import get_supabase
from app.modules.market.pricing import PricingEngine
from app.modules.market.statistics import MarketStatistics

logger = logging.getLogger(__name__)


class MarketService:
    """Market service for business logic."""
    
    def __init__(self):
        self.supabase = get_supabase()
        self.pricing = PricingEngine()
        self.statistics = MarketStatistics()
    
    async def get_market_insights(self, make: str = None, model: str = None) -> Dict[str, Any]:
        """Get market insights."""
        try:
            query = self.supabase.table("market_prices").select("*")
            if make:
                query = query.eq("make", make)
            if model:
                query = query.eq("model", model)
            
            response = query.execute()
            data = response.data
            
            if not data:
                return {
                    "total_listings": 0,
                    "average_price": 0,
                    "price_range": {"min": 0, "max": 0},
                    "insights": []
                }
            
            prices = [float(item.get("avg_price", 0)) for item in data if item.get("avg_price")]
            
            return {
                "total_listings": len(data),
                "average_price": sum(prices) / len(prices) if prices else 0,
                "price_range": {
                    "min": min(prices) if prices else 0,
                    "max": max(prices) if prices else 0
                },
                "makes": list(set(item.get("make") for item in data if item.get("make"))),
                "updated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting market insights: {str(e)}")
            return {"error": str(e)}
    
    async def get_market_prices(self, make: str, model: str, year: int = None) -> Dict[str, Any]:
        """Get market prices for a vehicle."""
        try:
            query = self.supabase.table("market_prices").select("*").eq("make", make).eq("model", model)
            if year:
                query = query.eq("year", year)
            
            response = query.execute()
            data = response.data
            
            if not data:
                return {"message": "No data found"}
            
            prices = [float(item.get("avg_price", 0)) for item in data if item.get("avg_price")]
            
            return {
                "make": make,
                "model": model,
                "year": year,
                "listings": len(data),
                "average_price": sum(prices) / len(prices) if prices else 0,
                "min_price": min(prices) if prices else 0,
                "max_price": max(prices) if prices else 0,
                "sources": list(set(item.get("source") for item in data if item.get("source"))),
                "updated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting market prices: {str(e)}")
            return {"error": str(e)}
    
    async def get_market_trends(self, make: str, model: str, period: str = "90d") -> Dict[str, Any]:
        """Get market trends for a vehicle."""
        try:
            # Calculate trend data
            trend_data = await self.statistics.calculate_trends(make, model, period)
            return trend_data
            
        except Exception as e:
            logger.error(f"Error getting market trends: {str(e)}")
            return {"error": str(e)}
    
    async def get_location_factors(self, location: str) -> Dict[str, Any]:
        """Get location factors for valuation."""
        factors = {
            "nairobi": 1.05, "mombasa": 1.02, "kisumu": 1.00,
            "nakuru": 1.00, "eldoret": 1.00, "thika": 1.00,
            "kiambu": 1.02, "kajiado": 1.00, "machakos": 1.00,
            "meru": 0.98, "nyeri": 0.98, "embu": 0.97,
            "malindi": 1.02, "nanyuki": 1.01, "other": 1.00
        }
        
        factor = factors.get(location.lower(), 1.00)
        
        return {
            "location": location,
            "factor": factor,
            "description": f"Price adjustment factor for {location}",
            "updated_at": datetime.utcnow().isoformat()
        }
    
    async def get_source_status(self) -> Dict[str, Any]:
        """Get status of all market data sources."""
        sources = {
            "jiji": {"status": "active", "last_scrape": None, "listings": 0},
            "cheki": {"status": "active", "last_scrape": None, "listings": 0},
            "autochek": {"status": "active", "last_scrape": None, "listings": 0}
        }
        
        try:
            # Get latest scrape data
            response = self.supabase.table("scraper_jobs").select("*").order("created_at", desc=True).limit(3).execute()
            for job in response.data:
                source = job.get("source")
                if source in sources:
                    sources[source]["last_scrape"] = job.get("created_at")
                    sources[source]["listings"] = job.get("listings_count", 0)
                    
        except Exception as e:
            logger.error(f"Error getting source status: {str(e)}")
        
        return {"sources": sources, "updated_at": datetime.utcnow().isoformat()}
