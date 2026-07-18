# backend/app/services/fuel_service.py
"""
Fuel Service - Business logic for fuel price operations
"""

from typing import Optional, List, Dict, Any
from app.repositories.fuel_repository import FuelRepository
from app.repositories.settings_repository import SettingsRepository
import logging

logger = logging.getLogger(__name__)


class FuelService:
    """Service for fuel price operations"""
    
    def __init__(self):
        self.repository = FuelRepository()
        self.settings_repository = SettingsRepository()
    
    def get_all_fuel_prices(self) -> List[Dict[str, Any]]:
        """Get all fuel prices"""
        return self.repository.get_all_fuel_prices()
    
    def get_fuel_price(self, fuel_type: str) -> Optional[Dict[str, Any]]:
        """Get price for a specific fuel type"""
        return self.repository.get_fuel_price(fuel_type)
    
    def get_fuel_prices_by_region(self, region: str) -> List[Dict[str, Any]]:
        """Get fuel prices for a specific region"""
        return self.repository.get_fuel_prices_by_region(region)
    
    def update_fuel_price(self, fuel_type: str, price: float, region: str = None) -> Optional[Dict[str, Any]]:
        """Update a fuel price"""
        if price <= 0:
            raise ValueError("Price must be greater than 0")
        return self.repository.upsert_fuel_price(fuel_type, price, region)
    
    def delete_fuel_price(self, fuel_type: str) -> bool:
        """Delete a fuel price"""
        return self.repository.delete_fuel_price(fuel_type)
    
    def get_fuel_price_history(self, fuel_type: str, limit: int = 30) -> List[Dict[str, Any]]:
        """Get historical fuel prices"""
        return self.repository.get_fuel_price_history(fuel_type, limit)
    
    def get_default_fuel_prices(self) -> Dict[str, float]:
        """Get default fuel prices from settings"""
        return self.settings_repository.get_fuel_prices_from_settings()
    
    def get_current_fuel_price_for_type(self, fuel_type: str) -> float:
        """Get current price for a fuel type, falling back to default"""
        price_data = self.get_fuel_price(fuel_type)
        if price_data:
            return price_data.get("price", 0)
        
        # Fallback to defaults
        defaults = self.get_default_fuel_prices()
        return defaults.get(fuel_type.lower(), 200.00)
