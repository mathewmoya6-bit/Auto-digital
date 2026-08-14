engine.py

Valuation business-logic layer for Auto-D Kenya.

Responsibilities:
- Select the best CRSP record for the requested vehicle.
- Normalize frontend condition/accident values to database values.
- Call the valuation repository/RPC.
- Shape the database result into the stable public API response.

The engine does not perform direct database operations.
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
    """Raised when the valuation pipeline cannot complete."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ValuationEngine:
    """Orchestrates CRSP selection, valuation and response shaping."""

    def __init__(self, repository: ValuationRepository):
        self.repo = repository

    def calculate(self, req: ValuationRequest) -> ValuationResponse:
        """Calculate a valuation for the supplied request."""
        crsp = self._select_crsp(req)
        row = self._run_valuation(req, crsp)
        return self._to_response(row, req, crsp)

    # ------------------------------------------------------------------
    # CRSP selection
    # ------------------------------------------------------------------

    def _select_crsp(self, req: ValuationRequest) -> CRSPRecord:
        """Select the best available CRSP record."""

        try:
            candidates = self.repo.find_crsp_candidates(
                req.make,
                req.model,
            )
        except RepositoryError as exc:
            raise ValuationEngineError(
                str(exc),
                status_code=502,
            ) from exc

        if not candidates:
            raise ValuationEngineError(
                f"No CRSP schedule found for {req.make} {req.model}",
                status_code=404,
            )

        requested_trim = (req.trim or "").strip().lower()

        def trim_matches(candidate: CRSPRecord) -> bool:
            return (
                (candidate.trim_level or "").strip().lower()
                == requested_trim
            )

        # 1. Exact trim + exact year.
        exact = [
            candidate
            for candidate in candidates
            if trim_matches(candidate)
            and candidate.year == req.year
        ]

        if exact:
            return exact[0]

        # 2. Exact trim + closest available year.
        by_trim = [
            candidate
            for candidate in candidates
            if trim_matches(candidate)
            and candidate.year is not None
        ]

        if by_trim:
            return min(
                by_trim,
                key=lambda candidate: abs(candidate.year - req.year),
            )

        # 3. Any trim + closest available year.
        with_year = [
            candidate
            for candidate in candidates
            if candidate.year is not None
        ]

        if not with_year:
            raise ValuationEngineError(
                f"No year-specific CRSP schedule found for "
                f"{req.make} {req.model}",
                status_code=404,
            )

        return min(
            with_year,
            key=lambda candidate: abs(candidate.year - req.year),
        )

    # ------------------------------------------------------------------
    # Valuation RPC
    # ------------------------------------------------------------------

    def _run_valuation(
        self,
        req: ValuationRequest,
        crsp: CRSPRecord,
    ) -> ValuationResultRow:
        """Execute the database valuation function."""

        condition_name = CONDITION_MAP.get(
            (req.condition or "").strip().lower(),
            (req.condition or "good").strip().upper(),
        )

        accident_status = ACCIDENT_MAP.get(
            (req.accident_history or "").strip().lower(),
            (req.accident_history or "none").strip().upper(),
        )

        vehicle_type = (
            (req.vehicle_type or "sedan")
            .strip()
            .upper()
        )

        location_name = (
            (req.location or "nairobi")
            .strip()
            .upper()
        )

        try:
            return self.repo.call_valuation_function(
                crsp_id=int(crsp.crsp_id),
                manufacture_year=int(req.year),
                mileage_km=float(req.mileage),
                vehicle_type=vehicle_type,
                condition_name=condition_name,
                accident_status=accident_status,
                location_name=location_name,
                profit_margin_percent=float(req.profit_margin),
            )
        except RepositoryError as exc:
            raise ValuationEngineError(
                str(exc),
                status_code=502,
            ) from exc

    # ------------------------------------------------------------------
    # Response shaping
    # ------------------------------------------------------------------

    def _to_response(
        self,
        row: ValuationResultRow,
        req: ValuationRequest,
        crsp: CRSPRecord,
    ) -> ValuationResponse:
        """Convert the domain result into the stable API response."""

        base = row.value_after_depreciation or row.crsp_value

        def pct(amount: Optional[float]) -> float:
            if amount is None or not base:
                return 0.0
            return float(amount) / float(base)

        depreciation_rate_frac = (
            float(row.depreciation_rate) / 100.0
            if row.depreciation_rate is not None
            else None
        )

        report_number = (
            row.valuation_reference
            or f"AUTO-D-{uuid.uuid4().hex[:8].upper()}"
        )

        return ValuationResponse(
            success=True,
            data=ValuationDataOut(
                vehicle=VehicleOut(
                    make=row.make or req.make,
                    model=row.model or req.model,
                    trim=req.trim,
                    year=row.manufacture_year or req.year,
                    mileage=req.mileage,
                    location=req.location,
                    condition=req.condition,
                    fuel_type=req.fuel_type,
                    transmission=req.transmission,
                    engine_capacity=req.engine_capacity,
                ),
                valuation=ValuationOut(
                    estimated_vehicle_value=row.final_market_value,
                    recommended_selling_price=row.recommended_selling_price,
                    confidence_score=row.confidence_score,
                ),
                analysis=AnalysisOut(
                    adjustments=AdjustmentsOut(
                        mileage=pct(row.mileage_adjustment),
                        condition=pct(row.condition_adjustment),
                        accident=pct(row.accident_adjustment),
                        location=pct(row.location_adjustment),
                        market=pct(row.market_adjustment),
                    ),
                    depreciation_rate=depreciation_rate_frac,
                    depreciation_amount=row.depreciation_value,
                    mileage_adjustment=pct(row.mileage_adjustment),
                    vehicle_age=row.vehicle_age,
                ),
                report=ReportOut(
                    report_number=report_number,
                ),
                crsp=CrspOut(
                    crsp_id=crsp.crsp_id,
                    crsp_value=row.crsp_value,
                    trim_level=crsp.trim_level,
                ),
            ),
        )
