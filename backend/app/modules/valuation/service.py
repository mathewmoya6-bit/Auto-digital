# app/modules/vehicles/service.py
"""
AUTO-D Kenya
Vehicle Service Layer

Responsibilities:
- Vehicle lookup and normalization
- Category normalization
- Make/model/engine resolution
- CRSP lookup
- Depreciation category resolution
- Vehicle profile preparation for valuation
- Safe handling of missing master-data records

IMPORTANT:
The frontend category is treated as a hint only.
The master vehicle data is authoritative.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class VehicleService:
    """Business logic for vehicle master data and valuation preparation."""

    # ============================================================
    # CATEGORY DEFINITIONS
    # ============================================================

    VALID_CATEGORIES = {
        "SEDAN",
        "SUV",
        "HATCHBACK",
        "WAGON",
        "MPV",
        "COUPE",
        "CONVERTIBLE",
        "PICKUP",
        "COMMERCIAL",
        "BUS",
        "TRUCK",
        "ELECTRIC",
        "LUXURY",
        "OTHER",
    }

    # Categories that should normally use passenger-vehicle depreciation.
    PASSENGER_CATEGORIES = {
        "SEDAN",
        "SUV",
        "HATCHBACK",
        "WAGON",
        "MPV",
        "COUPE",
        "CONVERTIBLE",
        "LUXURY",
        "ELECTRIC",
    }

    COMMERCIAL_CATEGORIES = {
        "COMMERCIAL",
        "BUS",
        "TRUCK",
        "PICKUP",
    }

    # ============================================================
    # TOYOTA NORMALIZATION
    # ============================================================

    # Toyota models which have historically been incorrectly placed
    # under COMMERCIAL/VAN but are fundamentally passenger vehicles.
    TOYOTA_PASSENGER_PATTERNS = (
        "ALPHARD",
        "VELLFIRE",
        "NOAH",
        "VOXY",
        "ESQUIRE",
        "SIENTA",
        "ESTIMA",
        "AERAS/ESTIMA",
        "ROOMY",
        "TANK",
        "PORTE",
        "SPADE",
        "ISIS",
        "WISH",
        "GRANACE",
        "COROLLA AXIO",
        "COROLLA FIELDER",
        "COROLLA TOURING",
        "PRIUS VAN CRUISE",
        "JPN TAXI",
        "JPN TAXI TAKUMI",
        "AQUA",
        "PIXIS",
        "PASSO",
        "YARIS",
        "VITZ",
        "RAIZE",
        "RUMION",
        "CROWN",
        "CAMRY",
        "COROLLA",
        "PREMIO",
        "ALLION",
        "MARK X",
        "SAI",
        "CENTURY",
        "BELTA",
        "AVENSIS",
        "MIRAI",
        "AURIS",
        "FJ CRUISER",
        "LAND CRUISER",
        "HARRIER",
        "RAV4",
        "FORTUNER",
        "C-HR",
        "YARIS CROSS",
        "COROLLA CROSS",
        "PRADO",
        "BZ4X",
    )

    # Toyota models that should remain commercial.
    TOYOTA_TRUE_COMMERCIAL_PATTERNS = (
        "DYNA",
        "TOYOACE",
        "HIACE",
        "REGIUSACE",
        "LITE ACE TRUCK",
        "TOWN ACE TRUCK",
        "TOWN ACE TRUCK",
        "COASTER",
        "PIXIS TRUCK",
        "HILUX",
        "LANDCRUISERVD SINGLE CABIN",
    )

    # ============================================================
    # INIT
    # ============================================================

    def __init__(self):
        self.supabase = get_supabase()

    # ============================================================
    # BASIC HELPERS
    # ============================================================

    @staticmethod
    def clean_text(value: Any) -> str:
        if value is None:
            return ""

        value = str(value).upper().strip()

        # Normalize whitespace
        value = re.sub(r"\s+", " ", value)

        return value

    @staticmethod
    def normalize_make(make: Any) -> str:
        value = VehicleService.clean_text(make)

        aliases = {
            "MITSUBISHI FUSO": "MITSUBISHI FUSO",
            "MITSUBISHI": "MITSUBISHI",
            "NISSAN DIESEL/UD": "NISSAN DIESEL/UD",
            "UD": "NISSAN DIESEL/UD",
            "TOYOTA MOTOR": "TOYOTA",
        }

        return aliases.get(value, value)

    # ============================================================
    # CATEGORY NORMALIZATION
    # ============================================================

    def normalize_category(
        self,
        make: Optional[str],
        model: Optional[str],
        body_type: Optional[str] = None,
        requested_category: Optional[str] = None,
    ) -> str:
        """
        Resolve the real vehicle category.

        Priority:
        1. Explicit body type from master data
        2. Toyota model intelligence
        3. Requested frontend category
        4. OTHER
        """

        make_n = self.normalize_make(make)
        model_n = self.clean_text(model)
        body_n = self.clean_text(body_type)
        requested_n = self.clean_text(requested_category)

        # --------------------------------------------------------
        # Toyota-specific correction
        # --------------------------------------------------------

        if make_n == "TOYOTA":

            # Genuine Toyota commercial vehicles first.
            for pattern in self.TOYOTA_TRUE_COMMERCIAL_PATTERNS:
                if pattern in model_n:
                    if "COASTER" in model_n:
                        return "BUS"

                    if "DYNA" in model_n:
                        return "TRUCK"

                    if "HILUX" in model_n:
                        return "PICKUP"

                    return "COMMERCIAL"

            # Toyota passenger vehicles incorrectly stored as VAN.
            for pattern in self.TOYOTA_PASSENGER_PATTERNS:
                if pattern in model_n:
                    return self._infer_toyota_passenger_category(
                        model_n,
                        body_n,
                    )

        # --------------------------------------------------------
        # Body type from database
        # --------------------------------------------------------

        if body_n:
            mapped = self._map_body_type(body_n)

            if mapped:
                return mapped

        # --------------------------------------------------------
        # Frontend category
        # --------------------------------------------------------

        if requested_n in self.VALID_CATEGORIES:
            return requested_n

        return "OTHER"

    # ============================================================
    # TOYOTA PASSENGER CATEGORY
    # ============================================================

    def _infer_toyota_passenger_category(
        self,
        model: str,
        body_type: str = "",
    ) -> str:

        # SUVs
        suv_patterns = (
            "LAND CRUISER",
            "LANDCRUISER",
            "PRADO",
            "HARRIER",
            "RAV4",
            "FORTUNER",
            "FJ CRUISER",
            "C-HR",
            "YARIS CROSS",
            "COROLLA CROSS",
            "RAIZE",
            "BZ4X",
        )

        for pattern in suv_patterns:
            if pattern in model:
                return "SUV"

        # Coupes
        if any(x in model for x in ("86", "SUPRA", "GR86", "GR SUPRA")):
            return "COUPE"

        # Hatchbacks
        hatch_patterns = (
            "AQUA",
            "PIXIS",
            "PASSO",
            "VITZ",
            "YARIS",
            "RUMION",
            "AURIS",
            "PRIUS",
        )

        for pattern in hatch_patterns:
            if pattern in model:
                return "HATCHBACK"

        # Wagons
        wagon_patterns = (
            "FIELDER",
            "FIELDER",
            "TOURING",
            "PROBOX",
            "SUCCEED",
        )

        for pattern in wagon_patterns:
            if pattern in model:
                return "WAGON"

        # Sedans
        sedan_patterns = (
            "COROLLA",
            "CAMRY",
            "PREMIO",
            "ALLION",
            "CROWN",
            "MARK X",
            "SAI",
            "CENTURY",
            "BELTA",
            "AVENSIS",
            "MIRAI",
            "JPN TAXI",
        )

        for pattern in sedan_patterns:
            if pattern in model:
                return "SEDAN"

        # MPVs
        mpv_patterns = (
            "ALPHARD",
            "VELLFIRE",
            "NOAH",
            "VOXY",
            "ESQUIRE",
            "SIENTA",
            "ESTIMA",
            "AERAS",
            "ROOMY",
            "TANK",
            "PORTE",
            "SPADE",
            "ISIS",
            "WISH",
            "GRANACE",
        )

        for pattern in mpv_patterns:
            if pattern in model:
                return "MPV"

        # If database body says VAN, treat passenger Toyota vans
        # as MPV rather than COMMERCIAL.
        if body_type == "VAN":
            return "MPV"

        return "OTHER"

    # ============================================================
    # BODY TYPE MAPPING
    # ============================================================

    @staticmethod
    def _map_body_type(body_type: str) -> Optional[str]:

        mappings = {
            "VAN": "COMMERCIAL",
            "MINIVAN": "MPV",
            "MPV": "MPV",
            "SEDAN": "SEDAN",
            "SUV": "SUV",
            "HATCHBACK": "HATCHBACK",
            "WAGON": "WAGON",
            "COUPE": "COUPE",
            "CONVERTIBLE": "CONVERTIBLE",
            "PICKUP": "PICKUP",
            "TRUCK": "TRUCK",
            "BUS": "BUS",
            "ELECTRIC": "ELECTRIC",
        }

        return mappings.get(body_type)

    # ============================================================
    # DEPRECIATION CATEGORY
    # ============================================================

    def get_depreciation_category(
        self,
        make: Optional[str],
        model: Optional[str],
        category: Optional[str],
        body_type: Optional[str] = None,
    ) -> str:
        """
        Returns the category that should be passed to depreciation.

        This is deliberately separate from the display category.
        """

        resolved = self.normalize_category(
            make=make,
            model=model,
            body_type=body_type,
            requested_category=category,
        )

        return resolved

    # ============================================================
    # VEHICLE LOOKUP
    # ============================================================

    def get_vehicle_by_id(self, vehicle_id: int) -> Optional[Dict[str, Any]]:
        try:
            response = (
                self.supabase
                .table("vehicle_models")
                .select("*")
                .eq("id", vehicle_id)
                .maybe_single()
                .execute()
            )

            return response.data

        except Exception as exc:
            logger.exception(
                "Failed to get vehicle by id %s: %s",
                vehicle_id,
                exc,
            )
            return None

    # ============================================================
    # SEARCH VEHICLES
    # ============================================================

    def search_vehicles(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:

        try:
            query = (
                self.supabase
                .table("vehicle_models")
                .select("*")
            )

            if make:
                query = query.ilike(
                    "make",
                    f"%{self.clean_text(make)}%",
                )

            if model:
                query = query.ilike(
                    "model",
                    f"%{self.clean_text(model)}%",
                )

            response = query.limit(limit).execute()

            vehicles = response.data or []

            result = []

            for vehicle in vehicles:
                resolved_category = self.normalize_category(
                    make=vehicle.get("make"),
                    model=vehicle.get("model"),
                    body_type=vehicle.get("body_type"),
                    requested_category=category,
                )

                if category:
                    if resolved_category != self.clean_text(category):
                        continue

                vehicle["resolved_category"] = resolved_category

                result.append(vehicle)

            return result

        except Exception as exc:
            logger.exception(
                "Vehicle search failed: %s",
                exc,
            )
            return []

    # ============================================================
    # CRSP LOOKUP
    # ============================================================

    def get_crsp(
        self,
        vehicle_id: Optional[int] = None,
        make: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:

        try:

            # ----------------------------------------------------
            # Direct vehicle ID
            # ----------------------------------------------------

            if vehicle_id:

                response = (
                    self.supabase
                    .table("vehicle_models")
                    .select("*")
                    .eq("id", vehicle_id)
                    .maybe_single()
                    .execute()
                )

                if response.data:
                    vehicle = response.data

                    if vehicle.get("crsp_kes") is not None:
                        return {
                            "vehicle_id": vehicle.get("id"),
                            "make": vehicle.get("make"),
                            "model": vehicle.get("model"),
                            "crsp_kes": float(
                                vehicle["crsp_kes"]
                            ),
                        }

            # ----------------------------------------------------
            # Make + model lookup
            # ----------------------------------------------------

            if make and model:

                response = (
                    self.supabase
                    .table("vehicle_models")
                    .select("*")
                    .ilike("make", self.clean_text(make))
                    .ilike("model", self.clean_text(model))
                    .limit(1)
                    .execute()
                )

                if response.data:

                    vehicle = response.data[0]

                    if vehicle.get("crsp_kes") is not None:
                        return {
                            "vehicle_id": vehicle.get("id"),
                            "make": vehicle.get("make"),
                            "model": vehicle.get("model"),
                            "crsp_kes": float(
                                vehicle["crsp_kes"]
                            ),
                        }

            return None

        except Exception as exc:
            logger.exception(
                "CRSP lookup failed: %s",
                exc,
            )
            return None

    # ============================================================
    # PREPARE VEHICLE FOR VALUATION
    # ============================================================

    def prepare_vehicle_for_valuation(
        self,
        vehicle: Dict[str, Any],
    ) -> Dict[str, Any]:

        make = vehicle.get("make")
        model = vehicle.get("model")
        body_type = vehicle.get("body_type")
        requested_category = vehicle.get("category")

        category = self.normalize_category(
            make=make,
            model=model,
            body_type=body_type,
            requested_category=requested_category,
        )

        depreciation_category = self.get_depreciation_category(
            make=make,
            model=model,
            category=category,
            body_type=body_type,
        )

        result = dict(vehicle)

        result["make"] = self.normalize_make(make)
        result["model"] = self.clean_text(model)

        result["category"] = category

        result["depreciation_category"] = (
            depreciation_category
        )

        # Keep original database body type for traceability.
        result["source_body_type"] = body_type

        # Flag potentially corrected records.
        result["category_corrected"] = (
            self.clean_text(requested_category)
            != category
            if requested_category
            else False
        )

        return result

    # ============================================================
    # VALIDATE VEHICLE
    # ============================================================

    def validate_vehicle(
        self,
        vehicle: Dict[str, Any],
    ) -> Dict[str, Any]:

        errors = []
        warnings = []

        make = self.clean_text(vehicle.get("make"))
        model = self.clean_text(vehicle.get("model"))

        if not make:
            errors.append("Vehicle make is required.")

        if not model:
            errors.append("Vehicle model is required.")

        category = self.normalize_category(
            make=make,
            model=model,
            body_type=vehicle.get("body_type"),
            requested_category=vehicle.get("category"),
        )

        if category == "OTHER":
            warnings.append(
                "Vehicle category could not be confidently resolved."
            )

        if not vehicle.get("crsp_kes"):
            warnings.append(
                "No matching KRA CRSP value was found."
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "category": category,
        }

    # ============================================================
    # PROFILE
    # ============================================================

    def build_vehicle_profile(
        self,
        vehicle: Dict[str, Any],
    ) -> Dict[str, Any]:

        prepared = self.prepare_vehicle_for_valuation(vehicle)

        validation = self.validate_vehicle(prepared)

        return {
            "vehicle": prepared,
            "validation": validation,
            "valuation_inputs": {
                "make": prepared.get("make"),
                "model": prepared.get("model"),
                "category": prepared.get("category"),
                "depreciation_category": prepared.get(
                    "depreciation_category"
                ),
                "body_type": prepared.get("body_type"),
                "fuel": prepared.get("fuel"),
                "transmission": prepared.get("transmission"),
                "engine_capacity": prepared.get(
                    "engine_capacity"
                ),
                "crsp_kes": prepared.get("crsp_kes"),
            },
        }


# ================================================================
# SERVICE SINGLETON
# ================================================================

vehicle_service = VehicleService()
