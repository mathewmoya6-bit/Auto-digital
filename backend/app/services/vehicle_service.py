# backend/app/services/vehicle_service.py
from typing import List, Optional, Dict, Any
from app.core.database import supabase
from app.models.vehicle import VehicleMake, VehicleModel, VehicleVariant
from app.repositories.vehicle_repository import VehicleRepository
from app.schemas.response import VehicleDetailResponse

class VehicleService:
    def __init__(self):
        self.repository = VehicleRepository()
    
    def get_makes(self) -> List[Dict[str, Any]]:
        """Get all vehicle makes"""
        return self.repository.get_all_makes()
    
    def get_models_by_make(self, make_id: str) -> List[Dict[str, Any]]:
        """Get models by make ID"""
        return self.repository.get_models_by_make(make_id)
    
    def get_variants_by_model(self, model_id: str) -> List[Dict[str, Any]]:
        """Get variants by model ID"""
        return self.repository.get_variants_by_model(model_id)
    
    def get_variant(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """Get variant by ID"""
        return self.repository.get_variant_by_id(variant_id)
    
    def get_vehicle_details(self, variant_id: str) -> Optional[VehicleDetailResponse]:
        """Get complete vehicle details with all specifications"""
        variant = self.repository.get_variant_by_id(variant_id)
        if not variant:
            return None
        
        # Get make and model information
        make = self.repository.get_make_by_id(variant.get("make_id"))
        model = self.repository.get_model_by_id(variant.get("model_id"))
        
        return VehicleDetailResponse(
            variant_id=variant["id"],
            make=make["name"] if make else None,
            model=model["name"] if model else None,
            variant=variant["name"],
            year=variant["year"],
            engine_cc=variant["engine_cc"],
            fuel_type=variant["fuel_type"],
            transmission=variant["transmission"],
            fuel_consumption=variant["fuel_consumption"],
            insurance_group=variant["insurance_group"],
            service_interval=variant["service_interval"],
            tyre_size=variant.get("tyre_size"),
            market_value=variant["market_value"],
            depreciation_class=variant["depreciation_class"],
            tyre_cost=variant["tyre_cost"],
            service_cost=variant["service_cost"]
        )
