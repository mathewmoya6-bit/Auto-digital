# app/modules/vehicles/service.py
# Auto-D Kenya - Vehicles Service
# ================================================================
# TYPE: MODULE - Vehicles business logic

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.modules.vehicles.repository import VehicleRepository
from app.core.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)


class VehicleService:
    """Vehicle service for business logic."""
    
    def __init__(self):
        self.repository = VehicleRepository()
    
    async def add_vehicle(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new vehicle."""
        if not data.get("plate"):
            raise ValidationException("Plate number is required")
        
        # Check if vehicle already exists
        existing = await self.repository.get_by_user(user_id)
        for vehicle in existing:
            if vehicle.get("plate", "").upper() == data.get("plate", "").upper():
                raise ValidationException("Vehicle with this plate already exists")
        
        return await self.repository.create(user_id, data)
    
    async def get_user_vehicles(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all vehicles for a user."""
        return await self.repository.get_by_user(user_id)
    
    async def get_vehicle(self, vehicle_id: str, user_id: str) -> Dict[str, Any]:
        """Get a vehicle by ID."""
        vehicle = await self.repository.get_by_id(vehicle_id, user_id)
        if not vehicle:
            raise NotFoundException("Vehicle not found")
        return vehicle
    
    async def update_vehicle(self, vehicle_id: str, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a vehicle."""
        vehicle = await self.repository.get_by_id(vehicle_id, user_id)
        if not vehicle:
            raise NotFoundException("Vehicle not found")
        return await self.repository.update(vehicle_id, user_id, data)
    
    async def delete_vehicle(self, vehicle_id: str, user_id: str) -> bool:
        """Delete a vehicle."""
        vehicle = await self.repository.get_by_id(vehicle_id, user_id)
        if not vehicle:
            raise NotFoundException("Vehicle not found")
        return await self.repository.delete(vehicle_id, user_id)
    
    async def get_makes(self, category_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all vehicle makes."""
        return await self.repository.get_makes(category_id)
    
    async def get_models(self, make_id: str) -> List[Dict[str, Any]]:
        """Get models for a make."""
        return await self.repository.get_models(make_id)
    
    async def get_generations(self, model_id: str) -> List[Dict[str, Any]]:
        """Get generations for a model."""
        return await self.repository.get_generations(model_id)
    
    async def get_variants(self, generation_id: str) -> List[Dict[str, Any]]:
        """Get variants for a generation."""
        return await self.repository.get_variants(generation_id)
    
    async def get_variant(self, variant_id: str) -> Dict[str, Any]:
        """Get variant by ID."""
        variant = await self.repository.get_variant(variant_id)
        if not variant:
            raise NotFoundException("Variant not found")
        return variant
