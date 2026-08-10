# app/modules/valuation/engine.py
# ================================================================
# Auto-D Kenya - Valuation Engine
# ================================================================
# TYPE: MODULE - Valuation API/Service Adapter
#
# IMPORTANT:
# PostgreSQL calculate_vehicle_valuation() is the SINGLE SOURCE
# OF TRUTH for valuation calculations.
#
# Python does NOT calculate depreciation, adjustments, market value,
# or profit independently.
# ================================================================

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional

from app.core.database import get_supabase

logger = logging.getLogger(__name__)  # Fixed: **name** -> __name__


class ValuationEngine:
    """
    Auto-D Kenya valuation engine.

    PostgreSQL performs the actual valuation calculation.

    Python is responsible for:
        - validating request data
        - calling PostgreSQL RPC
        - normalising the response
        - building API response
        - bulk valuation orchestration

    PostgreSQL function:
        public.calculate_vehicle_valuation()
    """

    DEFAULT_PROFIT_MARGIN = Decimal("5.00")

    def __init__(self):
        """Initialize the valuation engine."""
        self.supabase = get_supabase()
        logger.info("ValuationEngine initialized")

    # ============================================================
    # MAIN VALUATION
    # ============================================================

    async def calculate(self, request) -> Dict[str, Any]:
        """
        Calculate vehicle valuation using PostgreSQL.

        PostgreSQL is the authoritative valuation engine.
        """

        try:
            self._validate_request(request)

            logger.info(
                "Starting valuation: CRSP=%s, year=%s, mileage=%s",
                getattr(request, "variant_id", None),
                getattr(request, "year", None),
                getattr(request, "mileage", 0),
            )

            result = await self._call_database_valuation(request)

            if not result:
                raise ValueError(
                    "Database valuation returned no result"
                )

            valuation = result[0] if isinstance(result, list) else result

            response = self._build_response(
                valuation,
                request
            )

            logger.info(
                "Valuation completed: CRSP=%s final=%s selling=%s confidence=%s",
                response.get("vehicle_crsp_id"),
                response.get("final_market_value"),
                response.get("recommended_selling_price"),
                response.get("confidence_score"),
            )

            return response

        except Exception as exc:
            logger.exception(
                "Valuation calculation failed: %s",
                exc
            )

            # IMPORTANT:
            # Do NOT manufacture a fake valuation.
            # Return an explicit error so the API knows valuation failed.
            raise

    # ============================================================
    # REQUEST VALIDATION
    # ============================================================

    def _validate_request(self, request) -> None:
        """Validate valuation request before calling PostgreSQL."""

        crsp_id = getattr(request, "variant_id", None)

        if crsp_id is None:
            raise ValueError(
                "vehicle_crsp_id / variant_id is required"
            )

        year = getattr(request, "year", None)

        if year is None:
            raise ValueError(
                "manufacture year is required"
            )

        current_year = datetime.now(timezone.utc).year

        if year < 1900 or year > current_year + 1:
            raise ValueError(
                f"Invalid manufacture year: {year}"
            )

        mileage = getattr(request, "mileage", 0)

        if mileage is None:
            mileage = 0

        if mileage < 0:
            raise ValueError(
                "Mileage cannot be negative"
            )

    # ============================================================
    # DATABASE VALUATION
    # ============================================================

    async def _call_database_valuation(
        self,
        request
    ) -> List[Dict[str, Any]]:
        """
        Call PostgreSQL calculate_vehicle_valuation().

        The database function handles:

            CRSP resolution
            duplicate CRSP resolution
            depreciation
            depreciation interpolation
            mileage adjustment
            condition adjustment
            accident adjustment
            location adjustment
            model market adjustment
            final market value
            5% profit margin
            recommended selling price
            confidence score
            valuation reference
            result persistence
        """

        crsp_id = getattr(request, "variant_id")

        manufacture_year = getattr(request, "year")

        mileage_km = getattr(
            request,
            "mileage",
            0
        ) or 0

        vehicle_type = getattr(
            request,
            "vehicle_type",
            "SEDAN"
        ) or "SEDAN"

        condition_name = getattr(
            request,
            "condition",
            "GOOD"
        ) or "GOOD"

        accident_status = getattr(
            request,
            "accident_history",
            "NONE"
        ) or "NONE"

        location_name = getattr(
            request,
            "location",
            "NAIROBI"
        ) or "NAIROBI"

        profit_margin = getattr(
            request,
            "profit_margin_percent",
            self.DEFAULT_PROFIT_MARGIN
        )

        if profit_margin is None:
            profit_margin = self.DEFAULT_PROFIT_MARGIN

        logger.info(
            "Calling calculate_vehicle_valuation("
            "crsp=%s, year=%s, mileage=%s, type=%s, "
            "condition=%s, accident=%s, location=%s, profit=%s)",
            crsp_id,
            manufacture_year,
            mileage_km,
            vehicle_type,
            condition_name,
            accident_status,
            location_name,
            profit_margin,
        )

        rpc_params = {
            "p_vehicle_crsp_id": int(crsp_id),
            "p_manufacture_year": int(manufacture_year),
            "p_mileage_km": int(mileage_km),
            "p_vehicle_type": str(vehicle_type).upper().strip(),
            "p_condition_name": str(condition_name).upper().strip(),
            "p_accident_status": str(accident_status).upper().strip(),
            "p_location_name": str(location_name).upper().strip(),
            "p_profit_margin_percent": float(profit_margin),
        }

        response = self.supabase.rpc(
            "calculate_vehicle_valuation",
            rpc_params
        ).execute()

        if response is None:
            raise ValueError(
                "No response received from valuation RPC"
            )

        if not response.data:
            raise ValueError(
                "Valuation RPC returned no rows"
            )

        return response.data

    # ============================================================
    # RESPONSE BUILDER
    # ============================================================

    def _build_response(
        self,
        valuation: Dict[str, Any],
        request
    ) -> Dict[str, Any]:
        """
        Convert PostgreSQL valuation result into API response.
        """

        def money(value):
            if value is None:
                return None

            return float(
                Decimal(str(value)).quantize(
                    Decimal("0.01")
                )
            )

        def number(value):
            if value is None:
                return None

            return float(value)

        final_market_value = money(
            valuation.get("final_market_value")
        )

        recommended_selling_price = money(
            valuation.get(
                "recommended_selling_price"
            )
        )

        profit_margin_value = money(
            valuation.get(
                "profit_margin_value"
            )
        )

        response = {
            # ----------------------------------------------------
            # Vehicle
            # ----------------------------------------------------

            "vehicle_crsp_id": valuation.get(
                "vehicle_crsp_id"
            ),

            "make": valuation.get("make"),

            "model": valuation.get("model"),

            "manufacture_year": valuation.get(
                "manufacture_year"
            ),

            "vehicle_age": valuation.get(
                "vehicle_age"
            ),

            # ----------------------------------------------------
            # CRSP
            # ----------------------------------------------------

            "crsp_value": money(
                valuation.get("crsp_value")
            ),

            # ----------------------------------------------------
            # Depreciation
            # ----------------------------------------------------

            "depreciation_rate": number(
                valuation.get("depreciation_rate")
            ),

            "depreciation_value": money(
                valuation.get("depreciation_value")
            ),

            "value_after_depreciation": money(
                valuation.get(
                    "value_after_depreciation"
                )
            ),

            # ----------------------------------------------------
            # Adjustments
            # ----------------------------------------------------

            "mileage_adjustment": money(
                valuation.get(
                    "mileage_adjustment"
                )
            ),

            "condition_adjustment": money(
                valuation.get(
                    "condition_adjustment"
                )
            ),

            "accident_adjustment": money(
                valuation.get(
                    "accident_adjustment"
                )
            ),

            "location_adjustment": money(
                valuation.get(
                    "location_adjustment"
                )
            ),

            "market_adjustment": money(
                valuation.get(
                    "market_adjustment"
                )
            ),

            # ----------------------------------------------------
            # Final valuation
            # ----------------------------------------------------

            "final_market_value": final_market_value,

            # ----------------------------------------------------
            # Profit
            # ----------------------------------------------------

            "profit_margin_percent": number(
                valuation.get(
                    "profit_margin_percent"
                )
            ),

            "profit_margin_value": profit_margin_value,

            "recommended_selling_price":
                recommended_selling_price,

            # ----------------------------------------------------
            # Confidence
            # ----------------------------------------------------

            "confidence_score": number(
                valuation.get(
                    "confidence_score"
                )
            ),

            # ----------------------------------------------------
            # Reference
            # ----------------------------------------------------

            "valuation_reference":
                valuation.get(
                    "valuation_reference"
                ),

            # ----------------------------------------------------
            # Currency
            # ----------------------------------------------------

            "currency": "KES",

            # ----------------------------------------------------
            # Timestamp
            # ----------------------------------------------------

            "calculated_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            # ----------------------------------------------------
            # Calculation details
            # ----------------------------------------------------

            "calculation": {
                "crsp_value": money(
                    valuation.get(
                        "crsp_value"
                    )
                ),

                "depreciation_rate":
                    number(
                        valuation.get(
                            "depreciation_rate"
                        )
                    ),

                "depreciation_value":
                    money(
                        valuation.get(
                            "depreciation_value"
                        )
                    ),

                "value_after_depreciation":
                    money(
                        valuation.get(
                            "value_after_depreciation"
                        )
                    ),

                "mileage_adjustment":
                    money(
                        valuation.get(
                            "mileage_adjustment"
                        )
                    ),

                "condition_adjustment":
                    money(
                        valuation.get(
                            "condition_adjustment"
                        )
                    ),

                "accident_adjustment":
                    money(
                        valuation.get(
                            "accident_adjustment"
                        )
                    ),

                "location_adjustment":
                    money(
                        valuation.get(
                            "location_adjustment"
                        )
                    ),

                "market_adjustment":
                    money(
                        valuation.get(
                            "market_adjustment"
                        )
                    ),

                "final_market_value":
                    final_market_value,

                "profit_margin_percent":
                    number(
                        valuation.get(
                            "profit_margin_percent"
                        )
                    ),

                "profit_margin_value":
                    profit_margin_value,

                "recommended_selling_price":
                    recommended_selling_price,
            },

            # ----------------------------------------------------
            # API-friendly adjustments
            # ----------------------------------------------------

            "adjustments": [
                {
                    "factor": "mileage",
                    "value": money(
                        valuation.get(
                            "mileage_adjustment"
                        )
                    ),
                    "rate": number(
                        valuation.get(
                            "mileage_rate"
                        )
                    ),
                },
                {
                    "factor": "condition",
                    "value": money(
                        valuation.get(
                            "condition_adjustment"
                        )
                    ),
                    "rate": number(
                        valuation.get(
                            "condition_rate"
                        )
                    ),
                },
                {
                    "factor": "accident",
                    "value": money(
                        valuation.get(
                            "accident_adjustment"
                        )
                    ),
                    "rate": number(
                        valuation.get(
                            "accident_rate"
                        )
                    ),
                },
                {
                    "factor": "location",
                    "value": money(
                        valuation.get(
                            "location_adjustment"
                        )
                    ),
                    "rate": number(
                        valuation.get(
                            "location_rate"
                        )
                    ),
                },
                {
                    "factor": "market",
                    "value": money(
                        valuation.get(
                            "market_adjustment"
                        )
                    ),
                    "rate": number(
                        valuation.get(
                            "market_rate"
                        )
                    ),
                },
            ],
        }

        return response

    # ============================================================
    # BULK VALUATION
    # ============================================================

    async def calculate_bulk(
        self,
        requests: list
    ) -> List[Dict[str, Any]]:
        """
        Calculate multiple valuations.

        Each vehicle is independently processed by PostgreSQL.
        """

        results = []

        for request in requests:

            try:

                result = await self.calculate(
                    request
                )

                results.append(result)

            except Exception as exc:

                logger.exception(
                    "Bulk valuation failed for CRSP %s: %s",
                    getattr(
                        request,
                        "variant_id",
                        None
                    ),
                    exc,
                )

                results.append(
                    {
                        "error": str(exc),

                        "vehicle_crsp_id":
                            getattr(
                                request,
                                "variant_id",
                                None
                            ),

                        "status": "failed",
                    }
                )

        return results


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "ValuationEngine",
]
