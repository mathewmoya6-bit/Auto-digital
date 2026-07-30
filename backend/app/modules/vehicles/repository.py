# app/modules/vehicles/repository.py
# Auto-D Kenya - Vehicles Repository
# ================================================================
# TYPE: MODULE - Vehicles database operations

import logging
from typing import Optional, List, Dict, Any
from uuid import uuid4

from app.core.database import get_supabase
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)


class VehicleRepository:
    """Vehicle repository for database operations."""
    
    def __init__(self):
        self.supabase = get_supabase()
    
    async def create(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new vehicle."""
        try:
            vehicle_data = {
                "id": str(uuid4()),
                "user_id": user_id,
                "plate": data.get("plate", "").upper(),
                "make_model": data.get("make_model"),
                "vin": data.get("vin"),
                "year": data.get("year"),
                "mileage": data.get("mileage", 0),
                "created_at": data.get("created_at")
            }
            response = self.supabase.table("vehicles").insert(vehicle_data).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Error creating vehicle: {str(e)}")
            raise
    
    async def get_by_id(self, vehicle_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get vehicle by ID."""
        try:
            response = self.supabase.table("vehicles").select("*").eq("id", vehicle_id).eq("user_id", user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting vehicle: {str(e)}")
            return None
    
    async def get_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all vehicles for a user."""
        try:
            response = self.supabase.table("vehicles").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting user vehicles: {str(e)}")
            return []
    
    async def update(self, vehicle_id: str, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a vehicle."""
        try:
            response = self.supabase.table("vehicles").update(data).eq("id", vehicle_id).eq("user_id", user_id).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Error updating vehicle: {str(e)}")
            raise
    
    async def delete(self, vehicle_id: str, user_id: str) -> bool:
        """Delete a vehicle."""
        try:
            response = self.supabase.table("vehicles").delete().eq("id", vehicle_id).eq("user_id", user_id).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error deleting vehicle: {str(e)}")
            return False
    
    async def get_makes(self, category_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all vehicle makes."""
        try:
            query = self.supabase.table("vehicle_makes").select("*").eq("active", True)
            if category_id:
                query = query.eq("category_id", category_id)
            response = query.order("make_name").execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting makes: {str(e)}")
            return []
    
    async def get_models(self, make_id: str) -> List[Dict[str, Any]]:
        """Get models for a make."""
        try:
            response = self.supabase.table("vehicle_models").select("*").eq("make_id", make_id).eq("active", True).order("model_name").execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting models: {str(e)}")
            return []
    
    async def get_generations(self, model_id: str) -> List[Dict[str, Any]]:
        """Get generations for a model."""
        try:
            response = self.supabase.table("vehicle_generations").select("*").eq("model_id", model_id).eq("active", True).order("generation_start_year", desc=True).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting generations: {str(e)}")
            return []
    
    async def get_variants(self, generation_id: str) -> List[Dict[str, Any]]:
        """Get variants for a generation."""
        try:
            response = self.supabase.table("vehicle_variants").select("*").eq("generation_id", generation_id).eq("active", True).order("variant_name").execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting variants: {str(e)}")
            return []
    
    async def get_variant(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """Get variant by ID."""
        try:
            response = self.supabase.table("vehicle_variants").select("*").eq("variant_id", variant_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting variant: {str(e)}")
            return None
