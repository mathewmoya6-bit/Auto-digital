# backend/app/services/valuation_service.py
"""
Valuation Service - Business logic for vehicle valuations
"""

from typing import Dict, Any, Optional, List
from app.repositories.vehicle_repository import VehicleRepository
from app.engines.valuation_engine import ValuationEngine
from app.schemas.request import ValuationRequest
from app.schemas.response import ValuationResponse
import logging

logger = logging.getLogger(__name__)


class ValuationService:
    """Service for vehicle valuation operations"""
    
    def __init__(self):
        self.repository = VehicleRepository()
        self.engine = ValuationEngine()
    
    def get_makes(self) -> List[Dict[str, Any]]:
        """Get all vehicle makes"""
        return self.repository.get_makes()
    
    def get_models_by_make(self, make_id: str) -> List[Dict[str, Any]]:
        """Get models by make ID"""
        return self.repository.get_models_by_make(make_id)
    
    def get_variants_by_model(self, model_id: str) -> List[Dict[str, Any]]:
        """Get variants by model ID"""
        return self.repository.get_variants_by_model(model_id)
    
    def get_variant(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """Get vehicle variant by ID"""
        return self.repository.get_variant_by_id(variant_id)
    
    def search_vehicles(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for vehicles with filters"""
        return self.repository.search_vehicles(query)
    
    def calculate_valuation(self, request: ValuationRequest) -> Optional[ValuationResponse]:
        """Calculate vehicle valuation"""
        # Get vehicle data
        variant = self.repository.get_variant_by_id(request.variant_id)
        if not variant:
            logger.error(f"Variant not found: {request.variant_id}")
            return None
        
        # Calculate valuation
        result = self.engine.calculate_valuation(
            variant=variant,
            year=request.year,
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            previous_owners=request.previous_owners,
            location=request.location,
            service_history=request.service_history
        )
        
        # Build response
        return ValuationResponse(
            variant_id=variant.get("id"),
            make=variant.get("make_name"),
            model=variant.get("model_name"),
            variant=variant.get("name"),
            year=request.year,
            trade_value=result["trade_value"],
            dealer_value=result["dealer_value"],
            retail_value=result["retail_value"],
            quick_sale=result["quick_sale"],
            insurance_value=result["insurance_value"],
            market_value=result["market_value"],
            base_value=result["base_value"],
            depreciation_rate=result["depreciation_rate"],
            estimated_life=result["estimated_life"],
            confidence_score=result["confidence_score"],
            recommendations=result["recommendations"],
            market_adjustments=result["market_adjustments"]
        )
