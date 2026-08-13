"""
engine.py

The valuation "engine": orchestrates the repository and applies
business rules (CRSP match selection, enum normalization, adjustment
percentage derivation) to turn a `ValuationRequest` into a
`ValuationResponse`. This is the layer the router calls into — it's
the only place that should import both `schemas.py` and `models.py`.
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
    """Raised for any failure in the valuation pipeline; the router
    turns this into an HTTP error response."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ValuationEngine:
    def __init__(self, repository: ValuationRepository):
        self.repo = repository

    def calculate(self, req: ValuationRequest) -> ValuationResponse:
        crsp = self._select_crsp(req)
        row = self._run_valuation(req, crsp)
        return self._to_response(row, req, crsp)

    # ---- CRSP matching ---------------------------------------------------

    def _select_crsp(self, req: ValuationRequest) -> CRSPRecord:
        try:
            candidates = self.repo.find_crsp_candidates(req.make, req.model)
        except RepositoryError as exc:
            raise ValuationEngineError(str(exc), status_code=502) from exc

        if not candidates:
            raise ValuationEngineError(
                f"No CRSP schedule found for {req.make} {req.model}", status_code=404
            )

        def trim_matches(c: CRSPRecord) -> bool:
            return (c.trim_level or "").strip().lower() == req.trim.strip().lower()

        # Prefer exact trim + exact year
        exact = [c for c in candidates if trim_matches(c) and c.year == req.year]
        if exact:
            return exact[0]

        # Next best: exact trim, closest year in the schedule
        by_trim = [c for c in candidates if trim_matches(c)]
        pool = by_trim or candidates
        return min(pool, key=lambda c: abs((c.year or 0) - req.year))

    # ---- valuation call ---------------------------------------------------

    def _run_valuation(self, req: ValuationRequest, crsp: CRSPRecord) -> ValuationResultRow:
        try:
            return self.repo.call_valuation_function(
                crsp_id=crsp.crsp_id,
                manufacture_year=req.year,
                mileage_km=req.mileage,
                vehicle_type=req.vehicle_type.upper(),
                condition_name=CONDITION_MAP.get(req.condition, req.condition.upper()),
                accident_status=ACCIDENT_MAP.get(req.accident_history, req.accident_history.upper()),
                location_name=req.location.strip().upper(),
                profit_margin_percent=req.profit_margin,
            )
        except RepositoryError as exc:
            raise ValuationEngineError(str(exc), status_code=502) from exc

    # ---- response shaping ---------------------------------------------------

    def _to_response(
        self, row: ValuationResultRow, req: ValuationRequest, crsp: CRSPRecord
    ) -> ValuationResponse:
        base = row.value_after_depreciation or row.crsp_value

        def pct(amount: Optional[float]) -> float:
            if amount is None or not base:
                return 0.0
            return float(amount) / float(base)

        depreciation_rate_frac = (
            float(row.depreciation_rate) / 100.0 if row.depreciation_rate is not None else None
        )
        report_number = row.valuation_reference or f"AUTO-V-{uuid.uuid4().hex[:8].upper()}"

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
                report=ReportOut(report_number=report_number),
                crsp=CrspOut(
                    crsp_id=crsp.crsp_id,
                    crsp_value=row.crsp_value,
                    trim_level=crsp.trim_level,
                ),
            ),
        )
