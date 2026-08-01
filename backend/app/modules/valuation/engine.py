# app/modules/valuation/engine.py
# ================================================================
# Auto-D Kenya - Valuation Engine
# ================================================================
# TYPE: MODULE - Vehicle valuation calculation engine
# ================================================================

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from app.core.config import settings
from app.core.database import get_supabase


logger = logging.getLogger(__name__)


class ValuationEngine:
    """
    Vehicle valuation calculation engine.

    Factors:
    - Base market price
    - Vehicle age depreciation
    - Mileage adjustment
    - Location factor
    - Condition factor
    - Accident history
    """


    def __init__(self):

        self.supabase = get_supabase()



    # ============================================================
    # AGE FACTOR
    # ============================================================

    def calculate_age_factor(
        self,
        year: int
    ) -> float:

        age = datetime.now().year - year


        if age <= 0:
            return 1.00

        if age <= 1:
            return 0.95

        if age <= 2:
            return 0.90

        if age <= 3:
            return 0.85

        if age <= 5:
            return 0.75

        if age <= 7:
            return 0.65

        if age <= 10:
            return 0.50

        if age <= 15:
            return 0.30

        return 0.20



    # ============================================================
    # MILEAGE FACTOR
    # ============================================================

    def calculate_mileage_factor(
        self,
        mileage: int,
        age: int
    ) -> float:


        if mileage <= 0:
            return 1.00


        expected = max(
            age * 20000,
            10000
        )


        ratio = mileage / expected


        if ratio <= 0.5:
            return 1.05

        if ratio <= 0.75:
            return 1.02

        if ratio <= 1:
            return 1.00

        if ratio <= 1.25:
            return 0.97

        if ratio <= 1.5:
            return 0.93

        if ratio <= 2:
            return 0.85

        return 0.75



    # ============================================================
    # LOCATION FACTOR
    # ============================================================

    def get_location_factor(
        self,
        location: str
    ) -> float:


        factors = {

            "nairobi": 1.05,
            "mombasa": 1.02,
            "kisumu": 1.00,
            "nakuru": 1.00,
            "eldoret": 1.00,
            "kiambu": 1.02,
            "thika": 1.00,
            "other": 1.00

        }


        return factors.get(
            location.lower(),
            1.00
        )



    # ============================================================
    # CONDITION FACTOR
    # ============================================================

    def get_condition_factor(
        self,
        condition: str
    ) -> float:


        factors = {

            "excellent": 1.10,
            "very_good": 1.05,
            "good": 1.00,
            "fair": 0.90,
            "poor": 0.75

        }


        return factors.get(
            condition.lower(),
            1.00
        )



    # ============================================================
    # ACCIDENT FACTOR
    # ============================================================

    def get_accident_factor(
        self,
        accident_history: str
    ) -> float:


        factors = {

            "none": 1.00,
            "minor": 0.92,
            "major": 0.80,
            "total_loss": 0.60

        }


        return factors.get(
            accident_history.lower(),
            1.00
        )



    # ============================================================
    # BASE PRICE
    # ============================================================

    async def get_base_price(
        self,
        variant_id: int
    ) -> float:


        try:

            variant = (

                self.supabase
                .table("vehicle_variants")
                .select("*")
                .eq(
                    "id",
                    variant_id
                )
                .execute()

            )


            if variant.data:

                price = variant.data[0].get(
                    "base_price"
                )

                if price:

                    return float(price)



            market = (

                self.supabase
                .table("market_prices")
                .select("avg_price")
                .eq(
                    "variant_id",
                    variant_id
                )
                .execute()

            )


            if market.data:

                price = market.data[0].get(
                    "avg_price"
                )

                if price:

                    return float(price)



        except Exception as e:

            logger.error(
                f"Base price error: {e}"
            )


        return float(
            settings.DEFAULT_BASE_PRICE
        )



    # ============================================================
    # CALCULATE
    # ============================================================

    async def calculate(
        self,
        variant_id: int,
        year: int,
        mileage: int,
        condition: str = "good",
        accident_history: str = "none",
        location: str = "nairobi",
        variant_data: Optional[Dict] = None

    ) -> Dict[str, Any]:


        try:


            if year > datetime.now().year:

                raise ValueError(
                    "Invalid vehicle year"
                )



            # Use provided variant data first

            if (
                variant_data
                and variant_data.get("base_price")
            ):

                base_price = float(
                    variant_data["base_price"]
                )

            else:

                base_price = await self.get_base_price(
                    variant_id
                )



            age = (
                datetime.now().year
                - year
            )


            age_factor = (
                self.calculate_age_factor(
                    year
                )
            )


            mileage_factor = (
                self.calculate_mileage_factor(
                    mileage,
                    age
                )
            )


            location_factor = (
                self.get_location_factor(
                    location
                )
            )


            condition_factor = (
                self.get_condition_factor(
                    condition
                )
            )


            accident_factor = (
                self.get_accident_factor(
                    accident_history
                )
            )



            multiplier = (

                age_factor
                *
                mileage_factor
                *
                location_factor
                *
                condition_factor
                *
                accident_factor

            )



            market_value = (
                base_price
                *
                multiplier
            )



            confidence = 70


            if variant_data:
                confidence += 10

            if base_price:
                confidence += 10

            if mileage:
                confidence += 5


            confidence = min(
                confidence,
                95
            )



            return {

                "variant_id":
                    variant_id,

                "currency":
                    "KES",

                "market_value":
                    round(
                        market_value,
                        2
                    ),

                "retail_value":
                    round(
                        market_value * 1.08,
                        2
                    ),

                "trade_value":
                    round(
                        market_value * 0.92,
                        2
                    ),

                "dealer_value":
                    round(
                        market_value * 0.95,
                        2
                    ),

                "confidence_score":
                    float(confidence),

                "base_price":
                    base_price,

                "age_factor":
                    age_factor,

                "mileage_factor":
                    mileage_factor,

                "location_factor":
                    location_factor,

                "condition_factor":
                    condition_factor,

                "accident_factor":
                    accident_factor

            }


        except Exception as e:

            logger.exception(
                f"Valuation failed: {e}"
            )

            raise
