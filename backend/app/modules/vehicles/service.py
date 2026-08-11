# app/modules/vehicles/service.py

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from app.modules.vehicles.repository import VehicleRepository
from app.core.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)


class VehicleService:
    """Auto-D Kenya vehicle business service."""

    def __init__(self):
        self.repository = VehicleRepository()

    # ============================================================
    # USER VEHICLES
    # ============================================================

    async def add_vehicle(
        self,
        user_id: UUID,
        data: Dict[str, Any],
    ):
        plate = data.get("plate")

        if not plate:
            raise ValidationException("Plate number is required.")

        existing = await self.repository.get_vehicle_by_plate(
            user_id,
            plate,
        )

        if existing:
            raise ValidationException(
                "Vehicle already exists."
            )

        return await self.repository.create_vehicle(
            user_id,
            data,
        )

    async def get_user_vehicles(self, user_id: UUID):
        return await self.repository.get_user_vehicles(user_id)

    async def get_vehicle(
        self,
        vehicle_id: UUID,
        user_id: UUID,
    ):
        vehicle = await self.repository.get_vehicle(
            vehicle_id,
            user_id,
        )

        if not vehicle:
            raise NotFoundException("Vehicle not found.")

        return vehicle

    async def update_vehicle(
        self,
        vehicle_id: UUID,
        user_id: UUID,
        data: Dict[str, Any],
    ):
        await self.get_vehicle(vehicle_id, user_id)

        return await self.repository.update_vehicle(
            vehicle_id,
            user_id,
            data,
        )

    async def delete_vehicle(
        self,
        vehicle_id: UUID,
        user_id: UUID,
    ):
        await self.get_vehicle(vehicle_id, user_id)

        return await self.repository.delete_vehicle(
            vehicle_id,
            user_id,
        )

    # ============================================================
    # MASTER CATALOGUE
    # ============================================================

    async def get_categories(self):
        return await self.repository.get_categories()

    async def get_makes(
        self,
        category_id: Optional[int] = None,
    ):
        return await self.repository.get_makes(category_id)

    async def get_models(self, make_id: int):
        return await self.repository.get_models(make_id)

    async def get_generations(self, model_id: int):
        return await self.repository.get_generations(model_id)

    async def get_variants(self, generation_id: int):
        return await self.repository.get_variants(generation_id)

    async def get_variant(self, variant_id: int):
        vehicle = await self.repository.get_variant(variant_id)

        if not vehicle:
            raise NotFoundException(
                "Vehicle variant not found."
            )

        return vehicle

    async def get_vehicle_master(self, variant_id: int):
        vehicle = await self.repository.get_vehicle_master(
            variant_id
        )

        if not vehicle:
            raise NotFoundException(
                "Vehicle not found."
            )

        return vehicle

    async def search_vehicle_master(
        self,
        query: str,
        limit: int = 20,
    ):
        return await self.repository.search_master(
            query,
            limit,
        )

    # ============================================================
    # BASE PRICE
    # ============================================================

    async def get_base_price(self, variant_id: int):

        price = await self.repository.get_base_price(
            variant_id
        )

        if not price:
            raise NotFoundException(
                "CRSP price not found."
            )

        return price

    # ============================================================
    # STATISTICS
    # ============================================================

    async def get_statistics(self):
        return await self.repository.get_statistics()

    # ============================================================
    # HEALTH
    # ============================================================

    async def health_check(self):

        result = await self.repository.health_check()

        return {
            "status": result.get("status", "degraded"),
            "service": "vehicles",
            "version": "2.0",
            "timestamp": __import__(
                "datetime"
            ).datetime.utcnow().isoformat(),
            "database": result.get("database"),
            "crsp_records": result.get("crsp_records"),
            "error": result.get("error"),
        }
