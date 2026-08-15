"""
app/modules/valuation/engine.py

Business layer for vehicle valuation.

Flow:

    ValuationRequest
          ↓
    CRSP matching
          ↓
    calculate_vehicle_valuation()
          ↓
    vehicle_valuation_results
          ↓
    stable ValuationResponse
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from .models import CRSPRecord, ValuationResultRow
from .repository import RepositoryError, ValuationRepository
from .schemas import (
    AdjustmentsOut,
    AnalysisOut,
    CrspOut,
    ReportOut,
    ValuationDataOut,
    ValuationOut,
    ValuationRequest,
    ValuationResponse,
    VehicleOut,
)

logger = logging.getLogger(__name__)


CONDITION_MAP = {
    "excellent": "EXCELLENT",
    "very_good": "VERY_GOOD",
    "very good": "VERY_GOOD",
    "good": "GOOD",
    "fair": "FAIR",
    "poor": "POOR",
}


ACCIDENT_MAP = {
    "none": "NONE",
    "minor": "MINOR",
    "major": "MAJOR",
    "total_loss": "TOTAL_LOSS",
    "total loss": "TOTAL_LOSS",
}


class ValuationEngineError(Exception):

    def __init__(
        self,
        message: str,
        status_code: int = 400,
    ):
        super().__init__(message)

        self.message = message
        self.status_code = status_code


class ValuationEngine:

    def __init__(
        self,
        repository: ValuationRepository,
    ):
        self.repo = repository

    # ------------------------------------------------------------------
    # PUBLIC ENTRY POINT
    # ------------------------------------------------------------------

    def calculate(
        self,
        req: ValuationRequest,
    ) -> ValuationResponse:

        logger.info(
            "Valuation request: make=%r model=%r trim=%r "
            "year=%s mileage=%s",
            req.make,
            req.model,
            req.trim,
            req.year,
            req.mileage,
        )

        make = (req.make or "").strip()
        model = (req.model or "").strip()

        if not make or not model:
            raise ValuationEngineError(
                "Make and model are required for valuation",
                status_code=422,
            )

        crsp = self._select_crsp(
            req,
            make,
            model,
        )

        logger.info(
            "Selected CRSP: id=%s make=%s model=%s trim=%s year=%s",
            crsp.crsp_id,
            crsp.make,
            crsp.model,
            crsp.trim_level,
            crsp.manufacture_year,
        )

        result = self._run_valuation(
            req,
            crsp,
        )

        return self._to_response(
            result,
            req,
            crsp,
        )

    # ------------------------------------------------------------------
    # CRSP MATCHING
    # ------------------------------------------------------------------

    def _select_crsp(
        self,
        req: ValuationRequest,
        make: str,
        model: str,
    ) -> CRSPRecord:

        try:
            candidates = self.repo.find_crsp_candidates(
                make,
                model,
            )

        except RepositoryError as exc:
            raise ValuationEngineError(
                str(exc),
                status_code=502,
            ) from exc

        if not candidates:
            raise ValuationEngineError(
                f"No CRSP schedule found for {make} {model}",
                status_code=404,
            )

        requested_trim = (
            (req.trim or "")
            .strip()
            .lower()
        )

        # --------------------------------------------------------------
        # 1. Exact trim + exact year
        # --------------------------------------------------------------

        exact = [
            c
            for c in candidates
            if (
                (c.trim_level or "").strip().lower()
                == requested_trim
                and c.manufacture_year == req.year
            )
        ]

        if exact:
            return exact[0]

        # --------------------------------------------------------------
        # 2. Exact trim, any year
        # --------------------------------------------------------------

        trim_matches = [
            c
            for c in candidates
            if (
                (c.trim_level or "").strip().lower()
                == requested_trim
            )
        ]

        if trim_matches:
            return self._closest_year(
                trim_matches,
                req.year,
            )

        # --------------------------------------------------------------
        # 3. Exact year, any trim
        # --------------------------------------------------------------

        year_matches = [
            c
            for c in candidates
            if c.manufacture_year == req.year
        ]

        if year_matches:
            return year_matches[0]

        # --------------------------------------------------------------
        # 4. Closest available year
        # --------------------------------------------------------------

        return self._closest_year(
            candidates,
            req.year,
        )

    @staticmethod
    def _closest_year(
        candidates: list[CRSPRecord],
        requested_year: int,
    ) -> CRSPRecord:

        valid = [
            c
            for c in candidates
            if c.manufacture_year is not None
        ]

        if not valid:
            # CRSP exists but has no year information.
            return candidates[0]

        return min(
            valid,
            key=lambda c: abs(
                c.manufacture_year - requested_year
            ),
        )

    # ------------------------------------------------------------------
    # VALUATION
    # ------------------------------------------------------------------

    def _run_valuation(
        self,
        req: ValuationRequest,
        crsp: CRSPRecord,
    ) -> ValuationResultRow:

        condition_key = (
            (req.condition or "good")
            .strip()
            .lower()
        )

        accident_key = (
            (req.accident_history or "none")
            .strip()
            .lower()
        )

        condition = CONDITION_MAP.get(
            condition_key,
            condition_key.upper(),
        )

        accident = ACCIDENT_MAP.get(
            accident_key,
            accident_key.upper(),
        )

        vehicle_type = (
            (req.vehicle_type or "sedan")
            .strip()
            .upper()
        )

        location = (
            (req.location or "nairobi")
            .strip()
            .upper()
        )

        try:
            return self.repo.call_valuation_function(
                crsp_id=crsp.crsp_id,
                manufacture_year=int(req.year),
                mileage_km=float(req.mileage),
                vehicle_type=vehicle_type,
                condition_name=condition,
                accident_status=accident,
                location_name=location,
                profit_margin_percent=float(
                    req.profit_margin or 0
                ),
            )

        except RepositoryError as exc:
            raise ValuationEngineError(
                str(exc),
                status_code=502,
            ) from exc

    # ------------------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------------------

    def _to_response(
        self,
        row: ValuationResultRow,
        req: ValuationRequest,
        crsp: CRSPRecord,
    ) -> ValuationResponse:

        # The RPC returns "valuation_id", not "id". Prefer whichever
        # is actually populated so logging reflects the real row.
        result_id = row.valuation_id if row.valuation_id is not None else row.id

        logger.info(
            "Building valuation response: result_id=%s "
            "reference=%s final_value=%s",
            result_id,
            row.valuation_reference,
            row.final_market_value,
        )

        # --------------------------------------------------------------
        # Adjustment percentages
        #
        # The database stores adjustment amounts in KES.
        # We expose them as fractions of the post-depreciation base.
        # --------------------------------------------------------------

        base = (
            float(row.crsp_value or 0)
            - float(row.depreciation_value or 0)
        )

        if base <= 0:
            base = float(row.crsp_value or 0)

        def adjustment_fraction(
            amount: Optional[float],
        ) -> float:

            if amount is None or base <= 0:
                return 0.0

            return float(amount) / base

        depreciation_rate = None

        if row.depreciation_rate is not None:
            depreciation_rate = (
                float(row.depreciation_rate) / 100.0
            )

        report_number = (
            row.valuation_reference
            or f"AUTO-D-{uuid.uuid4().hex[:12].upper()}"
        )

        vehicle_age = row.vehicle_age

        if vehicle_age is None and row.manufacture_year:
            vehicle_age = max(
                0,
                2026 - int(row.manufacture_year),
            )

        return ValuationResponse(
            success=True,
            data=ValuationDataOut(

                vehicle=VehicleOut(
                    make=row.make or crsp.make or req.make,
                    model=row.model or crsp.model or req.model,
                    trim=(
                        crsp.trim_level
                        or req.trim
                    ),
                    year=(
                        row.manufacture_year
                        or req.year
                    ),
                    mileage=(
                        float(row.mileage_km)
                        if row.mileage_km is not None
                        else float(req.mileage)
                    ),
                    location=req.location,
                    condition=req.condition,
                    fuel_type=req.fuel_type,
                    transmission=req.transmission,
                    engine_capacity=req.engine_capacity,
                ),

                valuation=ValuationOut(
                    estimated_vehicle_value=(
                        row.final_market_value
                    ),
                    recommended_selling_price=(
                        row.recommended_selling_price
                    ),
                    confidence_score=(
                        row.confidence_score
                    ),
                ),

                analysis=AnalysisOut(
                    adjustments=AdjustmentsOut(
                        mileage=adjustment_fraction(
                            row.mileage_adjustment
                        ),
                        condition=adjustment_fraction(
                            row.condition_adjustment
                        ),
                        accident=adjustment_fraction(
                            row.accident_adjustment
                        ),
                        location=adjustment_fraction(
                            row.location_adjustment
                        ),
                        market=adjustment_fraction(
                            row.market_adjustment
                        ),
                    ),

                    depreciation_rate=depreciation_rate,

                    depreciation_amount=(
                        row.depreciation_value
                    ),

                    mileage_adjustment=(
                        adjustment_fraction(
                            row.mileage_adjustment
                        )
                    ),

                    vehicle_age=vehicle_age,
                ),

                report=ReportOut(
                    report_number=report_number
                ),

                crsp=CrspOut(
                    crsp_id=crsp.crsp_id,
                    crsp_value=row.crsp_value,
                    trim_level=crsp.trim_level,
                ),
            ),
        )


__all__ = [
    "ValuationEngine",
    "ValuationEngineError",
]
