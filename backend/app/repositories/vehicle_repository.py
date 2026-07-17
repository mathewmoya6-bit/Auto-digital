# backend/app/repositories/vehicle_repository.py
from typing import List, Optional, Dict, Any
from app.core.database import supabase
import logging

logger = logging.getLogger(__name__)

class VehicleRepository:
    def __init__(self):
        self.table_makes = "vehicle_makes"
        self.table_models = "vehicle_models"
        self.table_variants = "vehicle_variants"
    
    def get_all_makes(self) -> List[Dict[str, Any]]:
        """Get all vehicle makes"""
        try:
            response = supabase.table(self.table_makes).select("*").order("name").execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching makes: {e}")
            return []
    
    def get_make_by_id(self, make_id: str) -> Optional[Dict[str, Any]]:
        """Get make by ID"""
        try:
            response = supabase.table(self.table_makes).select("*").eq("id", make_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching make {make_id}: {e}")
            return None
    
    def get_models_by_make(self, make_id: str) -> List[Dict[str, Any]]:
        """Get models by make ID"""
        try:
            response = supabase.table(self.table_models).select("*").eq("make_id", make_id).order("name").execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching models for make {make_id}: {e}")
            return []
    
    def get_model_by_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model by ID"""
        try:
            response = supabase.table(self.table_models).select("*").eq("id", model_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching model {model_id}: {e}")
            return None
    
    def get_variants_by_model(self, model_id: str) -> List[Dict[str, Any]]:
        """Get variants by model ID"""
        try:
            response = supabase.table(self.table_variants).select("*").eq("model_id", model_id).order("year").execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching variants for model {model_id}: {e}")
            return []
    
    def get_variant_by_id(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """Get variant by ID"""
        try:
            # Join with makes and models to get complete data
            response = supabase.table(self.table_variants)\
                .select("*, vehicle_models(*, vehicle_makes(*))")\
                .eq("id", variant_id)\
                .execute()
            
            if response.data:
                variant = response.data[0]
                # Flatten the structure
                if variant.get("vehicle_models"):
                    model = variant["vehicle_models"]
                    variant["model_id"] = model["id"]
                    variant["model_name"] = model["name"]
                    if model.get("vehicle_makes"):
                        variant["make_id"] = model["vehicle_makes"]["id"]
                        variant["make_name"] = model["vehicle_makes"]["name"]
                return variant
            
            return None
        except Exception as e:
            logger.error(f"Error fetching variant {variant_id}: {e}")
            return None
