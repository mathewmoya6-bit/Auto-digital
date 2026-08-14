"""
app/modules/valuation/schemas.py

Public Pydantic request/response contracts for the valuation API.

This file defines the stable API shape consumed by the frontend.
It is intentionally separate from models.py, which represents
internal/database-shaped valuation objects.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# =====================================================================
# REQUEST
# =====================================================================

class ValuationRequest(BaseModel):
    """
    Request payload sent by the Instant Value Check frontend.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True
    )

    make: str = Field(
        ...,
        min_length=1,
        description="Vehicle make",
    )

    model: str = Field(
        ...,
        min_length=1,
        description="Vehicle model",
    )

    trim: str = Field(
        default="Base",
        min_length=1,
        description="Vehicle trim level",
    )

    year: int = Field(
        ...,
        ge=1900,
        le=2100,
        description="Vehicle manufacture year",
    )

    mileage: float = Field(
        ...,
        ge=0,
        description="Vehicle mileage in kilometres",
    )

    condition: str = Field(
        default="good",
        min_length=1,
    )

    accident_history: str = Field(
        default="none",
        min_length=1,
    )

    previous_owners: int = Field(
        default=1,
        ge=0,
    )

    location: str = Field(
        default="nairobi",
        min_length=1,
    )

    fuel_type: str = Field(
        default="petrol",
        min_length=1,
    )

    transmission: str = Field(
        default="automatic",
        min_length=1,
    )

    vehicle_type: str = Field(
        default="sedan",
        min_length=1,
    )

    profit_margin: float = Field(
        default=0.0,
        ge=0,
        le=100,
    )

    engine_capacity: Optional[str] = None

    # Informational only.
    # Server always resolves the authoritative CRSP value.
    crsp_kes: Optional[float] = Field(
        default=None,
        ge=0,
    )

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
    )
    @classmethod
    def normalize_strings(cls, value: str) -> str:
        """
        Normalize incoming strings without changing their meaning.
        """
        return value.strip()

    @field_validator("make", "model")
    @classmethod
    def require_make_and_model(cls, value: str) -> str:
        """
        Prevent blank make/model values from reaching the repository.
        """
        if not value:
            raise ValueError(
                "Make and model are required for valuation"
            )

        return value


# =====================================================================
# VEHICLE RESPONSE
# =====================================================================

class VehicleOut(BaseModel):
    """
    Vehicle information returned to the frontend.
    """

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


# =====================================================================
# VALUATION RESPONSE
# =====================================================================

class ValuationOut(BaseModel):
    """
    Main valuation figures.
    """

    estimated_vehicle_value: Optional[float] = None

    recommended_selling_price: Optional[float] = None

    confidence_score: Optional[float] = None


# =====================================================================
# ADJUSTMENTS
# =====================================================================

class AdjustmentsOut(BaseModel):
    """
    Valuation adjustment fractions.

    Example:
        0.05 = 5%
        -0.10 = -10%

    These are derived from the KES adjustment values stored by
    vehicle_valuation_results.
    """

    mileage: float = 0.0
    condition: float = 0.0
    accident: float = 0.0
    location: float = 0.0
    market: float = 0.0


# =====================================================================
# ANALYSIS
# =====================================================================

class AnalysisOut(BaseModel):
    """
    Supporting valuation analysis.
    """

    adjustments: AdjustmentsOut

    # Fraction:
    # 0.60 = 60%
    depreciation_rate: Optional[float] = None

    depreciation_amount: Optional[float] = None

    # Fraction of valuation base.
    mileage_adjustment: Optional[float] = None

    vehicle_age: Optional[int] = None


# =====================================================================
# REPORT
# =====================================================================

class ReportOut(BaseModel):
    """
    Valuation report reference.
    """

    report_number: str


# =====================================================================
# CRSP
# =====================================================================

class CrspOut(BaseModel):
    """
    CRSP information used for the valuation.
    """

    crsp_id: Optional[int] = None

    crsp_value: Optional[float] = None

    trim_level: Optional[str] = None


# =====================================================================
# COMPLETE DATA
# =====================================================================

class ValuationDataOut(BaseModel):
    """
    Complete valuation payload returned under `data`.
    """

    vehicle: VehicleOut

    valuation: ValuationOut

    analysis: AnalysisOut

    report: ReportOut

    crsp: CrspOut


# =====================================================================
# TOP-LEVEL RESPONSE
# =====================================================================

class ValuationResponse(BaseModel):
    """
    Stable public API response.

    Frontend can continue using:

        response.data.vehicle
        response.data.valuation
        response.data.analysis
        response.data.report
        response.data.crsp
    """

    success: bool = True

    data: ValuationDataOut


__all__ = [
    "ValuationRequest",
    "VehicleOut",
    "ValuationOut",
    "AdjustmentsOut",
    "AnalysisOut",
    "ReportOut",
    "CrspOut",
    "ValuationDataOut",
    "ValuationResponse",
]
