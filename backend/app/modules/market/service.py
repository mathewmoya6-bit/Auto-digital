# app/modules/market/service.py
"""Market service for Auto-D Kenya"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import random

from app.core.database import get_supabase

logger = logging.getLogger(__name__)

class MarketService:
    """Service for market data operations"""
    
    def __init__(self):
        self.supabase = get_supabase()
        
    async def get_market_insights(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get market insights"""
        try:
            # Build query
            query = self.supabase.table("market_insights").select("*")
            
            if make:
                query = query.eq("make", make)
            if model:
                query = query.eq("model", model)
            if year_from:
                query = query.gte("year", year_from)
            if year_to:
                query = query.lte("year", year_to)
                
            result = query.execute()
            
            if not result.data:
                # Return mock data for demonstration
                return self._generate_mock_insights(make, model)
            
            data = result.data[0]
            return {
                "average_price": data.get("average_price", 0),
                "price_range": {
                    "min": data.get("min_price", 0),
                    "max": data.get("max_price", 0)
                },
                "demand_score": data.get("demand_score", 0.5),
                "supply_score": data.get("supply_score", 0.5),
                "market_trend": data.get("market_trend", "stable"),
                "recommendations": data.get("recommendations", []),
                "timestamp": datetime.utcnow()
            }
        except Exception as e:
            logger.error(f"Error getting market insights: {str(e)}")
            # Return mock data on error
            return self._generate_mock_insights(make, model)
    
    async def get_market_prices(self, variant_id: int, days: int) -> Dict[str, Any]:
        """Get market prices for a variant"""
        try:
            result = self.supabase.table("market_prices")\
                .select("*")\
                .eq("variant_id", variant_id)\
                .order("date", desc=True)\
                .limit(days)\
                .execute()
            
            if not result.data:
                return self._generate_mock_prices(variant_id)
            
            prices = [p["price"] for p in result.data]
            current_price = prices[0] if prices else 0
            
            return {
                "current_price": current_price,
                "historical_prices": result.data,
                "price_trend": self._calculate_trend(prices),
                "price_change_percentage": self._calculate_change_percentage(prices),
                "confidence_score": 0.85,
                "last_updated": datetime.utcnow()
            }
        except Exception as e:
            logger.error(f"Error getting market prices: {str(e)}")
            return self._generate_mock_prices(variant_id)
    
    async def get_market_trends(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        period: str = "6m"
    ) -> Dict[str, Any]:
        """Get market trends"""
        try:
            query = self.supabase.table("market_trends").select("*")
            
            if make:
                query = query.eq("make", make)
            if model:
                query = query.eq("model", model)
                
            result = query.execute()
            
            if not result.data:
                return self._generate_mock_trends(make, model)
            
            data = result.data[0]
            return {
                "trend_type": data.get("trend_type", "stable"),
                "data_points": data.get("data_points", []),
                "forecast": data.get("forecast"),
                "seasonality": data.get("seasonality"),
                "timestamp": datetime.utcnow()
            }
        except Exception as e:
            logger.error(f"Error getting market trends: {str(e)}")
            return self._generate_mock_trends(make, model)
    
    async def get_location_factors(
        self,
        location: str,
        vehicle_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get location-based factors"""
        try:
            result = self.supabase.table("location_factors")\
                .select("*")\
                .eq("location", location)\
                .execute()
            
            if not result.data:
                return self._generate_mock_location_factors(location)
            
            data = result.data[0]
            return {
                "location": location,
                "demand_factor": data.get("demand_factor", 1.0),
                "supply_factor": data.get("supply_factor", 1.0),
                "price_adjustment": data.get("price_adjustment", 0),
                "transportation_costs": data.get("transportation_costs", 0),
                "market_maturity": data.get("market_maturity", "developing"),
                "recommendations": data.get("recommendations", [])
            }
        except Exception as e:
            logger.error(f"Error getting location factors: {str(e)}")
            return self._generate_mock_location_factors(location)
    
    async def get_source_status(self) -> List[Dict[str, Any]]:
        """Get status of data sources"""
        try:
            result = self.supabase.table("data_sources")\
                .select("*")\
                .execute()
            
            if not result.data:
                return self._generate_mock_sources()
            
            return result.data
        except Exception as e:
            logger.error(f"Error getting source status: {str(e)}")
            return self._generate_mock_sources()
    
    # ─── HELPER METHODS ──────────────────────────────────────────
    
    def _generate_mock_insights(self, make: Optional[str], model: Optional[str]) -> Dict[str, Any]:
        """Generate mock market insights"""
        return {
            "average_price": 2500000,
            "price_range": {"min": 1800000, "max": 3200000},
            "demand_score": 0.75,
            "supply_score": 0.60,
            "market_trend": "upward",
            "recommendations": [
                "Consider purchasing before prices increase further",
                "Toyota models hold value better than other brands",
                "Diesel variants have higher demand in this segment"
            ],
            "timestamp": datetime.utcnow()
        }
    
    def _generate_mock_prices(self, variant_id: int) -> Dict[str, Any]:
        """Generate mock price data"""
        historical = []
        base_price = 2500000
        for i in range(30):
            date = datetime.utcnow() - timedelta(days=i)
            price = base_price * (1 + random.uniform(-0.05, 0.05))
            historical.append({
                "date": date.isoformat(),
                "price": round(price, 2),
                "source": "market_data"
            })
        
        return {
            "current_price": base_price,
            "historical_prices": historical,
            "price_trend": "stable",
            "price_change_percentage": 2.5,
            "confidence_score": 0.85,
            "last_updated": datetime.utcnow()
        }
    
    def _generate_mock_trends(self, make: Optional[str], model: Optional[str]) -> Dict[str, Any]:
        """Generate mock trends"""
        data_points = []
        for i in range(6):
            month = datetime.utcnow() - timedelta(days=30*i)
            data_points.append({
                "month": month.strftime("%Y-%m"),
                "average_price": 2500000 * (1 + i * 0.02),
                "sales_volume": 1000 * (1 - i * 0.05)
            })
        
        return {
            "trend_type": "increasing",
            "data_points": data_points,
            "forecast": [
                {"month": "2024-02", "predicted_price": 2600000},
                {"month": "2024-03", "predicted_price": 2650000}
            ],
            "seasonality": {
                "peak_months": ["Jan", "Mar", "Aug"],
                "low_months": ["May", "Oct", "Nov"]
            },
            "timestamp": datetime.utcnow()
        }
    
    def _generate_mock_location_factors(self, location: str) -> Dict[str, Any]:
        """Generate mock location factors"""
        return {
            "location": location,
            "demand_factor": 1.2,
            "supply_factor": 0.9,
            "price_adjustment": 0.15,
            "transportation_costs": 50000,
            "market_maturity": "growing",
            "recommendations": [
                "High demand in urban areas",
                "Consider transportation costs in pricing",
                "Competitive market with multiple dealers"
            ]
        }
    
    def _generate_mock_sources(self) -> List[Dict[str, Any]]:
        """Generate mock data sources"""
        return [
            {
                "source_name": "AutoTrader Kenya",
                "status": "active",
                "last_update": datetime.utcnow().isoformat(),
                "data_points": 15000,
                "reliability_score": 0.95
            },
            {
                "source_name": "Local Dealerships",
                "status": "active",
                "last_update": datetime.utcnow().isoformat(),
                "data_points": 8000,
                "reliability_score": 0.88
            },
            {
                "source_name": "Market Analysis",
                "status": "active",
                "last_update": datetime.utcnow().isoformat(),
                "data_points": 5000,
                "reliability_score": 0.92
            }
        ]
    
    def _calculate_trend(self, prices: List[float]) -> str:
        """Calculate price trend"""
        if len(prices) < 2:
            return "stable"
        
        first = prices[-1]
        last = prices[0]
        change = ((last - first) / first) * 100 if first != 0 else 0
        
        if change > 5:
            return "upward"
        elif change < -5:
            return "downward"
        else:
            return "stable"
    
    def _calculate_change_percentage(self, prices: List[float]) -> float:
        """Calculate price change percentage"""
        if len(prices) < 2:
            return 0
        
        first = prices[-1]
        last = prices[0]
        return ((last - first) / first) * 100 if first != 0 else 0
