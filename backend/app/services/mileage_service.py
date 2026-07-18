# backend/app/services/mileage_service.py
"""
Mileage Service - Business logic for mileage calculations
"""

from typing import Optional, Dict, Any
from app.repositories.vehicle_repository import VehicleRepository
from app.repositories.mileage_repository import MileageRepository
from app.repositories.fuel_repository import FuelRepository
from app.engines.mileage_rate_engine import MileageRateEngine
from app.schemas.request import MileageRateRequest
from app.schemas.response import MileageRateResponse
import logging

logger = logging.getLogger(__name__)


class MileageService:
    """Service for mileage rate calculations"""
    
    def __init__(self):
        self.vehicle_repository = VehicleRepository()
        self.mileage_repository = MileageRepository()
        self.fuel_repository = FuelRepository()
        self.engine = MileageRateEngine()
    
    def calculate_mileage_rate(self, request: MileageRateRequest) -> Optional[MileageRateResponse]:
        """Calculate mileage rate for a vehicle"""
        # Get vehicle data
        variant = self.vehicle_repository.get_variant_by_id(request.variant_id)
        if not variant:
            logger.error(f"Variant not found: {request.variant_id}")
            return None
        
        # Get fuel price if not provided
        fuel_price = request.fuel_price
        if not fuel_price:
            fuel_type = variant.get("fuel_type", "petrol")
            fuel_price = self.fuel_repository.get_fuel_price(fuel_type)
            if fuel_price:
                fuel_price = fuel_price.get("price", 200.00)
            else:
                fuel_price = 200.00  # Default fallback
        
        # Calculate mileage rate
        result = self.engine.calculate(variant, request)
        
        # Save report
        try:
            self.mileage_repository.save_mileage_report({
                "user_id": request.user_id if hasattr(request, 'user_id') else None,
                "vehicle_id": request.variant_id,
                "trip_distance": request.distance,
                "trip_type": request.trip_type,
                "driving_style": request.driving_style,
                "total_cost": result.total_running_cost,
                "cost_per_km": result.total_rate,
                "fuel_price": fuel_price,
                "components": {
                    "fuel": result.fuel_rate * request.distance,
                    "maintenance": result.maintenance_rate * request.distance,
                    "tyres": result.tyre_rate * request.distance,
                    "insurance": result.insurance_rate * request.distance,
                    "depreciation": result.depreciation_rate * request.distance,
                    "finance": result.finance_rate * request.distance,
                    "misc": result.misc_rate * request.distance
                }
            })
        except Exception as e:
            logger.warning(f"Failed to save mileage report: {e}")
        
        return result
    
    def get_mileage_reports(self, user_id: str, limit: int = 20) -> list:
        """Get mileage reports for a user"""
        return self.mileage_repository.get_mileage_reports(user_id, limit)
    
    def get_mileage_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific mileage report"""
        return self.mileage_repository.get_mileage_report(report_id)
