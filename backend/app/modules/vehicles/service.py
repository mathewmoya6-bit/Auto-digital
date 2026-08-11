# app/modules/vehicles/service.py

# ================================================================
# Auto-D Kenya - Vehicle Service
# ================================================================
# Business logic for the CRSP-driven vehicle catalogue.
#
# CRSP is the authoritative vehicle identity.
# ================================================================

import logging
from typing import Optional, List, Dict, Any

from app.modules.vehicles.repository import VehicleRepository
from app.core.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)


class VehicleService:
    """
    Vehicle business service.

    Responsibilities:
        - Validate vehicle requests
        - Retrieve categories
        - Retrieve makes
        - Retrieve models
        - Search CRSP vehicles
        - Retrieve individual CRSP vehicles
        - Retrieve CRSP base prices
        - Provide vehicle statistics
        - Provide service health
    """

    def __init__(self):
        self.repository = VehicleRepository()

    # ============================================================
    # CATEGORIES
    # ============================================================

    async def get_categories(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Return the five approved application categories.
        """

        return await self.repository.get_categories()

    # ============================================================
    # MAKES
    # ============================================================

    async def get_makes(
        self,
        category_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return vehicle makes.

        Category filtering is handled by the repository/category
        architecture and does not depend on a nonexistent
        vehicle_crsp_lookup.vehicle_category column.
        """

        return await self.repository.get_makes(
            category_id=category_id
        )

    # ============================================================
    # MODELS
    # ============================================================

    async def get_models(
        self,
        make_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Return models for a specific make.
        """

        if make_id <= 0:
            raise ValidationException(
                "Invalid make ID."
            )

        models = await self.repository.get_models(
            make_id=make_id
        )

        if not models:
            raise NotFoundException(
                "No vehicle models found for this make."
            )

        return models

    # ============================================================
    # VEHICLE SEARCH
    # ============================================================

    async def search_vehicles(
        self,
        search: Optional[str] = None,
        make_id: Optional[int] = None,
        model_id: Optional[int] = None,
        fuel: Optional[str] = None,
        transmission: Optional[str] = None,
        engine_capacity_cc: Optional[int] = None,
        year: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Search the CRSP vehicle catalogue.
        """

        if limit < 1:
            limit = 1

        if limit > 500:
            limit = 500

        if offset < 0:
            offset = 0

        if search:
            search = search.strip()

            if len(search) < 2:
                raise ValidationException(
                    "Search must contain at least 2 characters."
                )

        if make_id is not None and make_id <= 0:
            raise ValidationException(
                "Invalid make ID."
            )

        if model_id is not None and model_id <= 0:
            raise ValidationException(
                "Invalid model ID."
            )

        if year is not None:
            if year < 1900 or year > 2100:
                raise ValidationException(
                    "Invalid vehicle year."
                )

        return await self.repository.search_vehicles(
            search=search,
            make_id=make_id,
            model_id=model_id,
            fuel=fuel,
            transmission=transmission,
            engine_capacity_cc=engine_capacity_cc,
            year=year,
            limit=limit,
            offset=offset,
        )

    # ============================================================
    # SINGLE VEHICLE
    # ============================================================

    async def get_vehicle(
        self,
        crsp_id: int,
    ) -> Dict[str, Any]:
        """
        Retrieve one CRSP vehicle.

        crsp_id is the authoritative vehicle identifier.
        """

        if crsp_id <= 0:
            raise ValidationException(
                "Invalid CRSP vehicle ID."
            )

        vehicle = await self.repository.get_vehicle(
            crsp_id=crsp_id
        )

        if not vehicle:
            raise NotFoundException(
                "CRSP vehicle not found."
            )

        return vehicle

    # ============================================================
    # BASE PRICE
    # ============================================================

    async def get_base_price(
        self,
        crsp_id: int,
    ) -> Dict[str, Any]:
        """
        Retrieve the CRSP reference price for a vehicle.
        """

        if crsp_id <= 0:
            raise ValidationException(
                "Invalid CRSP vehicle ID."
            )

        price = await self.repository.get_base_price(
            crsp_id=crsp_id
        )

        if not price:
            raise NotFoundException(
                "CRSP price not found for this vehicle."
            )

        return price

    # ============================================================
    # VEHICLE PROFILE
    # ============================================================

    async def get_vehicle_profile(
        self,
        crsp_id: int,
    ) -> Dict[str, Any]:
        """
        Return a complete vehicle profile.

        Includes:
            - CRSP vehicle identity
            - Vehicle specifications
            - CRSP price
        """

        vehicle = await self.get_vehicle(
            crsp_id=crsp_id
        )

        pricing = await self.get_base_price(
            crsp_id=crsp_id
        )

        return {
            "vehicle": vehicle,
            "pricing": pricing,
        }

    # ============================================================
    # STATISTICS
    # ============================================================

    async def get_statistics(
        self,
    ) -> Dict[str, Any]:
        """
        Return CRSP catalogue statistics.
        """

        return await self.repository.get_statistics()

    # ============================================================
    # HEALTH
    # ============================================================

    async def health_check(
        self,
    ) -> Dict[str, Any]:
        """
        Check vehicle catalogue/database health.
        """

        return await self.repository.health_check()
