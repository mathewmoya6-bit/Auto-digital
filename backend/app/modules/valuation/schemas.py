# app/modules/valuation/schemas.py

# ================================================================
# Auto-D Kenya - Valuation Schemas
# ================================================================

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ================================================================
# VALUATION REQUEST
# ================================================================

class ValuationRequest(BaseModel):
    """Request payload for vehicle valuation."""

    crsp_id: int = Field(
        ...,
        description="Authoritative vehicle CRSP ID"
    )

    year: int = Field(
        ...,
        ge=1900,
        le=2100,
        description="Vehicle manufacture year"
    )

    mileage: int = Field(
        0,
        ge=0,
        description="Vehicle mileage in KM"
    )

    condition: str = Field(
        "good",
        description="Vehicle condition"
    )

    accident_history: str = Field(
        "none",
        description="Accident history"
    )

    location: str = Field(
        "nairobi",
        description="Vehicle location"
    )

    service_history: bool = Field(
        False,
        description="Whether service history is available"
    )

    ownership_count: int = Field(
        1,
        ge=1,
        description="Number of previous owners"
    )


# ================================================================
# ADJUSTMENT
# ================================================================

class ValuationAdjustment(BaseModel):
    """Individual valuation adjustment."""

    factor: str
    adjustment: float
    percentage: float
    reason: str
    factor_value: float


# ================================================================
# DEPRECIATION
# ================================================================

class DepreciationResult(BaseModel):
    """Vehicle depreciation calculation."""

    original_value: float
    current_value: float
    depreciation_amount: float
    depreciation_percentage: float
    annual_rate: float
    age: int


# ================================================================
# VEHICLE DETAILS
# ================================================================

class ValuationVehicle(BaseModel):
    """Authoritative vehicle information from vehicle_crsp_lookup."""

    crsp_id: int

    make: Optional[str] = None
    make_id: Optional[int] = None

    model: Optional[str] = None
    normalized_model: Optional[str] = None

    model_id: Optional[int] = None

    master_model_id: Optional[int] = None
    master_model_name: Optional[str] = None

    generation_id: Optional[int] = None

    engine_capacity_id: Optional[int] = None
    engine_capacity: Optional[str] = None

    fuel: Optional[str] = None
    transmission: Optional[str] = None
    drive_configuration: Optional[str] = None
    body_type: Optional[str] = None

    manufacture_year: Optional[int] = None
    crsp_year: Optional[int] = None

    crsp_kes: Optional[float] = None

    currency: str = "KES"

    effective_date: Optional[str] = None

    is_inferred: bool = False
    is_duplicate: bool = False


# ================================================================
# COMPARABLE VEHICLE
# ================================================================

class ValuationComparable(BaseModel):
    """Comparable market vehicle."""

    id: Optional[int] = None

    make: Optional[str] = None
    model: Optional[str] = None
    variant: Optional[str] = None

    year: Optional[int] = None
    mileage: Optional[int] = None

    price: float

    source: Optional[str] = None
    location: Optional[str] = None
    date: Optional[str] = None
    url: Optional[str] = None

    difference: Optional[float] = None
    similarity_score: Optional[float] = None


# ================================================================
# VALUATION RESPONSE
# ================================================================

class ValuationResponse(BaseModel):
    """Complete vehicle valuation response."""

    vehicle: ValuationVehicle

    # ------------------------------------------------------------
    # Primary valuation
    # ------------------------------------------------------------

    market_value: float

    # ------------------------------------------------------------
    # Market bands
    # ------------------------------------------------------------

    retail_value: float
    trade_value: float
    dealer_value: float

    recommended_selling_price: Optional[float] = None

    # ------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------

    confidence_score: float = Field(
        ...,
        ge=0,
        le=100
    )

    # ------------------------------------------------------------
    # Depreciation
    # ------------------------------------------------------------

    depreciation: Optional[DepreciationResult] = None

    # ------------------------------------------------------------
    # Adjustments
    # ------------------------------------------------------------

    adjustments: List[ValuationAdjustment] = Field(
        default_factory=list
    )

    # ------------------------------------------------------------
    # Market information
    # ------------------------------------------------------------

    sample_size: int = 0

    market_trend: str = "Stable"

    comparables: List[ValuationComparable] = Field(
        default_factory=list
    )

    # ------------------------------------------------------------
    # Explanation
    # ------------------------------------------------------------

    recommendation: Optional[str] = None

    warnings: List[str] = Field(
        default_factory=list
    )

    # ------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------

    currency: str = "KES"

    calculated_at: datetime = Field(
        default_factory=datetime.utcnow
    )


# ================================================================
# COMPACT SUMMARY
# ================================================================

class ValuationSummary(BaseModel):
    """Compact valuation summary."""

    crsp_id: int

    market_value: float
    retail_value: float
    trade_value: float

    confidence_score: float

    currency: str = "KES"

    calculated_at: datetime = Field(
        default_factory=datetime.utcnow
    )


# ================================================================
# REPORT RESPONSE
# ================================================================

class ValuationReportResponse(ValuationResponse):
    """
    Full valuation report response.

    Kept as a separate response type so existing router/report
    endpoints can continue importing ValuationReportResponse.
    """

    pass
