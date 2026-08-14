"""
schemas.py

Public request/response contracts for the Auto-D Kenya valuation API.

The request model is deliberately tolerant of common frontend naming
variations while exposing the stable API contract to the engine.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ======================================================================
# REQUEST
# ======================================================================

class ValuationRequest(BaseModel):
    """
    Request received by POST /api/v1/valuation/calculate.
    """

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
    )

    make: str = ""
    model: str = ""
    trim: str = "Base"

    year: int = Field(default=2020, ge=1900, le=2100)

    mileage: float = Field(
        default=0,
        ge=0,
    )

    condition: str = "good"

    accident_history: str = "none"

    previous_owners: int = Field(
        default=1,
        ge=0,
    )

    location: str = "nairobi"

    fuel_type: str = "petrol"

    transmission: str = "automatic"

    vehicle_type: str = "sedan"

    profit_margin: float = Field(
        default=0,
        ge=0,
        le=100,
    )

    engine_capacity: Optional[str] = None

    # Informational only.
    # Server resolves the authoritative CRSP value.
    crsp_kes: Optional[float] = None

    # ------------------------------------------------------------------
    # STRING NORMALIZATION
    # ------------------------------------------------------------------

    @field_validator(
        "make",
        "model",
        "trim",
        "condition",
        "accident_history",
        "location",
        "fuel_type",
        "transmission",
        "vehicle_type",
        mode="before",
    )
    @classmethod
    def normalize_strings(cls, value: Any) -> str:
        if value is None:
            return ""

        return str(value).strip()

    # ------------------------------------------------------------------
    # NUMERIC NORMALIZATION
    # ------------------------------------------------------------------

    @field_validator(
        "mileage",
        "profit_margin",
        "crsp_kes",
        mode="before",
    )
    @classmethod
    def normalize_numbers(cls, value: Any):
        if value is None or value == "":
            return None if value is None else 0

        return float(value)


# ======================================================================
# RESPONSE
# ======================================================================

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

    # Fraction:
    # 0.60 = 60%
    depreciation_rate: Optional[float] = None

    depreciation_amount: Optional[float] = None

    # Fraction of base value
    mileage_adjustment: Optional[float] = None

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
