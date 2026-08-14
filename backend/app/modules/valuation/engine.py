"""
engine.py

Business layer for Auto-D Kenya vehicle valuation.

Flow:

    ValuationRequest
        ↓
    CRSP selection
        ↓
    calculate_vehicle_valuation()
        ↓
    Stable ValuationResponse
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
    "good": "GOOD",
    "fair": "FAIR",
    "poor": "POOR",
}


ACCIDENT_MAP = {
    "none": "NONE",
    "minor": "MINOR",
    "major": "MAJOR",
    "total_loss": "TOTAL_LOSS",
}


class ValuationEngineError(Exception):
    """Expected valuation failure mapped to an HTTP status."""

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
    # MAIN CALCULATION
    # ------------------------------------------------------------------

    def calculate(
        self,
        req: ValuationRequest,
    ) -> ValuationResponse:

        make = (req.make or "").strip()
        model = (req.model or "").strip()
        trim = (req.trim or "").strip()

        logger.info(
            "Valuation request: "
            "make=%r model=%r trim=%r year=%r mileage=%r",
            make,
            model,
            trim,
            req.year,
            req.mileage,
        )

        if not make or not model:
            raise ValuationEngineError(
                "Make and model are required for valuation",
                status_code=422,
            )

        crsp = self._select_crsp(
            req=req,
            make=make,
            model=model,
            trim=trim,
        )

        row = self._run_valuation(
            req=req,
            crsp=crsp,
        )

        return self._to_response(
            row=row,
            req=req,
            crsp=crsp,
        )

    # ------------------------------------------------------------------
    # CRSP SELECTION
    # ------------------------------------------------------------------

    def _select_crsp(
        self,
        *,
        req: ValuationRequest,
        make: str,
        model: str,
        trim: str,
    ) -> CRSPRecord:

        try:
            candidates = (
                self.repo.find_crsp_candidates(
                    make=make,
                    model=model,
                )
            )

        except RepositoryError as exc:
            raise ValuationEngineError(
                str(exc),
                status_code=502,
            ) from exc

        if not candidates:
            raise ValuationEngineError(
                f"No CRSP schedule found for "
                f"{make} {model}",
                status_code=404,
            )

        logger.info(
            "CRSP candidates found: %d for %s %s",
            len(candidates),
            make,
            model,
        )

        # --------------------------------------------------------------
        # 1. Exact trim
        # --------------------------------------------------------------

        trim_candidates = [
            candidate
            for candidate in candidates
            if (
                (candidate.trim_level or "")
                .strip()
                .casefold()
                == trim.casefold()
            )
        ]

        pool = (
            trim_candidates
            if trim_candidates
            else candidates
        )

        # --------------------------------------------------------------
        # 2. Exact manufacture year
        # --------------------------------------------------------------

        exact_year = [
            candidate
            for candidate in pool
            if candidate.manufacture_year == req.year
        ]

        if exact_year:
            selected = exact_year[0]

        else:
            # ----------------------------------------------------------
            # 3. Closest available year
            # ----------------------------------------------------------

            year_candidates = [
                candidate
                for candidate in pool
                if candidate.manufacture_year is not None
            ]

            if year_candidates:
                selected = min(
                    year_candidates,
                    key=lambda candidate: abs(
                        int(candidate.manufacture_year)
                        - int(req.year)
                    ),
                )

            else:
                # Some CRSP schedules may have no year stored.
                # In that case use the first valid schedule.
                selected = pool[0]

        logger.info(
            "Selected CRSP: "
            "id=%s make=%r model=%r trim=%r "
            "manufacture_year=%r crsp_kes=%r",
            selected.crsp_id,
            selected.make,
            selected.model,
            selected.trim_level,
            selected.manufacture_year,
            selected.crsp_kes,
        )

        return selected

    # ------------------------------------------------------------------
    # SQL VALUATION
    # ------------------------------------------------------------------

    def _run_valuation(
        self,
        *,
        req: ValuationRequest,
        crsp: CRSPRecord,
    ) -> ValuationResultRow:

        condition = CONDITION_MAP.get(
            (req.condition or "").strip().lower(),
            (req.condition or "GOOD")
            .strip()
            .upper(),
        )

        accident = ACCIDENT_MAP.get(
            (req.accident_history or "")
            .strip()
            .lower(),
            (req.accident_history or "NONE")
            .strip()
            .upper(),
        )

        vehicle_type = (
            (req.vehicle_type or "SEDAN")
            .strip()
            .upper()
        )

        location = (
            (req.location or "NAIROBI")
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
                    req.profit_margin
                ),
            )

        except RepositoryError as exc:
            raise ValuationEngineError(
                str(exc),
                status_code=502,
            ) from exc

    # ------------------------------------------------------------------
    # ADJUSTMENT HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _ratio(
        amount: Optional[float],
        base: Optional[float],
    ) -> float:

        if (
            amount is None
            or base is None
            or float(base) == 0
        ):
            return 0.0

        return float(amount) / float(base)

    # ------------------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------------------

    def _to_response(
        self,
        *,
        row: ValuationResultRow,
        req: ValuationRequest,
        crsp: CRSPRecord,
    ) -> ValuationResponse:

        base = (
            row.value_after_depreciation
            if row.value_after_depreciation is not None
            else row.crsp_value
        )

        depreciation_rate = (
            float(row.depreciation_rate) / 100.0
            if row.depreciation_rate is not None
            else None
        )

        report_number = (
            row.valuation_reference
            or (
                f"AUTO-D-"
                f"{uuid.uuid4().hex[:12].upper()}"
            )
        )

        return ValuationResponse(
            success=True,

            data=ValuationDataOut(

                vehicle=VehicleOut(
                    make=row.make or req.make,
                    model=row.model or req.model,
                    trim=req.trim,

                    year=(
                        row.manufacture_year
                        if row.manufacture_year is not None
                        else req.year
                    ),

                    mileage=req.mileage,
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
                        mileage=self._ratio(
                            row.mileage_adjustment,
                            base,
                        ),

                        condition=self._ratio(
                            row.condition_adjustment,
                            base,
                        ),

                        accident=self._ratio(
                            row.accident_adjustment,
                            base,
                        ),

                        location=self._ratio(
                            row.location_adjustment,
                            base,
                        ),

                        market=self._ratio(
                            row.market_adjustment,
                            base,
                        ),
                    ),

                    depreciation_rate=(
                        depreciation_rate
                    ),

                    depreciation_amount=(
                        row.depreciation_value
                    ),

                    mileage_adjustment=self._ratio(
                        row.mileage_adjustment,
                        base,
                    ),

                    vehicle_age=row.vehicle_age,
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
