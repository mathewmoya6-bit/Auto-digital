# app/modules/valuation/service.py

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class ValuationService:
    """
    AUTO-D Kenya
    Vehicle Valuation Service

    Flow:

        Vehicle
          ↓
        CRSP
          ↓
        Category
          ↓
        Depreciation
          ↓
        Mileage adjustment
          ↓
        Condition adjustment
          ↓
        Accident adjustment
          ↓
        Location adjustment
          ↓
        Estimated market value
    """

    def __init__(self):
        self.supabase = get_supabase()

    # ============================================================
    # BASIC HELPERS
    # ============================================================

    @staticmethod
    def _number(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default

            if isinstance(value, str):
                value = value.replace(",", "").strip()

            return float(value)

        except (TypeError, ValueError):
            return default

    @staticmethod
    def _text(value: Any) -> str:
        if value is None:
            return ""

        return str(value).strip().upper()

    # ============================================================
    # CATEGORY NORMALIZATION
    # ============================================================

    def normalize_category(
        self,
        make: Optional[str],
        model: Optional[str],
        category: Optional[str] = None,
        body_type: Optional[str] = None,
    ) -> str:

        make = self._text(make)
        model = self._text(model)
        category = self._text(category)
        body_type = self._text(body_type)

        # --------------------------------------------------------
        # Toyota passenger vehicles
        # --------------------------------------------------------

        if make == "TOYOTA":

            passenger_mpv = (
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
            )

            passenger_sedan = (
                "COROLLA AXIO",
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

            passenger_suv = (
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

            passenger_hatchback = (
                "AQUA",
                "PIXIS",
                "PASSO",
                "VITZ",
                "YARIS",
                "RUMION",
                "AURIS",
                "PRIUS",
            )

            passenger_wagon = (
                "FIELDER",
                "TOURING",
                "PROBOX",
                "SUCCEED",
            )

            true_commercial = (
                "DYNA",
                "TOYOACE",
                "HIACE",
                "REGIUSACE",
                "COASTER",
                "LITE ACE TRUCK",
                "TOWN ACE TRUCK",
                "PIXIS TRUCK",
                "HILUX",
            )

            for pattern in true_commercial:
                if pattern in model:

                    if "COASTER" in model:
                        return "BUS"

                    if "DYNA" in model or "TOYOACE" in model:
                        return "TRUCK"

                    if "HILUX" in model:
                        return "PICKUP"

                    return "COMMERCIAL"

            for pattern in passenger_mpv:
                if pattern in model:
                    return "MPV"

            for pattern in passenger_suv:
                if pattern in model:
                    return "SUV"

            for pattern in passenger_sedan:
                if pattern in model:
                    return "SEDAN"

            for pattern in passenger_hatchback:
                if pattern in model:
                    return "HATCHBACK"

            for pattern in passenger_wagon:
                if pattern in model:
                    return "WAGON"

        # --------------------------------------------------------
        # Generic body type
        # --------------------------------------------------------

        mappings = {
            "SEDAN": "SEDAN",
            "SUV": "SUV",
            "HATCHBACK": "HATCHBACK",
            "WAGON": "WAGON",
            "MPV": "MPV",
            "MINIVAN": "MPV",
            "COUPE": "COUPE",
            "CONVERTIBLE": "CONVERTIBLE",
            "PICKUP": "PICKUP",
            "TRUCK": "TRUCK",
            "BUS": "BUS",
            "COMMERCIAL": "COMMERCIAL",
            "VAN": "COMMERCIAL",
            "ELECTRIC": "ELECTRIC",
            "LUXURY": "LUXURY",
        }

        if body_type in mappings:
            return mappings[body_type]

        if category in mappings:
            return mappings[category]

        return "OTHER"

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

        return self.normalize_category(
            make=make,
            model=model,
            category=category,
            body_type=body_type,
        )

    # ============================================================
    # CRSP
    # ============================================================

    def get_crsp(
        self,
        vehicle_id: Optional[int] = None,
        make: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[float]:

        try:

            # ----------------------------------------------------
            # Vehicle ID lookup
            # ----------------------------------------------------

            if vehicle_id:

                response = (
                    self.supabase
                    .table("vehicle_models")
                    .select("id,make,model,crsp_kes")
                    .eq("id", vehicle_id)
                    .maybe_single()
                    .execute()
                )

                if response.data:
                    value = response.data.get("crsp_kes")

                    if value is not None:
                        return self._number(value)

            # ----------------------------------------------------
            # Make + model lookup
            # ----------------------------------------------------

            if make and model:

                response = (
                    self.supabase
                    .table("vehicle_models")
                    .select("id,make,model,crsp_kes")
                    .ilike("make", self._text(make))
                    .ilike("model", self._text(model))
                    .limit(1)
                    .execute()
                )

                rows = response.data or []

                if rows:
                    value = rows[0].get("crsp_kes")

                    if value is not None:
                        return self._number(value)

        except Exception as exc:
            logger.exception(
                "CRSP lookup failed: %s",
                exc,
            )

        return None

    # ============================================================
    # DEPRECIATION
    # ============================================================

    def calculate_depreciation(
        self,
        vehicle: Dict[str, Any],
    ) -> float:

        year = self._number(
            vehicle.get("year")
            or vehicle.get("year_of_manufacture")
        )

        current_year = 2026

        age = max(
            0,
            current_year - int(year)
        )

        category = self.get_depreciation_category(
            vehicle.get("make"),
            vehicle.get("model"),
            vehicle.get("category"),
            vehicle.get("body_type"),
        )

        # Conservative fallback rates.
        rates = {
            "SEDAN": 0.10,
            "SUV": 0.09,
            "HATCHBACK": 0.10,
            "WAGON": 0.10,
            "MPV": 0.09,
            "COUPE": 0.08,
            "CONVERTIBLE": 0.08,
            "PICKUP": 0.10,
            "COMMERCIAL": 0.12,
            "TRUCK": 0.12,
            "BUS": 0.13,
            "ELECTRIC": 0.10,
            "LUXURY": 0.12,
            "OTHER": 0.10,
        }

        annual_rate = rates.get(
            category,
            rates["OTHER"],
        )

        # Compound depreciation.
        factor = (1 - annual_rate) ** age

        return max(0.05, factor)

    # ============================================================
    # MILEAGE ADJUSTMENT
    # ============================================================

    def calculate_mileage_factor(
        self,
        vehicle: Dict[str, Any],
    ) -> float:

        mileage = self._number(
            vehicle.get("mileage")
            or vehicle.get("odometer")
            or vehicle.get("odometer_km")
        )

        if mileage <= 0:
            return 1.0

        if mileage <= 20_000:
            return 1.05

        if mileage <= 50_000:
            return 1.02

        if mileage <= 100_000:
            return 1.00

        if mileage <= 150_000:
            return 0.95

        if mileage <= 200_000:
            return 0.90

        if mileage <= 250_000:
            return 0.85

        return 0.80

    # ============================================================
    # CONDITION
    # ============================================================

    def calculate_condition_factor(
        self,
        vehicle: Dict[str, Any],
    ) -> float:

        condition = self._text(
            vehicle.get("condition")
            or vehicle.get("overall_condition")
        )

        factors = {
            "EXCELLENT": 1.08,
            "VERY GOOD": 1.04,
            "GOOD": 1.00,
            "FAIR": 0.92,
            "POOR": 0.80,
        }

        return factors.get(condition, 1.00)

    # ============================================================
    # ACCIDENT
    # ============================================================

    def calculate_accident_factor(
        self,
        vehicle: Dict[str, Any],
    ) -> float:

        accident = self._text(
            vehicle.get("accident_history")
            or vehicle.get("accident")
        )

        factors = {
            "NONE": 1.00,
            "MINOR": 0.95,
            "MAJOR": 0.80,
            "TOTAL LOSS": 0.50,
        }

        return factors.get(accident, 1.00)

    # ============================================================
    # LOCATION
    # ============================================================

    def calculate_location_factor(
        self,
        vehicle: Dict[str, Any],
    ) -> float:

        location = self._text(
            vehicle.get("location")
            or vehicle.get("county")
        )

        factors = {
            "NAIROBI": 1.02,
            "MOMBASA": 1.00,
            "KISUMU": 0.98,
            "NAKURU": 0.99,
            "ELDORET": 0.98,
            "THIKA": 1.00,
            "KIAMBU": 1.01,
            "KAJIADO": 1.00,
            "MACHAKOS": 0.98,
            "MERU": 0.97,
            "NYERI": 0.97,
            "EMBU": 0.97,
            "MALINDI": 0.98,
            "NANYUKI": 0.97,
            "OTHER": 0.97,
        }

        return factors.get(location, 1.00)

    # ============================================================
    # MAIN CALCULATION
    # ============================================================

    def calculate_valuation(
        self,
        vehicle: Dict[str, Any],
    ) -> Dict[str, Any]:

        try:

            vehicle = dict(vehicle)

            make = vehicle.get("make")
            model = vehicle.get("model")

            # ----------------------------------------------------
            # Resolve category
            # ----------------------------------------------------

            category = self.normalize_category(
                make=make,
                model=model,
                category=vehicle.get("category"),
                body_type=vehicle.get("body_type"),
            )

            depreciation_category = (
                self.get_depreciation_category(
                    make=make,
                    model=model,
                    category=category,
                    body_type=vehicle.get("body_type"),
                )
            )

            # ----------------------------------------------------
            # CRSP
            # ----------------------------------------------------

            crsp = self._number(
                vehicle.get("crsp_kes")
                or vehicle.get("crsp")
            )

            if crsp <= 0:

                found_crsp = self.get_crsp(
                    vehicle_id=vehicle.get("vehicle_id")
                    or vehicle.get("id"),
                    make=make,
                    model=model,
                )

                if found_crsp:
                    crsp = found_crsp

            # ----------------------------------------------------
            # If no CRSP, don't silently return nonsense.
            # ----------------------------------------------------

            if crsp <= 0:

                return {
                    "success": False,
                    "estimated_value": 0,
                    "estimated_value_min": 0,
                    "estimated_value_max": 0,
                    "crsp_kes": 0,
                    "confidence_score": 0,
                    "category": category,
                    "depreciation_category": depreciation_category,
                    "adjustments": [],
                    "warning": (
                        "No matching CRSP/master vehicle price "
                        "was found."
                    ),
                }

            # ----------------------------------------------------
            # Factors
            # ----------------------------------------------------

            depreciation_factor = (
                self.calculate_depreciation(vehicle)
            )

            mileage_factor = (
                self.calculate_mileage_factor(vehicle)
            )

            condition_factor = (
                self.calculate_condition_factor(vehicle)
            )

            accident_factor = (
                self.calculate_accident_factor(vehicle)
            )

            location_factor = (
                self.calculate_location_factor(vehicle)
            )

            # ----------------------------------------------------
            # Final value
            # ----------------------------------------------------

            estimated_value = (
                crsp
                * depreciation_factor
                * mileage_factor
                * condition_factor
                * accident_factor
                * location_factor
            )

            estimated_value = max(
                0,
                round(estimated_value, 2),
            )

            # ----------------------------------------------------
            # Range
            # ----------------------------------------------------

            minimum = round(
                estimated_value * 0.90,
                2,
            )

            maximum = round(
                estimated_value * 1.10,
                2,
            )

            # ----------------------------------------------------
            # Confidence
            # ----------------------------------------------------

            confidence = 85

            if crsp > 0:
                confidence += 5

            if vehicle.get("year"):
                confidence += 2

            if vehicle.get("mileage") is not None:
                confidence += 2

            if vehicle.get("condition"):
                confidence += 2

            confidence = min(
                99,
                confidence,
            )

            return {
                "success": True,

                "estimated_value": estimated_value,

                "estimated_value_min": minimum,

                "estimated_value_max": maximum,

                "crsp_kes": round(crsp, 2),

                "confidence_score": confidence,

                "category": category,

                "depreciation_category": (
                    depreciation_category
                ),

                "factors": {
                    "depreciation": depreciation_factor,
                    "mileage": mileage_factor,
                    "condition": condition_factor,
                    "accident": accident_factor,
                    "location": location_factor,
                },

                "adjustments": [
                    {
                        "name": "Depreciation",
                        "factor": depreciation_factor,
                    },
                    {
                        "name": "Mileage",
                        "factor": mileage_factor,
                    },
                    {
                        "name": "Condition",
                        "factor": condition_factor,
                    },
                    {
                        "name": "Accident history",
                        "factor": accident_factor,
                    },
                    {
                        "name": "Location",
                        "factor": location_factor,
                    },
                ],
            }

        except Exception as exc:

            logger.exception(
                "Vehicle valuation failed: %s",
                exc,
            )

            return {
                "success": False,
                "estimated_value": 0,
                "estimated_value_min": 0,
                "estimated_value_max": 0,
                "crsp_kes": 0,
                "confidence_score": 0,
                "adjustments": [],
                "error": str(exc),
            }

    # ============================================================
    # COMPATIBILITY METHODS
    # ============================================================

    def get_valuation(
        self,
        vehicle: Dict[str, Any],
    ) -> Dict[str, Any]:

        return self.calculate_valuation(vehicle)

    def value_vehicle(
        self,
        vehicle: Dict[str, Any],
    ) -> Dict[str, Any]:

        return self.calculate_valuation(vehicle)

    def valuate(
        self,
        vehicle: Dict[str, Any],
    ) -> Dict[str, Any]:

        return self.calculate_valuation(vehicle)

    # ============================================================
    # PROFILE
    # ============================================================

    def build_vehicle_profile(
        self,
        vehicle: Dict[str, Any],
    ) -> Dict[str, Any]:

        category = self.normalize_category(
            make=vehicle.get("make"),
            model=vehicle.get("model"),
            category=vehicle.get("category"),
            body_type=vehicle.get("body_type"),
        )

        depreciation_category = (
            self.get_depreciation_category(
                make=vehicle.get("make"),
                model=vehicle.get("model"),
                category=category,
                body_type=vehicle.get("body_type"),
            )
        )

        return {
            "make": vehicle.get("make"),
            "model": vehicle.get("model"),
            "category": category,
            "depreciation_category": depreciation_category,
            "body_type": vehicle.get("body_type"),
            "engine_capacity": vehicle.get(
                "engine_capacity"
            ),
            "fuel": vehicle.get("fuel"),
            "transmission": vehicle.get(
                "transmission"
            ),
            "year": vehicle.get("year"),
            "mileage": vehicle.get("mileage"),
            "condition": vehicle.get("condition"),
            "location": vehicle.get("location"),
            "crsp_kes": vehicle.get("crsp_kes"),
        }


# ================================================================
# SINGLETON
# ================================================================

valuation_service = ValuationService()
