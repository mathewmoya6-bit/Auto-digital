# app/modules/valuation/service.py

"""
AUTO-D Kenya
Vehicle Valuation Service

Coordinates:
- Vehicle master data
- CRSP base prices
- Depreciation
- Mileage
- Condition
- Accident history
- Previous owners
- Location
- Market adjustments

The service is intentionally tolerant of optional vehicle data so that
a missing CRSP match does not cause the entire valuation to fail.
"""

import logging
from typing import Any, Dict, Optional

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class ValuationService:

    def __init__(self):
        self.supabase = get_supabase()

    # ================================================================
    # MAIN VALUATION
    # ================================================================

    async def calculate_valuation(
        self,
        vehicle_id: Optional[int] = None,
        vehicle_crsp_id: Optional[int] = None,
        make: Optional[str] = None,
        model: Optional[str] = None,
        year: Optional[int] = None,
        mileage: float = 0,
        condition: str = "good",
        accident_history: str = "none",
        previous_owners: int = 0,
        county: Optional[str] = None,
        location: Optional[str] = None,
        fuel_type: Optional[str] = None,
        transmission: Optional[str] = None,
        engine_capacity: Optional[Any] = None,
        engine_capacity_cc: Optional[int] = None,
        body_type: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Calculate vehicle valuation.

        vehicle_crsp_id is optional.

        If supplied, it is used to retrieve the CRSP base price.
        If not supplied, the service attempts to find a CRSP record
        using make/model.
        """

        try:
            # --------------------------------------------------------
            # Normalise values
            # --------------------------------------------------------

            condition = self._normalise_condition(condition)
            accident_history = self._normalise_accident(accident_history)

            try:
                mileage = float(mileage or 0)
            except (TypeError, ValueError):
                mileage = 0

            try:
                previous_owners = int(previous_owners or 0)
            except (TypeError, ValueError):
                previous_owners = 0

            # --------------------------------------------------------
            # Get CRSP
            # --------------------------------------------------------

            crsp = await self._get_crsp_vehicle(
                vehicle_crsp_id=vehicle_crsp_id,
                make=make,
                model=model,
                body_type=body_type,
            )

            crsp_id = None
            crsp_value = 0.0

            if crsp:
                crsp_id = crsp.get("id")

                raw_crsp = (
                    crsp.get("crsp_kes")
                    or crsp.get("crsp")
                    or crsp.get("crsp_value")
                    or crsp.get("base_price")
                    or 0
                )

                try:
                    crsp_value = float(raw_crsp)
                except (TypeError, ValueError):
                    crsp_value = 0.0

            # --------------------------------------------------------
            # Base value
            # --------------------------------------------------------

            if crsp_value > 0:
                base_value = crsp_value
            else:
                base_value = await self._get_market_base_price(
                    vehicle_id=vehicle_id,
                    make=make,
                    model=model,
                    body_type=body_type,
                )

            # --------------------------------------------------------
            # If no base price exists
            # --------------------------------------------------------

            if base_value <= 0:
                logger.warning(
                    "No CRSP/base price found for %s %s",
                    make,
                    model,
                )

                return {
                    "success": False,
                    "estimated_value": 0,
                    "min_value": 0,
                    "max_value": 0,
                    "confidence_score": 0,
                    "crsp_id": crsp_id,
                    "crsp_value": 0,
                    "message": "No matching CRSP or market base price found.",
                    "adjustments": {},
                }

            # --------------------------------------------------------
            # Depreciation
            # --------------------------------------------------------

            depreciation_rate = await self._get_depreciation_rate(
                body_type=body_type,
                vehicle_type=body_type,
                age=self._vehicle_age(year),
            )

            age = self._vehicle_age(year)

            depreciation_factor = max(
                0.05,
                1 - (depreciation_rate * age),
            )

            age_adjusted_value = base_value * depreciation_factor

            # --------------------------------------------------------
            # Mileage
            # --------------------------------------------------------

            mileage_factor = self._mileage_factor(mileage)

            after_mileage = (
                age_adjusted_value * mileage_factor
            )

            # --------------------------------------------------------
            # Condition
            # --------------------------------------------------------

            condition_factor = {
                "excellent": 1.10,
                "very_good": 1.05,
                "good": 1.00,
                "fair": 0.90,
                "poor": 0.75,
            }.get(condition, 1.00)

            after_condition = (
                after_mileage * condition_factor
            )

            # --------------------------------------------------------
            # Accident
            # --------------------------------------------------------

            accident_factor = {
                "none": 1.00,
                "minor": 0.90,
                "major": 0.70,
                "total_loss": 0.00,
            }.get(accident_history, 1.00)

            after_accident = (
                after_condition * accident_factor
            )

            # --------------------------------------------------------
            # Previous owners
            # --------------------------------------------------------

            owner_factor = max(
                0.90,
                1 - (max(previous_owners - 1, 0) * 0.02),
            )

            after_owners = (
                after_accident * owner_factor
            )

            # --------------------------------------------------------
            # Location adjustment
            # --------------------------------------------------------

            location_factor = self._location_factor(
                county or location
            )

            estimated_value = (
                after_owners * location_factor
            )

            # --------------------------------------------------------
            # Safety limits
            # --------------------------------------------------------

            estimated_value = max(
                0,
                round(estimated_value, 2),
            )

            min_value = round(
                estimated_value * 0.90,
                2,
            )

            max_value = round(
                estimated_value * 1.10,
                2,
            )

            # --------------------------------------------------------
            # Confidence
            # --------------------------------------------------------

            confidence = self._confidence_score(
                crsp_value=crsp_value,
                mileage=mileage,
                year=year,
                condition=condition,
            )

            adjustments = {
                "age": round(
                    (depreciation_factor - 1) * 100,
                    2,
                ),
                "mileage": round(
                    (mileage_factor - 1) * 100,
                    2,
                ),
                "condition": round(
                    (condition_factor - 1) * 100,
                    2,
                ),
                "accident": round(
                    (accident_factor - 1) * 100,
                    2,
                ),
                "previous_owners": round(
                    (owner_factor - 1) * 100,
                    2,
                ),
                "location": round(
                    (location_factor - 1) * 100,
                    2,
                ),
            }

            return {
                "success": True,

                "estimated_value": estimated_value,
                "min_value": min_value,
                "max_value": max_value,

                "confidence_score": confidence,

                "crsp_id": crsp_id,
                "crsp_value": round(crsp_value, 2),

                "base_value": round(base_value, 2),

                "vehicle": {
                    "vehicle_id": vehicle_id,
                    "crsp_id": crsp_id,
                    "make": make,
                    "model": model,
                    "year": year,
                    "mileage": mileage,
                    "condition": condition,
                    "accident_history": accident_history,
                    "previous_owners": previous_owners,
                    "county": county or location,
                    "fuel_type": fuel_type,
                    "transmission": transmission,
                    "engine_capacity": engine_capacity,
                    "engine_capacity_cc": engine_capacity_cc,
                    "body_type": body_type,
                },

                "adjustments": adjustments,

                "message": (
                    "Valuation completed successfully."
                ),
            }

        except Exception as exc:
            logger.exception(
                "Vehicle valuation failed"
            )

            raise RuntimeError(
                f"Valuation failed: {exc}"
            ) from exc

    # ================================================================
    # CRSP LOOKUP
    # ================================================================

    async def _get_crsp_vehicle(
        self,
        vehicle_crsp_id: Optional[int] = None,
        make: Optional[str] = None,
        model: Optional[str] = None,
        body_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:

        # ------------------------------------------------------------
        # 1. Exact CRSP ID
        # ------------------------------------------------------------

        if vehicle_crsp_id:

            result = (
                self.supabase
                .table("vehicle_crsp")
                .select("*")
                .eq("id", vehicle_crsp_id)
                .limit(1)
                .execute()
            )

            if result.data:
                return result.data[0]

        # ------------------------------------------------------------
        # 2. Try vehicle master CRSP table
        # ------------------------------------------------------------

        if not make or not model:
            return None

        try:

            result = (
                self.supabase
                .table("vehicle_crsp")
                .select("*")
                .ilike("make", make)
                .ilike("model", model)
                .limit(5)
                .execute()
            )

            if result.data:

                # Prefer matching body type
                if body_type:
                    for row in result.data:
                        row_body = (
                            row.get("body_type")
                            or ""
                        )

                        if (
                            row_body.upper()
                            == body_type.upper()
                        ):
                            return row

                return result.data[0]

        except Exception as exc:

            logger.warning(
                "vehicle_crsp lookup failed: %s",
                exc,
            )

        # ------------------------------------------------------------
        # 3. Try vehicle_models / CRSP master
        # ------------------------------------------------------------

        try:

            result = (
                self.supabase
                .table("vehicle_models")
                .select("*")
                .ilike("make", make)
                .ilike("model", model)
                .limit(5)
                .execute()
            )

            if result.data:
                return result.data[0]

        except Exception as exc:

            logger.warning(
                "vehicle_models CRSP lookup failed: %s",
                exc,
            )

        return None

    # ================================================================
    # MARKET BASE PRICE
    # ================================================================

    async def _get_market_base_price(
        self,
        vehicle_id: Optional[int],
        make: Optional[str],
        model: Optional[str],
        body_type: Optional[str],
    ) -> float:

        if vehicle_id:

            try:

                result = (
                    self.supabase
                    .table("vehicle_base_prices")
                    .select("*")
                    .eq("vehicle_id", vehicle_id)
                    .limit(1)
                    .execute()
                )

                if result.data:

                    row = result.data[0]

                    return float(
                        row.get("base_price")
                        or row.get("market_value")
                        or 0
                    )

            except Exception as exc:

                logger.warning(
                    "Vehicle base price lookup failed: %s",
                    exc,
                )

        return 0.0

    # ================================================================
    # DEPRECIATION
    # ================================================================

    async def _get_depreciation_rate(
        self,
        body_type: Optional[str] = None,
        vehicle_type: Optional[str] = None,
        age: int = 0,
    ) -> float:

        vehicle_type = (
            vehicle_type
            or body_type
            or "SEDAN"
        ).upper().strip()

        # Map your frontend categories to depreciation categories
        category_map = {
            "SEDAN": "SEDAN",
            "SUV": "SUV",
            "MPV": "SEDAN",
            "HATCHBACK": "SEDAN",
            "WAGON": "SEDAN",
            "COUPE": "SEDAN",
            "CONVERTIBLE": "SEDAN",
            "LUXURY": "LUXURY",
            "COMMERCIAL": "COMMERCIAL",
            "VAN": "COMMERCIAL",
            "BUS": "COMMERCIAL",
            "TRUCK": "COMMERCIAL",
            "PICKUP": "PICKUP",
            "ELECTRIC": "ELECTRIC",
            "OTHER": "SEDAN",
        }

        category = category_map.get(
            vehicle_type,
            "SEDAN",
        )

        try:

            result = (
                self.supabase
                .table("depreciation_rates")
                .select("*")
                .ilike(
                    "vehicle_type",
                    category,
                )
                .limit(1)
                .execute()
            )

            if result.data:

                row = result.data[0]

                rate = (
                    row.get("depreciation_rate")
                    or row.get("annual_rate")
                    or row.get("rate")
                    or 0.08
                )

                rate = float(rate)

                # Support databases storing 8 instead of 0.08
                if rate > 1:
                    rate = rate / 100

                return rate

        except Exception as exc:

            logger.warning(
                "Depreciation lookup failed: %s",
                exc,
            )

        # Sensible defaults
        defaults = {
            "SEDAN": 0.08,
            "SUV": 0.075,
            "LUXURY": 0.10,
            "COMMERCIAL": 0.09,
            "PICKUP": 0.085,
            "ELECTRIC": 0.07,
        }

        return defaults.get(
            category,
            0.08,
        )

    # ================================================================
    # HELPERS
    # ================================================================

    @staticmethod
    def _vehicle_age(year: Optional[int]) -> int:

        if not year:
            return 0

        try:
            from datetime import datetime

            current_year = datetime.now().year

            return max(
                0,
                current_year - int(year),
            )

        except Exception:
            return 0

    @staticmethod
    def _mileage_factor(
        mileage: float,
    ) -> float:

        if mileage <= 0:
            return 1.00

        if mileage <= 20_000:
            return 1.02

        if mileage <= 50_000:
            return 1.00

        if mileage <= 100_000:
            return 0.95

        if mileage <= 150_000:
            return 0.90

        if mileage <= 200_000:
            return 0.84

        return 0.78

    @staticmethod
    def _location_factor(
        location: Optional[str],
    ) -> float:

        if not location:
            return 1.00

        location = location.upper().strip()

        factors = {
            "NAIROBI": 1.03,
            "MOMBASA": 1.01,
            "KIAMBU": 1.02,
            "NAKURU": 1.00,
            "ELDORET": 0.99,
            "KISUMU": 0.99,
            "THIKA": 1.01,
            "KAJIADO": 1.00,
            "MACHAKOS": 0.99,
            "MERU": 0.98,
            "NYERI": 0.98,
            "EMBU": 0.98,
            "MALINDI": 0.99,
            "NANYUKI": 0.98,
        }

        return factors.get(
            location,
            1.00,
        )

    @staticmethod
    def _confidence_score(
        crsp_value: float,
        mileage: float,
        year: Optional[int],
        condition: str,
    ) -> int:

        score = 70

        if crsp_value > 0:
            score += 15

        if year:
            score += 5

        if mileage >= 0:
            score += 3

        if condition in (
            "excellent",
            "very_good",
            "good",
        ):
            score += 3

        return min(
            99,
            score,
        )

    @staticmethod
    def _normalise_condition(
        condition: Optional[str],
    ) -> str:

        value = (
            condition
            or "good"
        ).lower().strip()

        aliases = {
            "very good": "very_good",
            "verygood": "very_good",
            "excellent": "excellent",
            "good": "good",
            "fair": "fair",
            "poor": "poor",
        }

        return aliases.get(
            value,
            "good",
        )

    @staticmethod
    def _normalise_accident(
        accident: Optional[str],
    ) -> str:

        value = (
            accident
            or "none"
        ).lower().strip()

        aliases = {
            "no accident": "none",
            "none": "none",
            "minor": "minor",
            "major": "major",
            "total loss": "total_loss",
            "total_loss": "total_loss",
        }

        return aliases.get(
            value,
            "none",
        )


# ================================================================
# SINGLETON
# ================================================================

valuation_service = ValuationService()
