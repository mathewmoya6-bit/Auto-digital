# app/modules/valuation/service.py
# ================================================================
# AUTO-D KENYA - VALUATION SERVICE
# ================================================================
#
# CRSP is the authoritative vehicle pricing source.
#
# IMPORTANT:
# - Uses vehicle_crsp_lookup
# - Does NOT use vehicle_variants
# - Does NOT calculate valuation independently in Python
# - Repository/database remains the valuation calculation authority
# - Supports direct CRSP ID lookup
# - Supports make/model lookup when CRSP ID is not supplied
# - Returns JSON-safe responses
#
# ================================================================

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.modules.valuation.repository import ValuationRepository

logger = logging.getLogger(__name__)


class ValuationService:
    """AUTO-D Kenya CRSP-based valuation service."""

    CRSP_TABLE = "vehicle_crsp_lookup"

    def __init__(self):
        self.repository = ValuationRepository()

        # Backward compatibility for existing code.
        self.supabase = getattr(
            self.repository,
            "supabase",
            None,
        )

        logger.info("ValuationService initialized")

    # ================================================================
    # BASIC HELPERS
    # ================================================================

    @staticmethod
    def _clean(value: Any) -> Optional[str]:
        if value is None:
            return None

        value = str(value).strip()

        return value if value else None

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _json_safe(value: Any) -> Any:
        """
        Convert common database/Python values into JSON-safe values.
        """

        if value is None:
            return None

        if isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, datetime):
            return value.isoformat()

        if isinstance(value, dict):
            return {
                str(k): ValuationService._json_safe(v)
                for k, v in value.items()
            }

        if isinstance(value, (list, tuple)):
            return [
                ValuationService._json_safe(v)
                for v in value
            ]

        return str(value)

    # ================================================================
    # CRSP LOOKUP
    # ================================================================

    def get_crsp_vehicle(
        self,
        vehicle_crsp_id: Optional[int] = None,
        make: Optional[str] = None,
        model: Optional[str] = None,
        manufacture_year: Optional[int] = None,
        engine_capacity_id: Optional[int] = None,
        crsp_id: Optional[int] = None,
        fuel_type: Optional[str] = None,
        transmission: Optional[str] = None,
        body_type: Optional[str] = None,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve a CRSP vehicle.

        Priority:

        1. vehicle_crsp_id
        2. crsp_id
        3. make + model search

        No vehicle_variants lookup is performed.
        """

        try:
            resolved_id = (
                self._safe_int(vehicle_crsp_id)
                or self._safe_int(crsp_id)
            )

            # --------------------------------------------------------
            # 1. DIRECT CRSP ID
            # --------------------------------------------------------

            if resolved_id is not None:

                logger.info(
                    "CRSP lookup by ID: %s",
                    resolved_id,
                )

                record = self.repository.get_crsp_by_id(
                    resolved_id
                )

                if record:
                    logger.info(
                        "CRSP record found: %s",
                        resolved_id,
                    )

                    return self._json_safe(record)

                logger.warning(
                    "CRSP ID %s was not found",
                    resolved_id,
                )

            # --------------------------------------------------------
            # 2. MAKE + MODEL
            # --------------------------------------------------------

            make = self._clean(make)
            model = self._clean(model)

            if not make or not model:
                logger.warning(
                    "No CRSP ID and no make/model provided for CRSP search"
                )
                return None

            logger.info(
                "CRSP search: make=%s model=%s year=%s",
                make,
                model,
                manufacture_year,
            )

            # --------------------------------------------------------
            # Exact search
            # --------------------------------------------------------

            records = self.repository.search_crsp(
                make=make,
                model=model,
                manufacture_year=manufacture_year,
                engine_capacity_id=engine_capacity_id,
                fuel=fuel_type,
                transmission=transmission,
                body_type=body_type,
                limit=50,
            )

            if records:

                selected = self._select_best_crsp(
                    records,
                    manufacture_year,
                    engine_capacity_id,
                )

                if selected:

                    logger.info(
                        "Selected CRSP record: %s",
                        selected.get("crsp_id"),
                    )

                    return self._json_safe(selected)

            # --------------------------------------------------------
            # Search without year
            # --------------------------------------------------------

            if manufacture_year is not None:

                logger.info(
                    "Retrying CRSP search without manufacture year"
                )

                records = self.repository.search_crsp(
                    make=make,
                    model=model,
                    manufacture_year=None,
                    engine_capacity_id=engine_capacity_id,
                    fuel=fuel_type,
                    transmission=transmission,
                    body_type=body_type,
                    limit=50,
                )

                if records:

                    selected = self._select_best_crsp(
                        records,
                        manufacture_year,
                        engine_capacity_id,
                    )

                    if selected:

                        logger.info(
                            "Selected CRSP record without year: %s",
                            selected.get("crsp_id"),
                        )

                        return self._json_safe(selected)

            # --------------------------------------------------------
            # Broad make/model search
            # --------------------------------------------------------

            logger.info(
                "Broad CRSP search: %s %s",
                make,
                model,
            )

            records = self.repository.search_crsp(
                make=make,
                model=model,
                manufacture_year=None,
                engine_capacity_id=None,
                fuel=None,
                transmission=None,
                body_type=None,
                limit=50,
            )

            if records:

                selected = self._select_best_crsp(
                    records,
                    manufacture_year,
                    engine_capacity_id,
                )

                if selected:

                    logger.info(
                        "Selected CRSP record from broad search: %s",
                        selected.get("crsp_id"),
                    )

                    return self._json_safe(selected)

            logger.warning(
                "No CRSP record found for %s %s",
                make,
                model,
            )

            return None

        except Exception as exc:

            logger.exception(
                "CRSP lookup failed: %s",
                exc,
            )

            return None

    # ================================================================
    # PUBLIC CRSP SEARCH
    # ================================================================

    def search_crsp(
        self,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Public synchronous CRSP search."""

        try:

            records = self.repository.search_crsp(
                make=self._clean(kwargs.get("make")),
                model=self._clean(kwargs.get("model")),
                manufacture_year=self._safe_int(
                    kwargs.get("manufacture_year")
                ),
                engine_capacity_id=self._safe_int(
                    kwargs.get("engine_capacity_id")
                ),
                fuel=(
                    kwargs.get("fuel_type")
                    or kwargs.get("fuel")
                ),
                transmission=kwargs.get("transmission"),
                body_type=kwargs.get("body_type"),
                limit=kwargs.get("limit", 25),
            )

            return self._json_safe(records or [])

        except Exception as exc:

            logger.exception(
                "CRSP search failed: %s",
                exc,
            )

            return []

    # ================================================================
    # SELECT BEST CRSP
    # ================================================================

    def _select_best_crsp(
        self,
        records: List[Dict[str, Any]],
        manufacture_year: Optional[int] = None,
        engine_capacity_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:

        if not records:
            return None

        def score(row: Dict[str, Any]) -> int:

            score_value = 0

            # Valid CRSP price
            crsp_value = self._safe_float(
                row.get("crsp_kes")
            )

            if crsp_value and crsp_value > 0:
                score_value += 30

            # Canonical record
            if row.get("canonical_id") is not None:
                score_value += 20

            # Non-duplicate
            if row.get("is_duplicate") is False:
                score_value += 20

            # Non-inferred
            if row.get("is_inferred") is False:
                score_value += 10

            # Generation
            if row.get("generation_id") is not None:
                score_value += 5

            # Engine
            if row.get("engine_capacity_id") is not None:
                score_value += 5

            # Exact year
            row_year = self._safe_int(
                row.get("manufacture_year")
            )

            if (
                manufacture_year is not None
                and row_year == manufacture_year
            ):
                score_value += 15

            # Year proximity
            if (
                manufacture_year is not None
                and row_year is not None
            ):

                difference = abs(
                    row_year - manufacture_year
                )

                if difference <= 1:
                    score_value += 10

                elif difference <= 2:
                    score_value += 5

            # Engine capacity
            row_engine = self._safe_int(
                row.get("engine_capacity_id")
            )

            if (
                engine_capacity_id is not None
                and row_engine == engine_capacity_id
            ):
                score_value += 10

            # Complete record
            if row.get("make") and row.get("model"):
                score_value += 5

            return score_value

        ranked = sorted(
            records,
            key=score,
            reverse=True,
        )

        best = ranked[0]

        logger.debug(
            "Best CRSP match score=%s crsp_id=%s",
            score(best),
            best.get("crsp_id"),
        )

        return best

    # ================================================================
    # CALCULATE VALUATION
    # ================================================================

    def calculate_valuation(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        manufacture_year: Optional[int] = None,
        mileage: int = 0,
        condition: str = "good",
        accident_history: str = "none",
        previous_owners: int = 0,
        location: Optional[str] = None,
        fuel_type: Optional[str] = None,
        transmission: Optional[str] = None,
        engine_capacity_id: Optional[int] = None,
        vehicle_crsp_id: Optional[int] = None,
        crsp_id: Optional[int] = None,
        vehicle_type: Optional[str] = None,
        body_type: Optional[str] = None,
        profit_margin_percent: float = 5.00,
        mileage_km: Optional[int] = None,
        location_name: Optional[str] = None,
        condition_name: Optional[str] = None,
        accident_status: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Calculate valuation.

        The database/repository is responsible for the actual valuation
        formula. This service only resolves the correct CRSP record and
        passes normalized inputs to the repository.
        """

        # ------------------------------------------------------------
        # Normalize
        # ------------------------------------------------------------

        make = self._clean(make)
        model = self._clean(model)

        manufacture_year = self._safe_int(
            manufacture_year
        )

        mileage_value = (
            mileage_km
            if mileage_km is not None
            else mileage
        )

        mileage_value = self._safe_int(
            mileage_value
        ) or 0

        location_value = (
            self._clean(location_name)
            or self._clean(location)
        )

        condition_value = (
            self._clean(condition_name)
            or self._clean(condition)
            or "good"
        )

        accident_value = (
            self._clean(accident_status)
            or self._clean(accident_history)
            or "none"
        )

        vehicle_type = (
            self._clean(vehicle_type)
            or self._clean(body_type)
        )

        # ------------------------------------------------------------
        # Resolve CRSP
        # ------------------------------------------------------------

        crsp = self.get_crsp_vehicle(
            vehicle_crsp_id=vehicle_crsp_id,
            crsp_id=crsp_id,
            make=make,
            model=model,
            manufacture_year=manufacture_year,
            engine_capacity_id=engine_capacity_id,
            fuel_type=fuel_type,
            transmission=transmission,
            body_type=body_type,
        )

        if not crsp:

            resolved_id = (
                self._safe_int(vehicle_crsp_id)
                or self._safe_int(crsp_id)
            )

            logger.warning(
                "Valuation cannot proceed: CRSP record not found "
                "make=%s model=%s crsp_id=%s",
                make,
                model,
                resolved_id,
            )

            return {
                "success": False,
                "status": "crsp_not_found",
                "crsp_found": False,
                "crsp_id": resolved_id,
                "crsp_value": None,
                "market_value": None,
                "retail_value": None,
                "trade_value": None,
                "dealer_value": None,
                "recommended_selling_price": None,
                "currency": "KES",
                "message": (
                    "No CRSP record found. "
                    "Please provide a valid CRSP vehicle."
                ),
                "warnings": [
                    "CRSP record not found"
                ],
                "comparables": [],
                "sample_size": 0,
                "calculated_at": datetime.now().isoformat(),
            }

        # ------------------------------------------------------------
        # CRSP ID
        # ------------------------------------------------------------

        resolved_crsp_id = self._safe_int(
            crsp.get("crsp_id")
        )

        crsp_value = self._safe_float(
            crsp.get("crsp_kes")
        )

        if resolved_crsp_id is None:

            return {
                "success": False,
                "status": "invalid_crsp",
                "crsp_found": False,
                "message": "CRSP record does not contain a valid crsp_id.",
                "warnings": [
                    "Invalid CRSP record"
                ],
            }

        # ------------------------------------------------------------
        # Database calculation
        # ------------------------------------------------------------

        try:

            repository_method = getattr(
                self.repository,
                "calculate_valuation",
                None,
            )

            if not callable(repository_method):

                logger.error(
                    "ValuationRepository.calculate_valuation() "
                    "does not exist"
                )

                return {
                    "success": False,
                    "status": "configuration_error",
                    "message": (
                        "Valuation repository calculation method "
                        "is not available."
                    ),
                }

            # Preferred current signature
            try:

                result = repository_method(
                    vehicle_crsp_id=resolved_crsp_id,
                    manufacture_year=manufacture_year,
                    mileage_km=mileage_value,
                    vehicle_type=vehicle_type,
                    condition_name=condition_value,
                    accident_status=accident_value,
                    location_name=location_value,
                    profit_margin_percent=profit_margin_percent,
                )

            except TypeError:

                # Compatibility with older repository signature
                logger.warning(
                    "Using legacy ValuationRepository "
                    "calculate_valuation signature"
                )

                result = repository_method(
                    resolved_crsp_id,
                    manufacture_year,
                    mileage_value,
                    vehicle_type,
                    condition_value,
                    accident_value,
                    location_value,
                    profit_margin_percent,
                )

            result = self._json_safe(result)

            # --------------------------------------------------------
            # Normalize response
            # --------------------------------------------------------

            response = {
                "success": True,
                "status": "completed",
                "crsp_found": True,
                "crsp_id": resolved_crsp_id,
                "crsp_value": crsp_value,
                "currency": "KES",
                "vehicle": {
                    "crsp_id": resolved_crsp_id,
                    "make": crsp.get("make") or make,
                    "model": crsp.get("model") or model,
                    "manufacture_year": (
                        crsp.get("manufacture_year")
                        or manufacture_year
                    ),
                    "fuel": crsp.get("fuel") or fuel_type,
                    "transmission": (
                        crsp.get("transmission")
                        or transmission
                    ),
                    "body_type": (
                        crsp.get("body_type")
                        or body_type
                    ),
                    "engine_capacity": crsp.get(
                        "engine_capacity"
                    ),
                    "engine_capacity_id": crsp.get(
                        "engine_capacity_id"
                    ),
                },
                "valuation": result,
                "message": "Valuation completed successfully.",
                "warnings": [],
                "comparables": [],
                "sample_size": 1,
                "calculated_at": datetime.now().isoformat(),
            }

            # Preserve common frontend fields if returned by DB.
            if isinstance(result, dict):

                for field in (
                    "market_value",
                    "retail_value",
                    "trade_value",
                    "dealer_value",
                    "recommended_selling_price",
                    "estimated_value",
                    "estimated_value_min",
                    "estimated_value_max",
                    "confidence_score",
                    "adjustments",
                    "depreciation",
                    "cost_per_km",
                    "total_cost",
                ):

                    if field in result:
                        response[field] = result[field]

            logger.info(
                "Valuation completed successfully: CRSP ID=%s",
                resolved_crsp_id,
            )

            return response

        except Exception as exc:

            logger.exception(
                "Valuation calculation failed: %s",
                exc,
            )

            # IMPORTANT:
            # Return a string message, not an exception object/list.
            # This prevents frontend:
            # "Valuation failed: [object Object]"
            return {
                "success": False,
                "status": "calculation_error",
                "crsp_found": True,
                "crsp_id": resolved_crsp_id,
                "crsp_value": crsp_value,
                "message": (
                    "Valuation calculation failed: "
                    f"{str(exc)}"
                ),
                "error": str(exc),
                "warnings": [
                    "Database valuation calculation failed"
                ],
                "calculated_at": datetime.now().isoformat(),
            }


# ================================================================
# SERVICE FACTORY
# ================================================================

def get_valuation_service() -> ValuationService:
    """Return a valuation service instance."""

    return ValuationService()
