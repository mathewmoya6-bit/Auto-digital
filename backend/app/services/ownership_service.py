# backend/app/services/ownership_service.py
"""
Ownership Service - Business logic for ownership cost calculations
"""

from typing import Optional, Dict, Any
from app.repositories.vehicle_repository import VehicleRepository
from app.repositories.ownership_repository import OwnershipRepository
from app.engines.ownership_engine import OwnershipEngine
from app.schemas.request import OwnershipCostRequest
from app.schemas.response import OwnershipCostResponse
import logging

logger = logging.getLogger(__name__)


class OwnershipService:
    """Service for ownership cost calculations"""
    
    def __init__(self):
        self.vehicle_repository = VehicleRepository()
        self.ownership_repository = OwnershipRepository()
        self.engine = OwnershipEngine()
    
    def calculate_ownership_cost(self, request: OwnershipCostRequest) -> Optional[OwnershipCostResponse]:
        """Calculate total cost of ownership"""
        # Get vehicle data
        variant = self.vehicle_repository.get_variant_by_id(request.variant_id)
        if not variant:
            logger.error(f"Variant not found: {request.variant_id}")
            return None
        
        # Calculate ownership cost
        result = self.engine.calculate(variant, request)
        
        # Save report
        try:
            self.ownership_repository.save_ownership_report({
                "user_id": request.user_id if hasattr(request, 'user_id') else None,
                "vehicle_id": request.variant_id,
                "years_owned": request.years_owned,
                "annual_mileage": request.annual_mileage,
                "usage_type": request.usage_type,
                "condition": request.condition,
                "financed": request.financed,
                "purchase_price": result.breakdown.get("purchase_price", 0),
                "resale_value": result.breakdown.get("resale_value", 0),
                "total_cost": result.total_cost,
                "cost_per_km": result.cost_per_km,
                "cost_per_month": result.annual_cost / 12,
                "yearly_breakdown": result.year_by_year
            })
        except Exception as e:
            logger.warning(f"Failed to save ownership report: {e}")
        
        return result
    
    def get_ownership_reports(self, user_id: str, limit: int = 20) -> list:
        """Get ownership reports for a user"""
        return self.ownership_repository.get_ownership_reports(user_id, limit)
