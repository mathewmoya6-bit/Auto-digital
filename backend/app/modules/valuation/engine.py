# app/modules/valuation/engine.py
# ================================================================
# Auto-D Kenya - Vehicle Valuation Engine
# ================================================================

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ValuationEngine:
    """
    Vehicle valuation calculation engine.
    """

    def __init__(self):
        self.current_year = datetime.utcnow().year

        self.condition_factors = {
            "excellent": 1.08,
            "very_good": 1.04,
            "good": 1.00,
            "fair": 0.92,
            "poor": 0.80,
        }

        self.accident_factors = {
            "none": 1.00,
            "minor": 0.97,
            "major": 0.90,
            "total_loss": 0.60,
        }

        self.location_factors = {
            "nairobi": 1.00,
            "mombasa": 0.98,
            "kisumu": 0.97,
            "nakuru": 0.97,
            "eldoret": 0.96,
        }

    async def calculate(
        self,
        variant_id: int,
        year: int,
        mileage: int,
        condition: str,
        accident_history: str,
        location: str,
        variant_data: Dict[str, Any],
    ) -> Dict[str, Any]:

        base_price = self._get_base_price(variant_data)

        age_factor = self._age_factor(year)

        mileage_factor = self._mileage_factor(mileage)

        condition_factor = self.condition_factors.get(
            condition.lower(),
            1.00,
        )

        accident_factor = self.accident_factors.get(
            accident_history.lower(),
            1.00,
        )

        location_factor = self.location_factors.get(
            location.lower(),
            1.00,
        )

        market_value = (
            base_price
            * age_factor
            * mileage_factor
            * condition_factor
            * accident_factor
            * location_factor
        )

        retail_value = market_value * 1.08
        trade_value = market_value * 0.88
        dealer_value = market_value * 0.95

        confidence = self._confidence(
            year,
            mileage,
            variant_data,
        )

        return {
            "market_value": round(market_value, 2),
            "retail_value": round(retail_value, 2),
            "trade_value": round(trade_value, 2),
            "dealer_value": round(dealer_value, 2),
            "confidence_score": confidence,
            "sample_size": 25,
            "comparables": [],
            "market_trend": "Stable",
            "adjustments": {
                "age_factor": round(age_factor, 3),
                "mileage_factor": round(mileage_factor, 3),
                "condition_factor": round(condition_factor, 3),
                "accident_factor": round(accident_factor, 3),
                "location_factor": round(location_factor, 3),
            },
        }

    # --------------------------------------------------------

    def _get_base_price(self, variant: Dict[str, Any]) -> float:

        candidates = [
            "market_value",
            "base_price",
            "price",
            "msrp",
            "estimated_value",
            "value",
        ]

        for key in candidates:
            value = variant.get(key)

            if value not in (None, "", 0):
                try:
                    return float(value)
                except Exception:
                    pass

        return 2_500_000.0

    # --------------------------------------------------------

    def _age_factor(self, year: int) -> float:

        age = max(0, self.current_year - year)

        factor = 1 - (age * 0.055)

        return max(0.30, factor)

    # --------------------------------------------------------

    def _mileage_factor(self, mileage: int) -> float:

        expected = 20000

        ratio = mileage / expected

        if ratio <= 1:
            return 1.00

        penalty = (ratio - 1) * 0.02

        return max(0.70, 1 - penalty)

    # --------------------------------------------------------

    def _confidence(
        self,
        year: int,
        mileage: int,
        variant: Dict[str, Any],
    ) -> float:

        score = 90

        age = self.current_year - year

        score -= age * 1.2

        if mileage > 150000:
            score -= 8

        if mileage > 250000:
            score -= 10

        if not variant.get("market_value"):
            score -= 12

        if not variant.get("engine_size_cc"):
            score -= 3

        if not variant.get("body_type_name"):
            score -= 3

        return max(35, min(98, round(score, 1)))
