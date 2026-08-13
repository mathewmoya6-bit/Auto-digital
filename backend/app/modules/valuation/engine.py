
# ================================================================
# Auto-D Kenya - Valuation Engine
# ================================================================
# TYPE: MODULE - Valuation API/Service Adapter
#
# PostgreSQL calculate_vehicle_valuation() is the SINGLE SOURCE
# OF TRUTH for valuation calculations.
#
# Python DOES NOT calculate:
#   - depreciation
#   - market adjustments
#   - final market value
#   - profit
#
# Python only:
#   - validates the request
#   - resolves the CRSP identifier
#   - calls PostgreSQL
#   - normalises the RPC response
#   - builds the API response
# ================================================================

import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class ValuationEngine:
    """
    Auto-D Kenya valuation engine.

    PostgreSQL is the authoritative valuation calculator.

    PostgreSQL function:
        public.calculate_vehicle_valuation()
    """

    DEFAULT_PROFIT_MARGIN = Decimal("5.00")

    def __init__(self):
        self.supabase = get_supabase()
        logger.info("ValuationEngine initialized")

    # ============================================================
    # MAIN VALUATION
    # ============================================================

    async def calculate(self, request) -> Dict[str, Any]:
        """
        Calculate valuation using PostgreSQL.

        No valuation is calculated in Python.
        """

        self._validate_request(request)

        crsp_id = self._get_crsp_id(request)

        logger.info(
            "Starting valuation: crsp_id=%s year=%s mileage=%s",
            crsp_id,
            getattr(request, "year", None),
            getattr(request, "mileage", 0),
        )

        try:
            result = await self._call_database_valuation(request)

        except Exception as exc:
            logger.exception(
                "Database valuation RPC failed for CRSP %s: %s",
                crsp_id,
                exc,
            )

            raise ValueError(
                f"Valuation database calculation failed for CRSP "
                f"{crsp_id}: {exc}"
            ) from exc

        if result is None:
            raise ValueError(
                f"Valuation database returned no data for CRSP {crsp_id}"
            )

        valuation = self._normalise_rpc_result(result)

        if not valuation:
            raise ValueError(
                f"Valuation database returned an empty result "
                f"for CRSP {crsp_id}"
            )

        logger.info(
            "RPC valuation response for CRSP %s: %s",
            crsp_id,
            valuation,
        )

        response = self._build_response(
            valuation,
            request,
        )

        # Make sure a real valuation was actually returned.
        if response.get("final_market_value") is None:
            raise ValueError(
                "Valuation database returned data, but "
                "final_market_value is missing. "
                f"CRSP={crsp_id}; response={valuation}"
            )

        logger.info(
            "Valuation completed: CRSP=%s final=%s selling=%s confidence=%s",
            response.get("vehicle_crsp_id"),
            response.get("final_market_value"),
            response.get("recommended_selling_price"),
            response.get("confidence_score"),
        )

        return response

    # ============================================================
    # CRSP ID RESOLUTION
    # ============================================================

    @staticmethod
    def _get_crsp_id(request) -> int:
        """
        Resolve the authoritative CRSP vehicle ID.

        New contract:
            vehicle_crsp_id

        Backward compatibility:
            variant_id
        """

        crsp_id = getattr(
            request,
            "vehicle_crsp_id",
            None,
        )

        if crsp_id is None:
            crsp_id = getattr(
                request,
                "variant_id",
                None,
            )

        if crsp_id is None:
            raise ValueError(
                "vehicle_crsp_id is required"
            )

        try:
            crsp_id = int(crsp_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid vehicle_crsp_id: {crsp_id}"
            ) from exc

        if crsp_id <= 0:
            raise ValueError(
                "vehicle_crsp_id must be greater than zero"
            )

        return crsp_id

    # ============================================================
    # REQUEST VALIDATION
    # ============================================================

    def _validate_request(self, request) -> None:
        """
        Validate valuation request.

        This does NOT perform valuation calculations.
        """

        crsp_id = self._get_crsp_id(request)

        year = getattr(
            request,
            "year",
            None,
        )

        if year is None:
            raise ValueError(
                f"Manufacture year is required for CRSP {crsp_id}"
            )

        try:
            year = int(year)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid manufacture year: {year}"
            ) from exc

        current_year = datetime.now(
            timezone.utc
        ).year

        if year < 1900 or year > current_year + 1:
            raise ValueError(
                f"Invalid manufacture year: {year}"
            )

        mileage = getattr(
            request,
            "mileage",
            0,
        )

        if mileage is None:
            mileage = 0

        try:
            mileage = int(mileage)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid mileage: {mileage}"
            ) from exc

        if mileage < 0:
            raise ValueError(
                "Mileage cannot be negative"
            )

    # ============================================================
    # DATABASE VALUATION
    # ============================================================

    async def _call_database_valuation(
        self,
        request,
    ) -> Any:
        """
        Call PostgreSQL calculate_vehicle_valuation().

        PostgreSQL performs all valuation calculations.
        """

        crsp_id = self._get_crsp_id(request)

        manufacture_year = int(
            getattr(request, "year")
        )

        mileage_km = getattr(
            request,
            "mileage",
            0,
        ) or 0

        vehicle_type = getattr(
            request,
            "vehicle_type",
            None,
        ) or "SEDAN"

        condition_name = getattr(
            request,
            "condition",
            None,
        ) or "GOOD"

        accident_status = getattr(
            request,
            "accident_history",
            None,
        ) or "NONE"

        location_name = getattr(
            request,
            "location",
            None,
        ) or "NAIROBI"

        profit_margin = getattr(
            request,
            "profit_margin_percent",
            None,
        )

        if profit_margin is None:
            profit_margin = self.DEFAULT_PROFIT_MARGIN

        try:
            profit_margin = Decimal(
                str(profit_margin)
            )
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid profit_margin_percent: {profit_margin}"
            ) from exc

        if profit_margin < 0:
            raise ValueError(
                "profit_margin_percent cannot be negative"
            )

        rpc_params = {
            "p_vehicle_crsp_id": crsp_id,
            "p_manufacture_year": manufacture_year,
            "p_mileage_km": int(mileage_km),
            "p_vehicle_type": str(
                vehicle_type
            ).strip().upper(),
            "p_condition_name": str(
                condition_name
            ).strip().upper(),
            "p_accident_status": str(
                accident_status
            ).strip().upper(),
            "p_location_name": str(
                location_name
            ).strip().upper(),
            "p_profit_margin_percent": float(
                profit_margin
            ),
        }

        logger.info(
            "Calling calculate_vehicle_valuation RPC: %s",
            rpc_params,
        )

        try:
            response = (
                self.supabase
                .rpc(
                    "calculate_vehicle_valuation",
                    rpc_params,
                )
                .execute()
            )
        except Exception as exc:
            logger.exception(
                "Supabase RPC exception for CRSP %s",
                crsp_id,
            )
            raise

        if response is None:
            raise ValueError(
                "No response received from "
                "calculate_vehicle_valuation RPC"
            )

        logger.info(
            "Valuation RPC raw response: data=%s count=%s",
            getattr(response, "data", None),
            getattr(response, "count", None),
        )

        data = getattr(
            response,
            "data",
            None,
        )

        if data is None:
            raise ValueError(
                "calculate_vehicle_valuation RPC returned "
                "NULL data"
            )

        if isinstance(data, list):
            if len(data) == 0:
                raise ValueError(
                    "calculate_vehicle_valuation RPC returned "
                    "an empty array"
                )

            return data

        if isinstance(data, dict):
            if not data:
                raise ValueError(
                    "calculate_vehicle_valuation RPC returned "
                    "an empty object"
                )

            return data

        raise ValueError(
            "Unexpected valuation RPC response type: "
            f"{type(data).__name__}"
        )

    # ============================================================
    # RPC RESULT NORMALISATION
    # ============================================================

    @staticmethod
    def _normalise_rpc_result(
        result: Any,
    ) -> Dict[str, Any]:
        """
        Normalise Supabase RPC result.

        Supports:
            - list[dict]
            - dict

        If PostgreSQL returns a single row as a list,
        use that row.
        """

        if isinstance(result, list):

            if not result:
                return {}

            first = result[0]

            if isinstance(first, dict):
                return first

            raise ValueError(
                "Valuation RPC returned a list containing "
                f"an unexpected type: {type(first).__name__}"
            )

        if isinstance(result, dict):
            return result

        raise ValueError(
            "Unexpected valuation result type: "
            f"{type(result).__name__}"
        )

    # ============================================================
    # RESPONSE BUILDER
    # ============================================================

    def _build_response(
        self,
        valuation: Dict[str, Any],
        request,
    ) -> Dict[str, Any]:
        """
        Convert PostgreSQL valuation result into API response.

        PostgreSQL remains the source of every calculated value.
        """

        def money(value):
            if value is None:
                return None

            try:
                return float(
                    Decimal(
                        str(value)
                    ).quantize(
                        Decimal("0.01")
                    )
                )
            except (
                InvalidOperation,
                TypeError,
                ValueError,
            ):
                return None

        def number(value):
            if value is None:
                return None

            try:
                return float(value)
            except (
                TypeError,
                ValueError,
            ):
                return None

        crsp_id = self._get_crsp_id(request)

        # --------------------------------------------------------
        # Support both current and legacy PostgreSQL field names.
        # --------------------------------------------------------

        vehicle_crsp_id = (
            valuation.get("vehicle_crsp_id")
            or valuation.get("crsp_id")
            or crsp_id
        )

        final_market_value = money(
            valuation.get("final_market_value")
            or valuation.get("market_value")
            or valuation.get("final_value")
        )

        recommended_selling_price = money(
            valuation.get(
                "recommended_selling_price"
            )
            or valuation.get(
                "selling_price"
            )
        )

        crsp_value = money(
            valuation.get("crsp_value")
            or valuation.get("crsp_kes")
            or valuation.get("base_price")
        )

        profit_margin_value = money(
            valuation.get(
                "profit_margin_value"
            )
        )

        profit_margin_percent = number(
            valuation.get(
                "profit_margin_percent"
            )
        )

        if profit_margin_percent is None:
            profit_margin_percent = number(
                getattr(
                    request,
                    "profit_margin_percent",
                    self.DEFAULT_PROFIT_MARGIN,
                )
            )

        # --------------------------------------------------------
        # Response
        # --------------------------------------------------------

        response = {

            # Vehicle
            "vehicle_crsp_id": vehicle_crsp_id,

            "make": valuation.get(
                "make"
            ),

            "model": valuation.get(
                "model"
            ),

            "manufacture_year": (
                valuation.get(
                    "manufacture_year"
                )
                or getattr(
                    request,
                    "year",
                    None,
                )
            ),

            "vehicle_age": valuation.get(
                "vehicle_age"
            ),

            # CRSP
            "crsp_value": crsp_value,

            # Depreciation
            "depreciation_rate": number(
                valuation.get(
                    "depreciation_rate"
                )
            ),

            "depreciation_value": money(
                valuation.get(
                    "depreciation_value"
                )
            ),

            "value_after_depreciation": money(
                valuation.get(
                    "value_after_depreciation"
                )
            ),

            # Adjustments
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

            # Final valuation
            "final_market_value":
                final_market_value,

            # Profit
            "profit_margin_percent":
                profit_margin_percent,

            "profit_margin_value":
                profit_margin_value,

            "recommended_selling_price":
                recommended_selling_price,

            # Confidence
            "confidence_score": number(
                valuation.get(
                    "confidence_score"
                )
            ),

            # Reference
            "valuation_reference":
                valuation.get(
                    "valuation_reference"
                ),

            # Currency
            "currency":
                valuation.get(
                    "currency"
                )
                or "KES",

            # Timestamp
            "calculated_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            # Raw database result
            # Useful for debugging and audit.
            "database_result": valuation,

            # Calculation
            "calculation": {

                "crsp_value":
                    crsp_value,

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
                    profit_margin_percent,

                "profit_margin_value":
                    profit_margin_value,

                "recommended_selling_price":
                    recommended_selling_price,
            },

            # API-friendly adjustments
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
        requests: list,
    ) -> List[Dict[str, Any]]:
        """
        Calculate multiple valuations.

        Each valuation is independently processed by PostgreSQL.
        """

        results = []

        for request in requests:

            crsp_id = getattr(
                request,
                "vehicle_crsp_id",
                None,
            )

            if crsp_id is None:
                crsp_id = getattr(
                    request,
                    "variant_id",
                    None,
                )

            try:
                result = await self.calculate(
                    request
                )

                results.append(result)

            except Exception as exc:

                logger.exception(
                    "Bulk valuation failed for CRSP %s: %s",
                    crsp_id,
                    exc,
                )

                results.append(
                    {
                        "error": str(exc),
                        "vehicle_crsp_id": crsp_id,
                        "status": "failed",
                    }
                )

        return results


# ================================================================
# EXPORTS
# ================================================================

__all__ = [
    "ValuationEngine",
]

