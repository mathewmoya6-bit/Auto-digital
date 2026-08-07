# app/modules/vehicles/service.py

# Auto-D Kenya - Vehicles Service
# ================================================================
# TYPE: MODULE - Business Logic

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from app.modules.vehicles.repository import VehicleRepository
from app.core.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)


class VehicleService:
    """Vehicle Business Service."""

    def __init__(self):
        self.repository = VehicleRepository()

    # ============================================================
    # USER VEHICLES
    # ============================================================

    async def add_vehicle(
        self,
        user_id: UUID,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Register a vehicle to a user.
        """

        plate = data.get("plate")

        if not plate:
            raise ValidationException("Plate number is required.")

        existing = await self.repository.get_vehicle_by_plate(
            user_id=user_id,
            plate=plate,
        )

        if existing:
            raise ValidationException(
                "Vehicle already exists."
            )

        return await self.repository.create_vehicle(
            user_id=user_id,
            data=data,
        )

    async def get_user_vehicles(
        self,
        user_id: UUID,
    ) -> List[Dict[str, Any]]:
        return await self.repository.get_user_vehicles(user_id)

    async def get_vehicle(
        self,
        vehicle_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:

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
    ) -> Dict[str, Any]:

        vehicle = await self.repository.get_vehicle(
            vehicle_id,
            user_id,
        )

        if not vehicle:
            raise NotFoundException("Vehicle not found.")

        return await self.repository.update_vehicle(
            vehicle_id,
            user_id,
            data,
        )

    async def delete_vehicle(
        self,
        vehicle_id: UUID,
        user_id: UUID,
    ) -> bool:

        vehicle = await self.repository.get_vehicle(
            vehicle_id,
            user_id,
        )

        if not vehicle:
            raise NotFoundException("Vehicle not found.")

        return await self.repository.delete_vehicle(
            vehicle_id,
            user_id,
        )

    # ============================================================
    # MASTER VEHICLE DATABASE
    # ============================================================

    async def get_categories(self):

        return await self.repository.get_categories()

    async def get_makes(
        self,
        category_id: Optional[int] = None,
    ):

        return await self.repository.get_makes(category_id)

    async def get_models(
        self,
        make_id: int,
    ):

        return await self.repository.get_models(make_id)

    async def get_generations(
        self,
        model_id: int,
    ):

        return await self.repository.get_generations(model_id)

    async def get_variants(
        self,
        generation_id: int,
    ):

        return await self.repository.get_variants(generation_id)

    async def get_variant(
        self,
        variant_id: int,
    ):

        variant = await self.repository.get_variant(
            variant_id
        )

        if not variant:
            raise NotFoundException(
                "Vehicle variant not found."
            )

        return variant

    async def search_master(
        self,
        keyword: str,
    ):

        return await self.repository.search_master(keyword)

    # ============================================================
    # BASE PRICES
    # ============================================================

    async def get_base_price(
        self,
        variant_id: int,
    ):

        return await self.repository.get_base_price(
            variant_id
        )

    async def update_base_price(
        self,
        variant_id: int,
        values: Dict[str, Any],
    ):

        return await self.repository.update_base_price(
            variant_id,
            values,
        )

    # ============================================================
    # VEHICLE DETAILS
    # ============================================================

    async def get_vehicle_profile(
        self,
        variant_id: int,
    ):
        """
        Returns:

        - Vehicle Specification
        - CRSP/Base Price
        - Market Values

        """

        vehicle = await self.repository.get_variant(
            variant_id
        )

        if not vehicle:
            raise NotFoundException(
                "Vehicle not found."
            )

        base_price = await self.repository.get_base_price(
            variant_id
        )

        return {
            "vehicle": vehicle,
            "pricing": base_price,
        }
