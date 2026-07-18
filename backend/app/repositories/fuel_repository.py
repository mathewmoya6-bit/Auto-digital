# backend/app/repositories/fuel_repository.py
"""
Fuel Repository - Data access layer for fuel prices
"""

from typing import Optional, List, Dict, Any
from app.core.database import supabase
import logging

logger = logging.getLogger(__name__)


class FuelRepository:
    """Repository for fuel price operations"""
    
    def __init__(self):
        self.table = "fuel_prices"
    
    def get_all_fuel_prices(self) -> List[Dict[str, Any]]:
        """Get all fuel prices"""
        try:
            response = supabase.table(self.table)\
                .select("*")\
                .order("fuel_type")\
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching fuel prices: {e}")
            return []
    
    def get_fuel_price(self, fuel_type: str) -> Optional[Dict[str, Any]]:
        """Get latest price for a specific fuel type"""
        try:
            response = supabase.table(self.table)\
                .select("*")\
                .eq("fuel_type", fuel_type)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching fuel price for {fuel_type}: {e}")
            return None
    
    def get_fuel_prices_by_region(self, region: str) -> List[Dict[str, Any]]:
        """Get fuel prices for a specific region"""
        try:
            response = supabase.table(self.table)\
                .select("*")\
                .eq("region", region)\
                .order("fuel_type")\
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching fuel prices for region {region}: {e}")
            return []
    
    def upsert_fuel_price(self, fuel_type: str, price: float, region: str = None) -> Optional[Dict[str, Any]]:
        """Insert or update a fuel price"""
        try:
            data = {
                "fuel_type": fuel_type,
                "price": price,
                "currency": "KES",
                "updated_at": "now()"
            }
            if region:
                data["region"] = region
            
            response = supabase.table(self.table)\
                .upsert(data, on_conflict="fuel_type")\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error upserting fuel price for {fuel_type}: {e}")
            return None
    
    def delete_fuel_price(self, fuel_type: str) -> bool:
        """Delete a fuel price"""
        try:
            response = supabase.table(self.table)\
                .delete()\
                .eq("fuel_type", fuel_type)\
                .execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error deleting fuel price for {fuel_type}: {e}")
            return False
    
    def get_fuel_price_history(self, fuel_type: str, limit: int = 30) -> List[Dict[str, Any]]:
        """Get historical fuel prices for a specific type"""
        try:
            response = supabase.table(self.table)\
                .select("*")\
                .eq("fuel_type", fuel_type)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching fuel price history for {fuel_type}: {e}")
            return []
