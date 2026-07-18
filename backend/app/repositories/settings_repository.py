# backend/app/repositories/settings_repository.py
"""
Settings Repository - Data access layer for application settings
"""

from typing import Optional, Dict, Any
from app.core.database import supabase
import logging
import json

logger = logging.getLogger(__name__)


class SettingsRepository:
    """Repository for settings operations"""
    
    def __init__(self):
        self.table = "settings"
    
    def get_setting(self, key: str) -> Optional[Any]:
        """Get a setting by key"""
        try:
            response = supabase.table(self.table)\
                .select("value")\
                .eq("key", key)\
                .execute()
            if response.data:
                return response.data[0].get("value")
            return None
        except Exception as e:
            logger.error(f"Error fetching setting {key}: {e}")
            return None
    
    def get_engine_settings(self) -> Dict[str, Any]:
        """Get all engine settings"""
        try:
            response = supabase.table(self.table)\
                .select("value")\
                .eq("key", "engine_settings")\
                .execute()
            if response.data:
                value = response.data[0].get("value", {})
                if isinstance(value, str):
                    try:
                        return json.loads(value)
                    except:
                        return {}
                return value or {}
            
            # Return defaults if not found
            return {
                "depreciation_rate": 0.15,
                "insurance_rate": 0.045,
                "annual_mileage": 20000,
                "tyre_lifespan": 45000,
                "service_interval": 10000,
                "fuel_price_petrol": 214.03,
                "fuel_price_diesel": 222.86,
                "fuel_price_electric": 30.00,
                "fuel_price_lpg": 120.00
            }
        except Exception as e:
            logger.error(f"Error fetching engine settings: {e}")
            return {}
    
    def update_engine_settings(self, settings: Dict[str, Any]) -> bool:
        """Update engine settings"""
        try:
            # Convert to JSON if needed
            value = settings
            if not isinstance(value, str):
                value = json.dumps(settings)
            
            response = supabase.table(self.table)\
                .upsert({
                    "key": "engine_settings",
                    "value": value,
                    "updated_at": "now()"
                }, on_conflict="key")\
                .execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error updating engine settings: {e}")
            return False
    
    def get_fuel_prices_from_settings(self) -> Dict[str, float]:
        """Get fuel prices from settings"""
        settings = self.get_engine_settings()
        return {
            "petrol": settings.get("fuel_price_petrol", 214.03),
            "diesel": settings.get("fuel_price_diesel", 222.86),
            "electric": settings.get("fuel_price_electric", 30.00),
            "lpg": settings.get("fuel_price_lpg", 120.00)
        }
    
    def get_valuation_settings(self) -> Dict[str, Any]:
        """Get valuation-specific settings"""
        try:
            response = supabase.table(self.table)\
                .select("value")\
                .eq("key", "valuation_settings")\
                .execute()
            if response.data:
                value = response.data[0].get("value", {})
                if isinstance(value, str):
                    try:
                        return json.loads(value)
                    except:
                        return {}
                return value or {}
            
            # Return defaults
            return {
                "depreciation_rates": {
                    "SUV_A": 0.08,
                    "SUV_B": 0.10,
                    "SUV_C": 0.13,
                    "SUV_D": 0.16,
                    "SEDAN_A": 0.07,
                    "SEDAN_B": 0.09,
                    "SEDAN_C": 0.12,
                    "SEDAN_D": 0.15,
                    "PICKUP_A": 0.09,
                    "PICKUP_B": 0.11,
                    "PICKUP_C": 0.14,
                    "LUXURY_A": 0.15,
                    "LUXURY_B": 0.20,
                    "LUXURY_C": 0.25
                },
                "condition_multipliers": {
                    "excellent": 1.10,
                    "very_good": 1.05,
                    "good": 1.00,
                    "fair": 0.85,
                    "poor": 0.70
                },
                "location_multipliers": {
                    "nairobi": 1.05,
                    "mombasa": 0.98,
                    "kisumu": 0.95,
                    "nakuru": 0.97,
                    "eldoret": 0.96,
                    "other": 0.95
                }
            }
        except Exception as e:
            logger.error(f"Error fetching valuation settings: {e}")
            return {}
