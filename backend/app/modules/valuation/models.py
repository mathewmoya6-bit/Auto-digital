```python
# app/modules/valuation/models.py

# ================================================================
# Auto-D Kenya - Valuation Models
# ================================================================

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict


# ================================================================
# VALUATION REQUEST
# ================================================================

class ValuationRequest(BaseModel):
    """
    Input required to calculate a vehicle valuation.
    """

    vehicle_crsp_id: int = Field(
        ...,
        gt=0,
        description="Vehicle CRSP/master vehicle ID"
    )

    manufacture_year: int = Field(
        ...,
        ge=1900,
        le=2100,
        description="Vehicle manufacture year"
    )

    mileage: int = Field(
        0,
        ge=0,
        description="Current mileage in kilometres"
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

    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    body_type: Optional[str] = None
    engine_capacity: Optional[float] = None

    service_history: bool = False
    ownership_count: int = Field(
        1,
        ge=1,
        description="Number of previous owners"
    )

    profit_margin_percent: float = Field(
        5.0,
        ge=0,
        le=50,
        description="Recommended selling profit margin"
    )


# ================================================================
# VALUATION ADJUSTMENT
# ================================================================

class ValuationAdjustment(BaseModel):
    """
    Individual valuation adjustment.
    """

    factor: str
    adjustment: Decimal
    percentage: float
    factor_value: float
    reason: Optional[str] = None


# ================================================================
# DEPRECIATION
# ================================================================

class DepreciationResult(BaseModel):
    """
    Depreciation calculation result.
    """

    manufacture_year: int
    vehicle_age: int

    original_value: Decimal
    depreciation_rate: float
    depreciation_value: Decimal
    value_after_depreciation: Decimal


# ================================================================
# VALUATION REPORT
# ================================================================

class ValuationReport(BaseModel):
    """
    Complete Auto-D Kenya vehicle valuation.
    """

    model_config = ConfigDict(from_attributes=True)

    valuation_id: Optional[int] = None

    vehicle_crsp_id: int

    make: str
    model: str
    variant: Optional[str] = None

    manufacture_year: int
    vehicle_age: int

    # ------------------------------------------------------------
    # BASE / CRSP VALUE
    # ------------------------------------------------------------

    crsp_value: Decimal

    # ------------------------------------------------------------
    # DEPRECIATION
    # ------------------------------------------------------------

    depreciation_rate: float
    depreciation_value: Decimal
    value_after_depreciation: Decimal

    # ------------------------------------------------------------
    # MARKET ADJUSTMENTS
    # ------------------------------------------------------------

    mileage_adjustment: Decimal = Decimal("0")
    condition_adjustment: Decimal = Decimal("0")
    accident_adjustment: Decimal = Decimal("0")
    location_adjustment: Decimal = Decimal("0")
    market_adjustment: Decimal = Decimal("0")

    # ------------------------------------------------------------
    # FINAL MARKET VALUE
    # ------------------------------------------------------------

    final_market_value: Decimal

    # ------------------------------------------------------------
    # SELLING PRICE
    # ------------------------------------------------------------

    profit_margin_percent: float = 5.0
    profit_margin_value: Decimal = Decimal("0")
    recommended_selling_price: Decimal

    # ------------------------------------------------------------
    # CONFIDENCE
    # ------------------------------------------------------------

    confidence_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence score from 0 to 100"
    )

    # ------------------------------------------------------------
    # VALUATION METADATA
    # ------------------------------------------------------------

    valuation_method: str = "crsp_market"

    data_points: int = 0
    comparable_listings: int = 0

    valuation_reference: Optional[str] = None

    status: str = "completed"

    adjustments: List[ValuationAdjustment] = Field(
        default_factory=list
    )

    notes: Optional[str] = None

    metadata: Dict[str, Any] = Field(
        default_factory=dict
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ================================================================
# VALUATION ANALYSIS
# ================================================================

class ValuationAnalysis(BaseModel):
    """
    Market analysis associated with a valuation.
    """

    valuation_id: Optional[int] = None

    market_trend: str = "stable"

    demand_level: str = "medium"

    supply_level: str = "medium"

    key_factors: List[str] = Field(
        default_factory=list
    )

    factor_weights: Dict[str, float] = Field(
        default_factory=dict
    )

    risk_factors: List[str] = Field(
        default_factory=list
    )

    risk_score: float = Field(
        0.0,
        ge=0,
        le=100
    )

    recommendations: List[str] = Field(
        default_factory=list
    )

    price_suggestion: Optional[Decimal] = None

    negotiation_min: Optional[Decimal] = None

    negotiation_max: Optional[Decimal] = None

    market_insights: Dict[str, Any] = Field(
        default_factory=dict
    )

    seasonality_factor: Optional[float] = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ================================================================
# VALUATION HISTORY
# ================================================================

class ValuationHistory(BaseModel):
    """
    Historical valuation record.
    """

    id: Optional[int] = None

    vehicle_crsp_id: int

    valuation_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    estimated_value: Decimal

    confidence_score: float = Field(
        ...,
        ge=0,
        le=100
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ================================================================
# VALUATION COMPARABLE
# ================================================================

class ValuationComparable(BaseModel):
    """
    Real market comparable used in valuation.
    """

    id: Optional[int] = None

    valuation_id: Optional[int] = None

    vehicle_crsp_id: Optional[int] = None

    make: str
    model: str

    variant: Optional[str] = None

    year: int

    mileage: int = Field(
        0,
        ge=0
    )

    price: Decimal

    source: str

    source_id: Optional[str] = None

    listing_url: Optional[str] = None

    listing_date: Optional[datetime] = None

    location: Optional[str] = None

    similarity_score: float = Field(
        0,
        ge=0,
        le=100
    )

    distance_km: Optional[float] = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ================================================================
# COMPLETE RESPONSE
# ================================================================

class ValuationReportResponse(ValuationReport):
    """
    Complete valuation response including analysis and comparables.
    """

    analysis: Optional[ValuationAnalysis] = None

    comparables: List[ValuationComparable] = Field(
        default_factory=list
    )

    vehicle_details: Optional[Dict[str, Any]] = None
```
