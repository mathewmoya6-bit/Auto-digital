# app/modules/valuation/schemas.py

# ================================================================
# Auto-D Kenya - Valuation Schemas
# ================================================================

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ================================================================
# VALUATION REQUEST
# ================================================================

class ValuationRequest(BaseModel):
    """Request payload for vehicle valuation."""

    variant_id: int = Field(..., description="Vehicle variant ID")
    year: int = Field(..., ge=1900, le=2100, description="Manufacture year")
    mileage: int = Field(0, ge=0, description="Vehicle mileage in KM")

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

    fuel_type: Optional[str] = Field(
        None,
        description="Fuel type"
    )

    transmission: Optional[str] = Field(
        None,
        description="Transmission type"
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
    """Vehicle information used during valuation."""

    variant_id: int
    make: str
    model: str
    variant: str

    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    engine_size: Optional[float] = None
    body_type: Optional[str] = None

    seats: Optional[int] = None
    doors: Optional[int] = None
    drive_type: Optional[str] = None


# ================================================================
# COMPARABLE VEHICLE
# ================================================================

class ValuationComparable(BaseModel):
    """Comparable market vehicle."""

    id: Optional[int] = None

    make: str
    model: str

    variant: Optional[str] = None
    year: int
    mileage: int

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

    market_value: float
    retail_value: float
    trade_value: float
    dealer_value: float

    confidence_score: float = Field(
        ...,
        ge=0,
        le=100
    )

    depreciation: DepreciationResult

    adjustments: List[ValuationAdjustment] = Field(
        default_factory=list
    )

    sample_size: int = 0

    market_trend: str = "Stable"

    comparables: List[ValuationComparable] = Field(
        default_factory=list
    )

    recommendation: str

    currency: str = "KES"

    calculated_at: datetime


# ================================================================
# OPTIONAL GENERIC RESPONSE
# ================================================================

class ValuationSummary(BaseModel):
    """Compact valuation summary."""

    variant_id: int

    market_value: float
    retail_value: float
    trade_value: float

    confidence_score: float

    currency: str = "KES"

    calculated_at: datetime
