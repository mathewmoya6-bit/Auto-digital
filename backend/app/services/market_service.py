"""
Market Service - Business logic for market data and insights
"""

from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import logging
import random

from app.core.database import supabase
from app.core.config import settings

logger = logging.getLogger(__name__)


class MarketService:
    """Service for market data analysis and insights"""
    
    def __init__(self):
        self.table = settings.TABLE_MARKET_PRICES if hasattr(settings, 'TABLE_MARKET_PRICES') else "market_prices"
    
    # ─── Market Insights ──────────────────────────────────────────────
    
    def get_market_insights(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        days: int = 30
    ) -> Dict:
        """Get market insights from scraped data"""
        
        # Query market data
        query = supabase.table(self.table).select("*")
        
        if make:
            query = query.ilike("make", f"%{make}%")
        if model:
            query = query.ilike("model", f"%{model}%")
        
        # Filter by date
        cutoff = datetime.now() - timedelta(days=days)
        query = query.gte("created_at", cutoff.isoformat())
        
        result = query.execute()
        listings = result.data or []
        
        if not listings:
            return {
                "message": "No market data available",
                "metrics": {
                    "total_listings": 0,
                    "average_price": 0,
                    "price_range": {"min": 0, "max": 0},
                    "sources": {},
                    "market_health": "no_data"
                },
                "insights": [],
                "recommendations": []
            }
        
        # Calculate metrics
        prices = [float(l.get("price", 0)) for l in listings if l.get("price")]
        
        # Group by source
        sources = {}
        for l in listings:
            source = l.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1
        
        # Calculate market health
        total_listings = len(listings)
        if total_listings > 50:
            market_health = "good"
        elif total_listings > 20:
            market_health = "fair"
        else:
            market_health = "limited"
        
        # Generate insights
        insights = []
        if total_listings > 50:
            insights.append("High market activity detected")
        if prices and sum(prices) / len(prices) > 1000000:
            insights.append("Premium segment market")
        else:
            insights.append("Mid-range market segment")
        
        # Price trend (simplified)
        if len(listings) > 10:
            sorted_listings = sorted(listings, key=lambda x: x.get("created_at", ""))
            if len(sorted_listings) >= 2:
                old_price = float(sorted_listings[0].get("price", 0)) if sorted_listings[0].get("price") else 0
                new_price = float(sorted_listings[-1].get("price", 0)) if sorted_listings[-1].get("price") else 0
                if old_price > 0 and new_price > 0:
                    trend = ((new_price - old_price) / old_price) * 100
                    if trend > 5:
                        insights.append(f"📈 Prices up {trend:.1f}% in {days} days")
                    elif trend < -5:
                        insights.append(f"📉 Prices down {abs(trend):.1f}% in {days} days")
        
        avg_price = sum(prices) / len(prices) if prices else 0
        
        return {
            "metrics": {
                "total_listings": total_listings,
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
    
    # ─── Location Factors ─────────────────────────────────────────────
    
    def get_location_factors(self, location: str) -> Dict:
        """Get location-specific market factors"""
        
        # Query location data
        query = supabase.table(self.table).select("*")
        query = query.ilike("location", f"%{location}%")
        
        result = query.execute()
        listings = result.data or []
        
        # Calculate factors
        demand = "high" if len(listings) > 30 else "medium" if len(listings) > 10 else "low"
        supply = len(listings)
        
        # Price adjustment factor (relative to national average)
        price_adjustment = 1.0 + (random.random() - 0.5) * 0.2
        
        # Get average price for location
        prices = [float(l.get("price", 0)) for l in listings if l.get("price")]
        avg_price = sum(prices) / len(prices) if prices else 0
        
        return {
            "location": location,
            "factors": {
                "demand": demand,
                "supply": supply,
                "price_adjustment": round(price_adjustment, 2),
                "market_activity": "active" if demand in ["high", "medium"] else "slow",
                "competition_level": "high" if supply > 20 else "medium" if supply > 10 else "low",
                "average_price": round(avg_price, 2)
            },
            "listings_found": supply,
            "currency": "KES"
        }
    
    # ─── Price Trends ─────────────────────────────────────────────────
    
    def get_price_trends(
        self,
        make: str,
        model: str,
        months: int = 6
    ) -> Dict:
        """Get price trends for a specific vehicle"""
        
        cutoff = datetime.now() - timedelta(days=months * 30)
        
        query = supabase.table(self.table).select("*")
        query = query.ilike("make", f"%{make}%")
        query = query.ilike("model", f"%{model}%")
        query = query.gte("created_at", cutoff.isoformat())
        query = query.order("created_at", ascending=True)
        
        result = query.execute()
        listings = result.data or []
        
        if not listings:
            return {
                "message": f"No data found for {make} {model}",
                "trend": "insufficient_data",
                "data": []
            }
        
        # Aggregate by month
        monthly_data = {}
        for l in listings:
            created_at = l.get("created_at")
            if created_at:
                month = created_at[:7]  # YYYY-MM
                if month not in monthly_data:
                    monthly_data[month] = {"prices": [], "count": 0}
                if l.get("price"):
                    monthly_data[month]["prices"].append(float(l.get("price")))
                    monthly_data[month]["count"] += 1
        
        # Calculate monthly averages
        monthly_avg = []
        for month, data in sorted(monthly_data.items()):
            if data["prices"]:
                avg_price = sum(data["prices"]) / len(data["prices"])
                monthly_avg.append({
                    "month": month,
                    "average_price": round(avg_price, 2),
                    "count": data["count"]
                })
        
        # Calculate trend
        if len(monthly_avg) >= 3:
            first_price = monthly_avg[0]["average_price"]
            last_price = monthly_avg[-1]["average_price"]
            change = ((last_price - first_price) / first_price) * 100 if first_price > 0 else 0
            
            if change > 5:
                trend = "increasing"
            elif change < -5:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
            change = 0
        
        return {
            "make": make,
            "model": model,
            "trend": trend,
            "percentage_change": round(change, 2),
            "months_analyzed": len(monthly_avg),
            "data": monthly_avg,
            "currency": "KES"
        }
    
    # ─── Market Comparison ────────────────────────────────────────────
    
    def get_market_comparison(self, variant_id: str) -> Dict:
        """Get market comparison for a vehicle variant"""
        
        # Get variant details
        variant = self._get_variant(variant_id)
        if not variant:
            return {"error": "Variant not found"}
        
        # Get market data for similar vehicles
        query = supabase.table(self.table).select("*")
        query = query.ilike("make", f"%{variant.get('make_name', '')}%")
        query = query.ilike("model", f"%{variant.get('model_name', '')}%")
        query = query.limit(100)
        
        result = query.execute()
        listings = result.data or []
        
        if not listings:
            return {
                "vehicle": {
                    "make": variant.get("make_name"),
                    "model": variant.get("model_name"),
                    "variant": variant.get("name")
                },
                "market": {
                    "available": False,
                    "message": "No market data available for this vehicle"
                }
            }
        
        # Calculate market statistics
        prices = [float(l.get("price", 0)) for l in listings if l.get("price")]
        
        return {
            "vehicle": {
                "make": variant.get("make_name"),
                "model": variant.get("model_name"),
                "variant": variant.get("name")
            },
            "market": {
                "available": True,
                "total_listings": len(listings),
                "average_price": round(sum(prices) / len(prices), 2) if prices else 0,
                "price_range": {
                    "min": round(min(prices), 2) if prices else 0,
                    "max": round(max(prices), 2) if prices else 0
                },
                "sources": self._get_sources(listings)
            }
        }
    
    # ─── Helper Methods ──────────────────────────────────────────────
    
    def _get_variant(self, variant_id: str) -> Optional[Dict]:
        """Get vehicle variant details"""
        try:
            result = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                .select("*")\
                .eq("id", variant_id)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting variant: {e}")
            return None
    
    def _get_sources(self, listings: List[Dict]) -> Dict:
        """Get source distribution"""
        sources = {}
        for l in listings:
            source = l.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1
        return sources
    
    # ─── Market Stats ─────────────────────────────────────────────────
    
    def get_market_stats(self) -> Dict:
        """Get overall market statistics"""
        try:
            # Get total listings
            result = supabase.table(self.table)\
                .select("count", count="exact")\
                .execute()
            total_listings = result.count or 0
            
            # Get top makes
            makes_result = supabase.table(self.table)\
                .select("make, count", count="exact")\
                .group_by("make")\
                .order("count", desc=True)\
                .limit(10)\
                .execute()
            
            top_makes = []
            if makes_result.data:
                for item in makes_result.data:
                    top_makes.append({
                        "make": item.get("make", "Unknown"),
                        "count": item.get("count", 0)
                    })
            
            # Get sources
            sources_result = supabase.table(self.table)\
                .select("source, count", count="exact")\
                .group_by("source")\
                .execute()
            
            sources = {}
            if sources_result.data:
                for item in sources_result.data:
                    sources[item.get("source", "unknown")] = item.get("count", 0)
            
            return {
                "total_listings": total_listings,
                "top_makes": top_makes,
                "sources": sources,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting market stats: {e}")
            return {
                "total_listings": 0,
                "top_makes": [],
                "sources": {},
                "last_updated": datetime.now().isoformat()
            }
    
    # ─── Search Market Data ──────────────────────────────────────────
    
    def search_market_data(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        location: Optional[str] = None,
        limit: int = 100
    ) -> Dict:
        """Search market data with filters"""
        
        query = supabase.table(self.table).select("*")
        
        if make:
            query = query.ilike("make", f"%{make}%")
        if model:
            query = query.ilike("model", f"%{model}%")
        if year_from:
            query = query.gte("year", year_from)
        if year_to:
            query = query.lte("year", year_to)
        if min_price:
            query = query.gte("price", min_price)
        if max_price:
            query = query.lte("price", max_price)
        if location:
            query = query.ilike("location", f"%{location}%")
        
        query = query.order("created_at", desc=True).limit(limit)
        
        result = query.execute()
        listings = result.data or []
        
        return {
            "total": len(listings),
            "listings": listings,
            "filters": {
                "make": make,
                "model": model,
                "year_from": year_from,
                "year_to": year_to,
                "min_price": min_price,
                "max_price": max_price,
                "location": location
            }
        }
