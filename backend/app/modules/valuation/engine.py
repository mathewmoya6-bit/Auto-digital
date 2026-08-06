# app/modules/valuation/engine.py
# ================================================================
# Auto-D Kenya - Valuation Engine
# ================================================================
# TYPE: MODULE - Vehicle valuation calculation engine
# ================================================================

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class ValuationEngine:
    """
    Vehicle market valuation engine.

    Calculates:
    - Base market value
    - Depreciation
    - Mileage adjustment
    - Condition adjustment
    - Accident adjustment
    - Location adjustment
    - Confidence score
    """

    # ============================================================
    # DEFAULT MARKET FACTORS
    # ============================================================

    CONDITION_FACTORS = {
        "excellent": 1.05,
        "very_good": 1.03,  # Added very_good
        "good": 1.00,
        "fair": 0.90,
        "poor": 0.75,
    }

    LOCATION_FACTORS = {
        "nairobi": 1.03,
        "mombasa": 1.00,
        "kisumu": 0.98,
        "nakuru": 0.98,
        "eldoret": 0.97,
        "other": 0.95,
    }

    FUEL_FACTORS = {
        "petrol": 1.00,
        "diesel": 1.03,
        "hybrid": 1.08,
        "electric": 1.10,
    }


    def __init__(self):
        self.supabase = get_supabase()


    # ============================================================
    # MAIN VALUATION
    # ============================================================

    async def calculate(
        self,
        request
    ) -> Dict[str, Any]:

        try:

            vehicle = await self.get_vehicle(
                request.variant_id
            )

            if not vehicle:
                raise ValueError(
                    "Vehicle variant not found"
                )


            base_price = await self.get_base_price(
                request.variant_id
            )

            # FIXED: Use request.year instead of request.vehicle_year
            depreciation = self.calculate_depreciation(
                base_price,
                request.year  # Was: request.vehicle_year
            )


            current_value = depreciation[
                "current_value"
            ]


            adjustments = []


            # Mileage adjustment
            mileage_adjustment = (
                self.calculate_mileage_adjustment(
                    request.mileage
                )
            )

            current_value *= mileage_adjustment["factor_value"]

            adjustments.append(
                mileage_adjustment
            )


            # Condition adjustment
            condition_factor = (
                self.CONDITION_FACTORS.get(
                    request.condition.lower(),
                    1.00
                )
            )

            condition_adjustment = current_value * (condition_factor - 1)
            current_value *= condition_factor

            adjustments.append({
                "factor": "condition",
                "adjustment": round(condition_adjustment, 2),
                "percentage": round((condition_factor - 1) * 100, 2),
                "reason": f"Vehicle condition: {request.condition}"
            })


            # Accident adjustment
            if request.accident_history and request.accident_history != "none":
                accident_factor = 0.85 if request.accident_history == "minor" else 0.70 if request.accident_history == "major" else 0.55
                accident_adjustment = current_value * (accident_factor - 1)
                current_value *= accident_factor

                adjustments.append({
                    "factor": "accident_history",
                    "adjustment": round(accident_adjustment, 2),
                    "percentage": round((accident_factor - 1) * 100, 2),
                    "reason": f"Accident history: {request.accident_history}"
                })


            # Location adjustment
            location_factor = (
                self.LOCATION_FACTORS.get(
                    request.location.lower(),
                    0.95
                )
            )

            location_adjustment = current_value * (location_factor - 1)
            current_value *= location_factor

            adjustments.append({
                "factor": "location",
                "adjustment": round(location_adjustment, 2),
                "percentage": round((location_factor - 1) * 100, 2),
                "reason": f"Location: {request.location}"
            })


            # Fuel adjustment
            if request.fuel_type:
                fuel_factor = (
                    self.FUEL_FACTORS.get(
                        request.fuel_type.lower(),
                        1.00
                    )
                )
                fuel_adjustment = current_value * (fuel_factor - 1)
                current_value *= fuel_factor

                adjustments.append({
                    "factor": "fuel_type",
                    "adjustment": round(fuel_adjustment, 2),
                    "percentage": round((fuel_factor - 1) * 100, 2),
                    "reason": f"Fuel type: {request.fuel_type}"
                })


            # Ensure realistic minimum
            current_value = max(
                current_value,
                base_price * 0.15
            )


            confidence = (
                self.calculate_confidence(
                    request,
                    vehicle
                )
            )


            return {

                "vehicle": vehicle,

                "market_value":
                    round(current_value, 2),

                "price_range_low":
                    round(
                        current_value * 0.90,
                        2
                    ),

                "price_range_high":
                    round(
                        current_value * 1.10,
                        2
                    ),


                "confidence_score":
                    confidence,


                "depreciation":
                    depreciation,


                "adjustments":
                    adjustments,


                "recommendation":
                    self.generate_recommendation(
                        confidence
                    ),

                "currency":
                    "KES",

                "calculated_at":
                    datetime.now(
                        timezone.utc
                    ).isoformat()

            }


        except Exception as e:

            logger.exception(
                "Valuation calculation failed"
            )

            raise e



    # ============================================================
    # VEHICLE DATA
    # ============================================================

    async def get_vehicle(
        self,
        variant_id: int
    ) -> Optional[Dict[str, Any]]:

        try:
            # Try vehicle_variants table first
            result = (
                self.supabase
                .table("vehicle_variants")
                .select(
                    """
                    id,
                    name,
                    vehicle_models(
                        name,
                        vehicle_makes(name)
                    ),
                    fuel_type,
                    engine_size,
                    transmission,
                    body_type
                    """
                )
                .eq(
                    "id",
                    variant_id
                )
                .single()
                .execute()
            )


            if result.data:
                data = result.data
                return {
                    "variant_id": data["id"],
                    "make": data["vehicle_models"]["vehicle_makes"]["name"],
                    "model": data["vehicle_models"]["name"],
                    "variant": data["name"],
                    "year": datetime.now().year,
                    "fuel_type": data.get("fuel_type"),
                    "transmission": data.get("transmission"),
                    "engine_size": data.get("engine_size"),
                    "body_type": data.get("body_type")
                }

        except Exception as e:
            logger.warning(f"Error fetching from vehicle_variants: {str(e)}")

        # Fallback: Try vehicle_master_specs view
        try:
            result = (
                self.supabase
                .table("vehicle_master_specs")
                .select(
                    """
                    variant_id,
                    make_name,
                    model_name,
                    variant_name,
                    fuel_type_name,
                    transmission_type_name,
                    engine_size_cc,
                    body_type_name
                    """
                )
                .eq("variant_id", variant_id)
                .execute()
            )

            if result.data:
                data = result.data[0]
                return {
                    "variant_id": data.get("variant_id"),
                    "make": data.get("make_name", "Unknown"),
                    "model": data.get("model_name", "Unknown"),
                    "variant": data.get("variant_name", "Unknown"),
                    "year": datetime.now().year,
                    "fuel_type": data.get("fuel_type_name"),
                    "transmission": data.get("transmission_type_name"),
                    "engine_size": data.get("engine_size_cc"),
                    "body_type": data.get("body_type_name")
                }

        except Exception as e:
            logger.warning(f"Error fetching from vehicle_master_specs: {str(e)}")

        return None



    # ============================================================
    # BASE PRICE
    # ============================================================

    async def get_base_price(
        self,
        variant_id: int
    ) -> float:

        """
        Priority:
        1. Market average
        2. Vehicle market value
        3. Variant base price
        """

        tables = [

            "vehicle_market_values",

            "market_prices",

            "vehicle_variants"

        ]


        for table in tables:

            try:

                result = (

                    self.supabase
                    .table(table)
                    .select("*")
                    .eq(
                        "variant_id",
                        variant_id
                    )
                    .limit(1)
                    .execute()

                )


                if result.data:

                    row = result.data[0]


                    for field in [
                        "market_value",
                        "average_price",
                        "price",
                        "base_price"
                    ]:

                        if row.get(field):

                            return float(
                                row[field]
                            )


            except Exception:

                continue



        # Safe fallback

        return 1000000.0



    # ============================================================
    # DEPRECIATION
    # ============================================================

    def calculate_depreciation(
        self,
        original_value: float,
        year: int
    ) -> Dict[str, float]:


        current_year = (
            datetime.now().year
        )

        age = max(
            current_year - year,
            0
        )


        rates = [
            0.20,
            0.15,
            0.12,
            0.10,
            0.08
        ]


        value = original_value


        for i in range(age):

            rate = (
                rates[i]
                if i < len(rates)
                else 0.07
            )

            value *= (
                1 - rate
            )


        return {

            "original_value":
                original_value,

            "current_value":
                round(value,2),

            "depreciation_amount":
                round(
                    original_value-value,
                    2
                ),

            "depreciation_percentage":
                round(
                    (
                    1-value/original_value
                    )*100,
                    2
                ),

            "annual_rate":
                0.15

        }



    # ============================================================
    # ADJUSTMENTS
    # ============================================================

    def calculate_mileage_adjustment(
        self,
        mileage: int
    ):

        expected = 15000

        excess = max(
            mileage - expected,
            0
        )


        reduction = min(
            excess / 100000 * 0.10,
            0.30
        )


        return {

            "factor":
                "mileage",

            "adjustment":
                round(-(mileage * reduction), 2) if mileage > 0 else 0,

            "percentage":
                -(reduction * 100),

            "reason":
                f"{mileage} KM mileage",

            "factor_value":
                1 - reduction

        }



    def calculate_confidence(
        self,
        request,
        vehicle
    ):

        score = 70


        if request.mileage > 0:
            score += 5

        if vehicle:
            score += 10

        if request.service_history:
            score += 5

        if request.accident_history and request.accident_history != "none":
            score -= 20 if request.accident_history == "major" else 10


        return max(
            min(score,100),
            0
        )



    def generate_recommendation(
        self,
        confidence
    ):

        if confidence >= 85:
            return "High confidence valuation based on complete data"

        if confidence >= 70:
            return "Good market estimate with reasonable data availability"

        return "Limited data available; professional inspection recommended"



    # ============================================================
    # BULK VALUATION
    # ============================================================

    async def calculate_bulk(
        self,
        requests: list
    ) -> list:

        results = []

        for req in requests:

            try:

                result = await self.calculate(
                    req
                )

                results.append(result)

            except Exception as e:

                results.append({

                    "error": str(e),

                    "variant_id":
                        req.variant_id

                })

        return results
