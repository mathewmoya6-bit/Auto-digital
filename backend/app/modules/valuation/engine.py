"""
Auto-D Kenya - Valuation Engine

Responsibilities:
1. Validate the valuation request.
2. Resolve CRSP from vehicle_crsp.
3. Resolve missing make from model when necessary.
4. Select the best CRSP row for the requested trim/year.
5. Call calculate_vehicle_valuation().
6. Convert the database result into the stable API response.

IMPORTANT:
- vehicle_crsp is the authoritative CRSP source.
- calculate_vehicle_valuation() is the authoritative valuation calculation.
- This module contains business/orchestration logic only.
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


# =====================================================================
# ENUM NORMALIZATION
# =====================================================================

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


# =====================================================================
# ERROR
# =====================================================================

class ValuationEngineError(Exception):
    """
    Business/application error raised by the valuation engine.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 400,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# =====================================================================
# ENGINE
# =====================================================================

class ValuationEngine:

    def __init__(
        self,
        repository: ValuationRepository,
    ):
        self.repo = repository

    # =================================================================
    # PUBLIC ENTRY POINT
    # =================================================================

    def calculate(
        self,
        req: ValuationRequest,
    ) -> ValuationResponse:

        make = self._clean(req.make)
        model = self._clean(req.model)
        trim = self._clean(req.trim)

        logger.info(
            "Valuation request: make=%r model=%r trim=%r "
            "year=%r mileage=%r",
            make,
            model,
            trim,
            req.year,
            req.mileage,
        )

        # -------------------------------------------------------------
        # MODEL IS REQUIRED
        # -------------------------------------------------------------

        if not model:
            raise ValuationEngineError(
                "Vehicle model is required for valuation",
                status_code=422,
            )

        # -------------------------------------------------------------
        # RESOLVE CRSP
        #
        # IMPORTANT:
        # If make is empty, DO NOT call find_crsp_candidates().
        # That method requires both make and model.
        #
        # Instead search vehicle_crsp by model and derive the make.
        # -------------------------------------------------------------

        if not make:

            logger.info(
                "Make missing. Resolving make from CRSP using model=%r",
                model,
            )

            crsp = self._resolve_crsp_without_make(
                model=model,
                trim=trim,
                year=req.year,
            )

            make = self._clean(crsp.make)

            if not make:
                raise ValuationEngineError(
                    f"CRSP record for {model} has no make",
                    status_code=422,
                )

            logger.info(
                "Make resolved from CRSP: make=%r model=%r "
                "crsp_id=%s trim=%r year=%r",
                make,
                crsp.model,
                crsp.crsp_id,
                crsp.trim_level,
                crsp.manufacture_year,
            )

        else:

            crsp = self._resolve_crsp(
                make=make,
                model=model,
                trim=trim,
                year=req.year,
            )

        # -------------------------------------------------------------
        # RUN AUTHORITATIVE SQL VALUATION
        # -------------------------------------------------------------

        row = self._run_valuation(
            req=req,
            crsp=crsp,
        )

        # -------------------------------------------------------------
        # BUILD API RESPONSE
        # -------------------------------------------------------------

        return self._to_response(
            row=row,
            req=req,
            crsp=crsp,
            resolved_make=make,
            resolved_model=model,
        )

    # =================================================================
    # HELPERS
    # =================================================================

    @staticmethod
    def _clean(value: Optional[str]) -> str:
        """
        Safely normalize strings.

        None      -> ""
        ""        -> ""
        "  ABC "  -> "ABC"
        """
        if value is None:
            return ""

        return str(value).strip()

    # =================================================================
    # CRSP RESOLUTION - MAKE + MODEL
    # =================================================================

    def _resolve_crsp(
        self,
        *,
        make: str,
        model: str,
        trim: str,
        year: int,
    ) -> CRSPRecord:

        logger.info(
            "CRSP lookup: make=%r model=%r trim=%r year=%r",
            make,
            model,
            trim,
            year,
        )

        try:
            candidates = self.repo.find_crsp_candidates(
                make=make,
                model=model,
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

        return self._select_best_crsp(
            candidates=candidates,
            trim=trim,
            year=year,
        )

    # =================================================================
    # CRSP RESOLUTION - MODEL ONLY
    # =================================================================

    def _resolve_crsp_without_make(
        self,
        *,
        model: str,
        trim: str,
        year: int,
    ) -> CRSPRecord:

        logger.info(
            "CRSP model-only lookup: model=%r trim=%r year=%r",
            model,
            trim,
            year,
        )

        try:
            candidates = self.repo.find_crsp_by_model(
                model=model,
            )

        except RepositoryError as exc:
            raise ValuationEngineError(
                str(exc),
                status_code=502,
            ) from exc

        if not candidates:
            raise ValuationEngineError(
                f"No CRSP schedule found for model {model}",
                status_code=404,
            )

        # -------------------------------------------------------------
        # Make sure we don't accidentally combine unrelated makes.
        # -------------------------------------------------------------

        makes = {
            self._clean(c.make).upper()
            for c in candidates
            if self._clean(c.make)
        }

        logger.info(
            "Model-only CRSP lookup found makes=%s",
            sorted(makes),
        )

        if len(makes) > 1:
            # If multiple makes have the exact same model name,
            # use trim/year to narrow the selection.
            selected = self._select_best_crsp(
                candidates=candidates,
                trim=trim,
                year=year,
            )

            if not selected.make:
                raise ValuationEngineError(
                    f"Unable to determine make for {model}",
                    status_code=422,
                )

            return selected

        return self._select_best_crsp(
            candidates=candidates,
            trim=trim,
            year=year,
        )

    # =================================================================
    # BEST CRSP MATCH
    # =================================================================

    def _select_best_crsp(
        self,
        *,
        candidates: list[CRSPRecord],
        trim: str,
        year: int,
    ) -> CRSPRecord:

        if not candidates:
            raise ValuationEngineError(
                "No CRSP candidates available",
                status_code=404,
            )

        requested_trim = self._clean(trim).casefold()

        # -------------------------------------------------------------
        # 1. Exact trim + exact year
        # -------------------------------------------------------------

        exact_trim_year = [
            c
            for c in candidates
            if self._clean(c.trim_level).casefold()
            == requested_trim
            and c.manufacture_year == year
        ]

        if exact_trim_year:
            selected = exact_trim_year[0]

            logger.info(
                "CRSP selected: exact trim + year "
                "crsp_id=%s make=%r model=%r trim=%r year=%r",
                selected.crsp_id,
                selected.make,
                selected.model,
                selected.trim_level,
                selected.manufacture_year,
            )

            return selected

        # -------------------------------------------------------------
        # 2. Exact trim
        # -------------------------------------------------------------

        exact_trim = [
            c
            for c in candidates
            if self._clean(c.trim_level).casefold()
            == requested_trim
        ]

        if exact_trim:
            year_candidates = [
                c
                for c in exact_trim
                if c.manufacture_year is not None
            ]

            if year_candidates:
                selected = min(
                    year_candidates,
                    key=lambda c: abs(
                        c.manufacture_year - year
                    ),
                )
            else:
                selected = exact_trim[0]

            logger.info(
                "CRSP selected: exact trim / closest year "
                "crsp_id=%s year=%r requested_year=%r",
                selected.crsp_id,
                selected.manufacture_year,
                year,
            )

            return selected

        # -------------------------------------------------------------
        # 3. Closest year regardless of trim
        # -------------------------------------------------------------

        year_candidates = [
            c
            for c in candidates
            if c.manufacture_year is not None
        ]

        if year_candidates:
            selected = min(
                year_candidates,
                key=lambda c: abs(
                    c.manufacture_year - year
                ),
            )

            logger.info(
                "CRSP selected: closest year "
                "crsp_id=%s year=%r requested_year=%r",
                selected.crsp_id,
                selected.manufacture_year,
                year,
            )

            return selected

        # -------------------------------------------------------------
        # 4. Last resort
        # -------------------------------------------------------------

        selected = candidates[0]

        logger.info(
            "CRSP selected: fallback first candidate "
            "crsp_id=%s",
            selected.crsp_id,
        )

        return selected

    # =================================================================
    # SQL VALUATION
    # =================================================================

    def _run_valuation(
        self,
        *,
        req: ValuationRequest,
        crsp: CRSPRecord,
    ) -> ValuationResultRow:

        if crsp.crsp_id is None:
            raise ValuationEngineError(
                "Selected CRSP record has no crsp_id",
                status_code=422,
            )

        condition = CONDITION_MAP.get(
            self._clean(req.condition).casefold(),
            self._clean(req.condition).upper(),
        )

        accident = ACCIDENT_MAP.get(
            self._clean(req.accident_history).casefold(),
            self._clean(req.accident_history).upper(),
        )

        vehicle_type = (
            self._clean(req.vehicle_type).upper()
            or "SEDAN"
        )

        location = (
            self._clean(req.location).upper()
            or "NAIROBI"
        )

        logger.info(
            "Running valuation RPC: "
            "crsp_id=%s year=%s mileage=%s "
            "vehicle_type=%s condition=%s accident=%s "
            "location=%s profit_margin=%s",
            crsp.crsp_id,
            req.year,
            req.mileage,
            vehicle_type,
            condition,
            accident,
            location,
            req.profit_margin,
        )

        try:
            return self.repo.call_valuation_function(
                crsp_id=int(crsp.crsp_id),
                manufacture_year=int(req.year),

                # PostgreSQL function expects INTEGER.
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

    # =================================================================
    # RESPONSE
    # =================================================================

    def _to_response(
        self,
        *,
        row: ValuationResultRow,
        req: ValuationRequest,
        crsp: CRSPRecord,
        resolved_make: str,
        resolved_model: str,
    ) -> ValuationResponse:

        base = (
            row.value_after_depreciation
            if row.value_after_depreciation is not None
            else row.crsp_value
        )

        def pct(
            amount: Optional[float],
        ) -> float:

            if amount is None:
                return 0.0

            if base is None:
                return 0.0

            if float(base) == 0:
                return 0.0

            return float(amount) / float(base)

        # Database stores depreciation_rate as percentage:
        #
        # 60.0000
        #
        # API contract expects fraction:
        #
        # 0.60
        #

        depreciation_rate = None

        if row.depreciation_rate is not None:
            depreciation_rate = (
                float(row.depreciation_rate) / 100.0
            )

        report_number = (
            row.valuation_reference
            or f"AUTO-D-{uuid.uuid4().hex[:12].upper()}"
        )

        return ValuationResponse(
            success=True,
            data=ValuationDataOut(

                # -----------------------------------------------------
                # VEHICLE
                # -----------------------------------------------------

                vehicle=VehicleOut(
                    make=(
                        row.make
                        or resolved_make
                        or req.make
                    ),

                    model=(
                        row.model
                        or resolved_model
                        or req.model
                    ),

                    trim=(
                        req.trim
                        or crsp.trim_level
                    ),

                    year=(
                        row.manufacture_year
                        or req.year
                    ),

                    mileage=req.mileage,

                    location=req.location,

                    condition=req.condition,

                    fuel_type=req.fuel_type,

                    transmission=req.transmission,

                    engine_capacity=req.engine_capacity,
                ),

                # -----------------------------------------------------
                # VALUATION
                # -----------------------------------------------------

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

                # -----------------------------------------------------
                # ANALYSIS
                # -----------------------------------------------------

                analysis=AnalysisOut(

                    adjustments=AdjustmentsOut(

                        mileage=pct(
                            row.mileage_adjustment
                        ),

                        condition=pct(
                            row.condition_adjustment
                        ),

                        accident=pct(
                            row.accident_adjustment
                        ),

                        location=pct(
                            row.location_adjustment
                        ),

                        market=pct(
                            row.market_adjustment
                        ),
                    ),

                    depreciation_rate=(
                        depreciation_rate
                    ),

                    depreciation_amount=(
                        row.depreciation_value
                    ),

                    mileage_adjustment=pct(
                        row.mileage_adjustment
                    ),

                    vehicle_age=(
                        row.vehicle_age
                    ),
                ),

                # -----------------------------------------------------
                # REPORT
                # -----------------------------------------------------

                report=ReportOut(
                    report_number=report_number
                ),

                # -----------------------------------------------------
                # CRSP
                # -----------------------------------------------------

                crsp=CrspOut(
                    crsp_id=crsp.crsp_id,

                    crsp_value=(
                        row.crsp_value
                        if row.crsp_value is not None
                        else crsp.crsp_kes
                    ),

                    trim_level=(
                        crsp.trim_level
                    ),
                ),
            ),
        )
