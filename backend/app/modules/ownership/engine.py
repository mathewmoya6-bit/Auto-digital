"""
Auto-D Kenya
Production Ownership / TCO Engine

Architecture:

    Router
       ↓
    Engine
       ↓
    Repository
       ↓
    vehicle_crsp
       ↓
    calculate_vehicle_running_cost_v2()

The PostgreSQL function remains the calculation source of truth.

This engine:
- validates the vehicle exists
- normalizes production inputs
- calls the authoritative DB function
- normalizes the response
- prevents string/number arithmetic errors
- does not use user_vehicles
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from app.modules.ownership.repository import OwnershipRepository
from app.modules.ownership.schemas import OwnershipCostRequest

logger = logging.getLogger(__name__)


class OwnershipEngine:
    """
    Production Ownership / TCO calculation engine.
    """

    def __init__(self):
        self.repository = OwnershipRepository()

    # ==================================================================
    # PUBLIC API
    # ==================================================================

    async def calculate(
        self,
        request: OwnershipCostRequest,
    ) -> Dict[str, Any]:
        """
        Calculate vehicle ownership/running costs.
        """

        crsp_id = request.vehicle_crsp_id

        # --------------------------------------------------------------
        # 1. Verify authoritative vehicle exists
        # --------------------------------------------------------------

        vehicle = await self.repository.get_vehicle_crsp(crsp_id)

        if not vehicle:
            logger.warning(
                "Ownership requested for unknown CRSP ID: %s",
                crsp_id,
            )

            return {
                "success": False,
                "error": f"Vehicle with CRSP ID {crsp_id} not found",
                "vehicle_crsp_id": crsp_id,
            }

        # --------------------------------------------------------------
        # 2. Build production calculation payload
        # --------------------------------------------------------------

        payload = self._build_payload(request)

        # --------------------------------------------------------------
        # 3. Execute authoritative PostgreSQL calculation
        # --------------------------------------------------------------

        result = await self.repository.calculate_running_cost(
            payload
        )

        # --------------------------------------------------------------
        # 4. Handle DB-level failure
        # --------------------------------------------------------------

        if result.get("success") is False:
            return {
                **result,
                "vehicle_crsp_id": crsp_id,
            }

        # --------------------------------------------------------------
        # 5. Normalize response
        # --------------------------------------------------------------

        result = self._normalize_result(result)

        # --------------------------------------------------------------
        # 6. Add API metadata
        # --------------------------------------------------------------

        result["success"] = True

        result["vehicle_crsp_id"] = crsp_id

        result["calculated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        # --------------------------------------------------------------
        # 7. Attach authoritative vehicle identity
        # --------------------------------------------------------------

        result["vehicle"] = {
            "crsp_id": crsp_id,
            "make": vehicle.get("make"),
            "model": vehicle.get("model"),
            "trim_level": vehicle.get("trim_level"),
            "fuel": vehicle.get("fuel"),
            "engine_capacity": vehicle.get(
                "engine_capacity"
            ),
            "engine_capacity_cc": vehicle.get(
                "engine_capacity_cc"
            ),
            "body_type": vehicle.get("body_type"),
            "transmission": vehicle.get("transmission"),
            "manufacture_year": vehicle.get(
                "manufacture_year"
            ),
            "crsp_kes": vehicle.get("crsp_kes"),
        }

        return result

    # ==================================================================
    # PAYLOAD
    # ==================================================================

    @staticmethod
    def _build_payload(
        request: OwnershipCostRequest,
    ) -> Dict[str, Any]:
        """
        Build the exact JSON payload expected by:

            calculate_vehicle_running_cost_v2(jsonb)
        """

        payload: Dict[str, Any] = {
            "crsp_id": int(request.vehicle_crsp_id),

            "distance": float(request.distance),

            "annual_mileage": float(
                request.annual_mileage
            ),

            "trip_type": (
                request.trip_type.lower().strip()
            ),

            "driving_style": (
                request.driving_style.lower().strip()
            ),

            "include_insurance": bool(
                request.include_insurance
            ),

            "include_maintenance": bool(
                request.include_maintenance
            ),

            "include_tyres": bool(
                request.include_tyres
            ),

            "include_depreciation": bool(
                request.include_depreciation
            ),
        }

        # Do not send null fuel_price unnecessarily.
        if request.fuel_price is not None:
            payload["fuel_price"] = float(
                request.fuel_price
            )

        return payload

    # ==================================================================
    # RESPONSE NORMALIZATION
    # ==================================================================

    @classmethod
    def _normalize_result(
        cls,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Normalize numeric fields returned by PostgreSQL.

        This protects the API from numeric values being serialized as
        strings by PostgREST/PostgreSQL.
        """

        numeric_fields = {
            "distance",
            "annual_mileage",
            "fuel_price",
            "fuel_consumption",
            "fuel_consumption_l_per_100km",
            "purchase_price",
            "original_cost",
            "current_value",
            "resale_value",

            "fuel_cost",
            "service_cost",
            "tyre_cost",
            "insurance_cost",
            "depreciation_cost",
            "total_cost",
            "cost_per_km",

            "annual_fuel",
            "annual_service",
            "annual_tyres",
            "annual_insurance",
            "annual_depreciation",
            "annual_total",

            "monthly_fuel",
            "monthly_service",
            "monthly_tyres",
            "monthly_insurance",
            "monthly_depreciation",
            "monthly_total",

            "five_year_total",
            "total_5yr_cost",

            "category_id",
            "vehicle_age",
            "engine_capacity",
        }

        normalized = dict(result)

        for field in numeric_fields:
            if field in normalized:
                normalized[field] = cls._to_float(
                    normalized[field]
                )

        # --------------------------------------------------------------
        # Normalize rates
        # --------------------------------------------------------------

        rates = normalized.get("rates")

        if isinstance(rates, dict):
            rates = dict(rates)

            for key in (
                "fuel_cost_per_km",
                "service_cost_per_km",
                "tyre_cost_per_km",
                "insurance_rate",
                "annual_depreciation",
            ):
                if key in rates:
                    rates[key] = cls._to_float(
                        rates[key]
                    )

            normalized["rates"] = rates

        # --------------------------------------------------------------
        # Normalize yearly breakdown
        # --------------------------------------------------------------

        yearly = normalized.get("yearly_breakdown")

        if isinstance(yearly, list):
            normalized["yearly_breakdown"] = [
                cls._normalize_year(row)
                for row in yearly
                if isinstance(row, dict)
            ]

        five_year = normalized.get("fiveYearData")

        if isinstance(five_year, list):
            normalized["fiveYearData"] = [
                cls._normalize_year(row)
                for row in five_year
                if isinstance(row, dict)
            ]

        return normalized

    @classmethod
    def _normalize_year(
        cls,
        row: Dict[str, Any],
    ) -> Dict[str, Any]:
        normalized = dict(row)

        numeric_fields = {
            "year",
            "fuel",
            "service",
            "tyres",
            "insurance",
            "depreciation",
            "total",
            "value",
        }

        for field in numeric_fields:
            if field in normalized:
                normalized[field] = cls._to_float(
                    normalized[field]
                )

        return normalized

    # ==================================================================
    # NUMERIC CONVERSION
    # ==================================================================

    @staticmethod
    def _to_float(
        value: Any,
    ) -> Any:
        """
        Safely convert PostgreSQL numeric/string values to float.

        Never performs arithmetic on strings.
        """

        if value is None:
            return None

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            cleaned = value.replace(",", "").strip()

            if cleaned == "":
                return None

            try:
                return float(cleaned)
            except ValueError:
                return value

        return value
