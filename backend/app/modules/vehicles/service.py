```python
# app/modules/vehicles/service.py

# ================================================================
# Auto-D Kenya - Vehicles Service
# ================================================================
#
# TYPE: MODULE - Business Logic
#
# Responsibilities:
#   - Validate vehicle operations
#   - Delegate database operations to VehicleRepository
#   - Keep database-specific logic out of the service
#
# ================================================================

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from app.modules.vehicles.repository import VehicleRepository
from app.core.exceptions import NotFoundException, ValidationException


logger = logging.getLogger(__name__)


class VehicleService:
    """
    Vehicle business service.

    The service does not directly query Supabase.
    All database operations are delegated to VehicleRepository.
    """

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
            raise ValidationException(
                "Plate number is required."
            )

        plate = str(plate).strip().upper()

        existing = await self.repository.get_vehicle_by_plate(
            user_id=user_id,
            plate=plate,
        )

        if existing:
            raise ValidationException(
                "Vehicle already exists."
            )

        data = {
            **data,
            "plate": plate,
        }

        return await self.repository.create_vehicle(
            user_id=user_id,
            data=data,
        )

    async def get_user_vehicles(
        self,
        user_id: UUID,
    ) -> List[Dict[str, Any]]:
        """
        Get all vehicles belonging to a user.
        """

        return await self.repository.get_user_vehicles(
            user_id
        )

    async def get_vehicle(
        self,
        vehicle_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get a specific user vehicle.
        """

        vehicle = await self.repository.get_vehicle(
            vehicle_id,
            user_id,
        )

        if not vehicle:
            raise NotFoundException(
                "Vehicle not found."
            )

        return vehicle

    async def update_vehicle(
        self,
        vehicle_id: UUID,
        user_id: UUID,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update a user's vehicle.
        """

        vehicle = await self.repository.get_vehicle(
            vehicle_id,
            user_id,
        )

        if not vehicle:
            raise NotFoundException(
                "Vehicle not found."
            )

        if data.get("plate"):
            data = {
                **data,
                "plate": str(data["plate"]).strip().upper(),
            }

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
        """
        Delete a user's vehicle.
        """

        vehicle = await self.repository.get_vehicle(
            vehicle_id,
            user_id,
        )

        if not vehicle:
            raise NotFoundException(
                "Vehicle not found."
            )

        return await self.repository.delete_vehicle(
            vehicle_id,
            user_id,
        )

    # ============================================================
    # MASTER VEHICLE DATABASE
    # ============================================================

    async def get_categories(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Get the five approved vehicle categories.

        Source:
            vehicle_category_lookup.vehicle_category

        Categories:
            COMMERCIAL
            ELECTRIC
            LUXURY
            PICKUP
            SEDAN
        """

        return await self.repository.get_categories()

    async def get_makes(
        self,
        category_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get vehicle makes.

        Makes come from:
            vehicle_crsp_lookup.make

        category_id is retained for API compatibility, but the
        repository currently returns the complete Make catalogue.
        """

        return await self.repository.get_makes(
            category_id
        )

    async def get_models(
        self,
        make_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Get models for a selected make.
        """

        return await self.repository.get_models(
            make_id
        )

    # ============================================================
    # SEARCH
    # ============================================================

    async def search_master(
        self,
        keyword: str,
    ) -> List[Dict[str, Any]]:
        """
        Search the CRSP vehicle catalogue.
        """

        if not keyword or not keyword.strip():
            return []

        keyword = keyword.strip()

        return await self.repository.search_master(
            keyword
        )

    # ============================================================
    # BASE PRICES
    # ============================================================

    async def get_base_price(
        self,
        variant_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Get the base price for a vehicle variant.
        """

        return await self.repository.get_base_price(
            variant_id
        )

    async def update_base_price(
        self,
        variant_id: int,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update a vehicle base price.
        """

        if not values:
            raise ValidationException(
                "Price data is required."
            )

        return await self.repository.update_base_price(
            variant_id,
            values,
        )
```
