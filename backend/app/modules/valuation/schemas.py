"""
schemas.py

Pydantic request/response contracts for the valuation API. Kept
deliberately separate from `models.py` (internal, DB-shaped objects)
so the public API response shape — the one the "Instant Value Check"
frontend's showValuationResult() parses — can stay stable even if
column names change in Postgres.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────────
# Request
# ─────────────────────────────────────────────────────────────────

class ValuationRequest(BaseModel):
    """Matches the `formData` payload built by the frontend's
    App.calculateValuation()."""

    make: str
    model: str
    trim: str
    year: int
    mileage: float = Field(ge=0)
    condition: str = "good"
    accident_history: str = "none"
    previous_owners: int = 1
    location: str = "nairobi"
    fuel_type: str = "petrol"
    transmission: str = "automatic"
    vehicle_type: str = "sedan"
    profit_margin: float = Field(default=0, ge=0, le=100)
    engine_capacity: Optional[str] = None
    crsp_kes: Optional[float] = None  # informational only; resolved server-side via CRSP lookup

    @field_validator("make", "model", "trim", "location", "condition", "accident_history")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


# ─────────────────────────────────────────────────────────────────
# Response
# ─────────────────────────────────────────────────────────────────

class VehicleOut(BaseModel):
    make: str
    model: str
    trim: Optional[str] = None
    year: Optional[int] = None
    mileage: Optional[float] = None
    location: Optional[str] = None
    condition: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    engine_capacity: Optional[str] = None


class ValuationOut(BaseModel):
    estimated_vehicle_value: Optional[float] = None
    recommended_selling_price: Optional[float] = None
    confidence_score: Optional[float] = None


class AdjustmentsOut(BaseModel):
    mileage: float = 0.0
    condition: float = 0.0
    accident: float = 0.0
    location: float = 0.0
    market: float = 0.0


class AnalysisOut(BaseModel):
    adjustments: AdjustmentsOut
    depreciation_rate: Optional[float] = None       # fraction, e.g. 0.60 for 60%
    depreciation_amount: Optional[float] = None
    mileage_adjustment: Optional[float] = None       # fraction of base value
    vehicle_age: Optional[int] = None


class ReportOut(BaseModel):
    report_number: str


class CrspOut(BaseModel):
    crsp_id: Optional[int] = None
    crsp_value: Optional[float] = None
    trim_level: Optional[str] = None


class ValuationDataOut(BaseModel):
    vehicle: VehicleOut
    valuation: ValuationOut
    analysis: AnalysisOut
    report: ReportOut
    crsp: CrspOut


class ValuationResponse(BaseModel):
    success: bool = True
    data: ValuationDataOut
