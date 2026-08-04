# app/modules/valuation/schemas.py
# ================================================================
# Auto-D Kenya - Valuation Schemas
# ================================================================
# TYPE: MODULE - Vehicle Valuation Pydantic schemas
# Compatible with Pydantic v2
# ================================================================

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator


# ================================================================
# REQUEST SCHEMAS
# ================================================================

class ValuationRequest(BaseModel):
    """
    Vehicle valuation request.

    Calculates:
    - Current market value
    - Depreciation
    - Price range
    - Confidence score
    """

    variant_id: int = Field(
        ...,
        gt=0,
        description="Vehicle variant database ID"
    )

    vehicle_year: int = Field(
        ...,
        ge=1980,
        description="Manufacturing year"
    )

    mileage: int = Field(
        0,
        ge=0,
        description="Current mileage in KM"
    )

    condition: str = Field(
        "good",
        description="Vehicle condition"
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

    accident_history: bool = Field(
        False,
        description="Whether vehicle has accident history"
    )

    ownership_count: int = Field(
        1,
        ge=1,
        description="Number of previous owners"
    )

    service_history: bool = Field(
        True,
        description="Has service records"
    )


    @field_validator("condition")
    @classmethod
    def validate_condition(cls, value: str):
        allowed = [
            "excellent",
            "good",
            "fair",
            "poor"
        ]

        value = value.lower()

        if value not in allowed:
            raise ValueError(
                f"Condition must be one of {allowed}"
            )

        return value


    @field_validator("location")
    @classmethod
    def validate_location(cls, value: str):
        return value.lower().strip()


    @field_validator("vehicle_year")
    @classmethod
    def validate_year(cls, value: int):

        current_year = datetime.now(
            timezone.utc
        ).year

        if value > current_year + 1:
            raise ValueError(
                "Vehicle year cannot be in the future"
            )

        return value


# ================================================================
# VEHICLE DETAILS
# ================================================================

class VehicleDetails(BaseModel):

    variant_id: int

    make: str

    model: str

    variant: str

    year: int

    fuel_type: Optional[str] = None

    transmission: Optional[str] = None

    engine_size: Optional[float] = None

    body_type: Optional[str] = None


# ================================================================
# VALUATION BREAKDOWN
# ================================================================

class ValuationAdjustment(BaseModel):

    factor: str = Field(
        ...,
        description="Adjustment factor"
    )

    adjustment: float = Field(
        ...,
        description="Amount adjusted"
    )

    percentage: float = Field(
        ...,
        description="Percentage adjustment"
    )

    reason: str


class DepreciationDetails(BaseModel):

    original_value: float

    current_value: float

    depreciation_amount: float

    depreciation_percentage: float

    annual_rate: float


class MarketComparison(BaseModel):

    average_price: float

    lowest_price: float

    highest_price: float

    listings_count: int = 0


# ================================================================
# RESPONSE SCHEMA
# ================================================================

class ValuationResponse(BaseModel):

    vehicle: VehicleDetails

    market_value: float = Field(
        ...,
        description="Estimated market value in KES"
    )

    price_range_low: float

    price_range_high: float

    confidence_score: float = Field(
        ...,
        ge=0,
        le=100
    )

    depreciation: DepreciationDetails

    adjustments: List[ValuationAdjustment] = Field(
        default_factory=list
    )

    market_comparison: Optional[
        MarketComparison
    ] = None

    recommendation: Optional[str] = None

    currency: str = "KES"

    calculated_at: str


# ================================================================
# SIMPLE VALUE CHECK RESPONSE
# ================================================================

class QuickValuationResponse(BaseModel):

    variant_id: int

    estimated_value: float

    currency: str = "KES"

    confidence_score: float

    calculated_at: str


# ================================================================
# HISTORY RESPONSE
# ================================================================

class ValuationHistoryItem(BaseModel):

    id: str

    vehicle_id: str

    market_value: float

    mileage: int

    valuation_date: datetime


class ValuationHistoryResponse(BaseModel):

    items: List[
        ValuationHistoryItem
    ] = Field(default_factory=list)

    total: int


# ================================================================
# HEALTH RESPONSE
# ================================================================

class ValuationHealthResponse(BaseModel):

    status: str

    service: str = "valuation"

    version: str = "1.0"

    timestamp: str


# ================================================================
# FACTORY FUNCTION
# ================================================================

def create_valuation_response(
    vehicle: Dict[str, Any],
    market_value: float,
    price_range_low: float,
    price_range_high: float,
    confidence_score: float,
    depreciation: Dict[str, Any],
    adjustments: Optional[List[Dict[str, Any]]] = None,
    market_comparison: Optional[Dict[str, Any]] = None,
    recommendation: Optional[str] = None
) -> ValuationResponse:

    return ValuationResponse(
        vehicle=VehicleDetails(**vehicle),
        market_value=round(market_value, 2),
        price_range_low=round(price_range_low, 2),
        price_range_high=round(price_range_high, 2),
        confidence_score=round(confidence_score, 2),
        depreciation=DepreciationDetails(**depreciation),
        adjustments=[
            ValuationAdjustment(**item)
            for item in (adjustments or [])
        ],
        market_comparison=(
            MarketComparison(**market_comparison)
            if market_comparison
            else None
        ),
        recommendation=recommendation,
        calculated_at=datetime.now(
            timezone.utc
        ).isoformat()
    )
