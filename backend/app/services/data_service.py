"""
Data Service - Central source for all market data
Fetches from scraper data or falls back to database
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
import statistics

from app.core.database import supabase
from app.core.config import settings

logger = logging.getLogger(__name__)


class DataService:
    """Central service for all market data"""
    
    def __init__(self):
        self.cache = {}
        self.cache_expiry = {}
        self.cache_ttl = 3600  # 1 hour
    
    # ─── Fuel Prices ──────────────────────────────────────────────────
    
    def get_fuel_prices(self, fuel_type: Optional[str] = None) -> Dict:
        """Get current fuel prices from database"""
        try:
            query = supabase.table("fuel_prices").select("*")
            
            if fuel_type:
                query = query.eq("fuel_type", fuel_type)
            
            query = query.order("created_at", desc=True).limit(1)
            result = query.execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            # Fallback: get from fuel_types table
            return self._get_fuel_type_default(fuel_type)
            
        except Exception as e:
            logger.error(f"Error getting fuel prices: {e}")
            return self._get_fuel_type_default(fuel_type)
    
    def _get_fuel_type_default(self, fuel_type: Optional[str]) -> Dict:
        """Get default fuel price from fuel_types table"""
        try:
            result = supabase.table("fuel_types")\
                .select("*")\
                .eq("name", fuel_type or "petrol")\
                .execute()
            
            if result.data and len(result.data) > 0:
                return {
                    "fuel_type": fuel_type,
                    "price": result.data[0].get("default_price", 200),
                    "unit": "Litre",
                    "source": "database"
                }
        except Exception:
            pass
        
        # Ultimate fallback
        defaults = {"petrol": 203.47, "diesel": 195.67, "electric": 30.00, "hybrid": 150.00}
        return {
            "fuel_type": fuel_type or "petrol",
            "price": defaults.get(fuel_type or "petrol", 200),
            "unit": "Litre",
            "source": "fallback"
        }
    
    # ─── Market Prices ──────────────────────────────────────────────
    
    def get_market_prices(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        year: Optional[int] = None,
        days: int = 90,
        limit: int = 100
    ) -> List[Dict]:
        """Get market prices from scraper data"""
        try:
            query = supabase.table("market_prices").select("*")
            
            if make:
                query = query.ilike("make", f"%{make}%")
            if model:
                query = query.ilike("model", f"%{model}%")
            if year:
                query = query.eq("year", year)
            
            cutoff = datetime.now() - timedelta(days=days)
            query = query.gte("created_at", cutoff.isoformat())
            query = query.order("created_at", desc=True).limit(limit)
            
            result = query.execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting market prices: {e}")
            return []
    
    def get_market_statistics(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        days: int = 90
    ) -> Dict:
        """Get market statistics from scraper data"""
        listings = self.get_market_prices(make, model, days=days)
        
        if not listings:
            return {
                "total_listings": 0,
                "average_price": 0,
                "median_price": 0,
                "min_price": 0,
                "max_price": 0,
                "sources": {},
                "market_health": "no_data",
                "price_percentiles": {}
            }
        
        prices = [float(l.get("price", 0)) for l in listings if l.get("price", 0) > 0]
        
        if not prices:
            return {
                "total_listings": len(listings),
                "average_price": 0,
                "median_price": 0,
                "min_price": 0,
                "max_price": 0,
                "sources": {},
                "market_health": "no_data",
                "price_percentiles": {}
            }
        
        # Group by source
        sources = {}
        for l in listings:
            source = l.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1
        
        # Calculate percentiles
        sorted_prices = sorted(prices)
        percentiles = {
            "p10": sorted_prices[int(len(sorted_prices) * 0.1)] if len(sorted_prices) > 10 else 0,
            "p25": sorted_prices[int(len(sorted_prices) * 0.25)] if len(sorted_prices) > 4 else 0,
            "p50": sorted_prices[int(len(sorted_prices) * 0.5)] if len(sorted_prices) > 2 else 0,
            "p75": sorted_prices[int(len(sorted_prices) * 0.75)] if len(sorted_prices) > 4 else 0,
            "p90": sorted_prices[int(len(sorted_prices) * 0.9)] if len(sorted_prices) > 10 else 0,
        }
        
        total_listings = len(listings)
        if total_listings > 50:
            health = "good"
        elif total_listings > 20:
            health = "fair"
        elif total_listings > 5:
            health = "limited"
        else:
            health = "sparse"
        
        return {
            "total_listings": total_listings,
            "average_price": round(sum(prices) / len(prices), 2),
            "median_price": round(statistics.median(prices), 2),
            "min_price": round(min(prices), 2),
            "max_price": round(max(prices), 2),
            "sources": sources,
            "market_health": health,
            "price_percentiles": percentiles,
            "last_updated": datetime.now().isoformat()
        }
    
    def get_location_factors(self, location: str) -> Dict:
        """Get location-specific factors from database"""
        try:
            result = supabase.table("location_factors")\
                .select("*")\
                .eq("location", location.lower())\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            # Default factors
            return {
                "location": location,
                "price_adjustment": 1.0,
                "demand_index": 1.0,
                "supply_index": 1.0,
                "insurance_multiplier": 1.0,
                "parking_cost": 200
            }
        except Exception as e:
            logger.error(f"Error getting location factors: {e}")
            return {
                "location": location,
                "price_adjustment": 1.0,
                "demand_index": 1.0,
                "supply_index": 1.0,
                "insurance_multiplier": 1.0,
                "parking_cost": 200
            }
    
    # ─── Vehicle Data ──────────────────────────────────────────────────
    
    def get_vehicle_parameters(self, variant_id: str) -> Dict:
        """Get vehicle parameters from database"""
        try:
            result = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                .select("*")\
                .eq("id", variant_id)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return {}
        except Exception as e:
            logger.error(f"Error getting vehicle parameters: {e}")
            return {}
    
    def get_vehicle_type_parameters(self, body_type: str) -> Dict:
        """Get vehicle type parameters from database"""
        try:
            result = supabase.table("vehicle_type_parameters")\
                .select("*")\
                .eq("body_type", body_type.lower())\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            # Default parameters
            return {
                "body_type": body_type,
                "depreciation_rate": 0.15,
                "maintenance_multiplier": 1.0,
                "tyre_multiplier": 1.0,
                "insurance_multiplier": 1.0,
                "fuel_multiplier": 1.0
            }
        except Exception as e:
            logger.error(f"Error getting vehicle type parameters: {e}")
            return {
                "body_type": body_type,
                "depreciation_rate": 0.15,
                "maintenance_multiplier": 1.0,
                "tyre_multiplier": 1.0,
                "insurance_multiplier": 1.0,
                "fuel_multiplier": 1.0
            }
    
    # ─── Cost Parameters ──────────────────────────────────────────────
    
    def get_cost_parameters(self, category: str) -> Dict:
        """Get cost parameters from database"""
        try:
            result = supabase.table("cost_parameters")\
                .select("*")\
                .eq("category", category)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return {}
        except Exception as e:
            logger.error(f"Error getting cost parameters: {e}")
            return {}
    
    def get_insurance_rates(self, vehicle_type: str) -> Dict:
        """Get insurance rates from database"""
        try:
            result = supabase.table("insurance_rates")\
                .select("*")\
                .eq("vehicle_type", vehicle_type.lower())\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            return {
                "vehicle_type": vehicle_type,
                "comprehensive_rate": 0.045,
                "third_party_fee": 7000,
                "location_multiplier": 1.0
            }
        except Exception as e:
            logger.error(f"Error getting insurance rates: {e}")
            return {
                "vehicle_type": vehicle_type,
                "comprehensive_rate": 0.045,
                "third_party_fee": 7000,
                "location_multiplier": 1.0
            }
    
    def get_service_intervals(self, vehicle_type: str) -> Dict:
        """Get service intervals from database"""
        try:
            result = supabase.table("service_intervals")\
                .select("*")\
                .eq("vehicle_type", vehicle_type.lower())\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            return {
                "vehicle_type": vehicle_type,
                "interval_km": 10000,
                "base_cost": 15000,
                "major_interval_km": 40000,
                "major_cost": 45000
            }
        except Exception as e:
            logger.error(f"Error getting service intervals: {e}")
            return {
                "vehicle_type": vehicle_type,
                "interval_km": 10000,
                "base_cost": 15000,
                "major_interval_km": 40000,
                "major_cost": 45000
            }
    
    def get_depreciation_rates(self, vehicle_class: str) -> Dict:
        """Get depreciation rates from database"""
        try:
            result = supabase.table("depreciation_rates")\
                .select("*")\
                .eq("vehicle_class", vehicle_class)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            return {
                "vehicle_class": vehicle_class,
                "year_1": 0.15,
                "year_2": 0.12,
                "year_3": 0.10,
                "year_4": 0.08,
                "year_5": 0.07,
                "year_6_plus": 0.06
            }
        except Exception as e:
            logger.error(f"Error getting depreciation rates: {e}")
            return {
                "vehicle_class": vehicle_class,
                "year_1": 0.15,
                "year_2": 0.12,
                "year_3": 0.10,
                "year_4": 0.08,
                "year_5": 0.07,
                "year_6_plus": 0.06
            }
