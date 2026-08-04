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


class ComparableVehicle(BaseModel):
    """Schema for a comparable vehicle."""
    
    id: Optional[int] = None
    year: int = Field(..., description="Vehicle year")
    mileage: int = Field(..., description="Vehicle mileage")
    price: float = Field(..., description="Listing price")
    source: str = Field(..., description="Data source")
    location: Optional[str] = Field(None, description="Vehicle location")
    make: Optional[str] = Field(None, description="Vehicle make")
    model: Optional[str] = Field(None, description="Vehicle model")
    date: Optional[str] = Field(None, description="Listing date")
    url: Optional[str] = Field(None, description="Listing URL")
    difference: Optional[float] = Field(None, description="Price difference")


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
# VALUATION REPORT RESPONSE (NEW)
# ================================================================

class ReportMetadata(BaseModel):
    """Report metadata."""
    
    report_number: str = Field(..., description="Unique report number")
    generated_at: datetime = Field(..., description="Report generation timestamp")
    report_status: str = Field("completed", description="Report status")
    report_title: str = Field(..., description="Report title")
    report_description: str = Field(..., description="Report description")
    expires_at: Optional[datetime] = Field(None, description="Report expiration timestamp")


class ValuationResult(BaseModel):
    """Valuation result details."""
    
    estimated_vehicle_value: float = Field(..., description="Estimated vehicle value")
    retail_value: float = Field(..., description="Retail value")
    trade_value: float = Field(..., description="Trade-in value")
    dealer_value: float = Field(..., description="Dealer value")
    currency: str = Field("KES", description="Currency code")
    confidence_score: float = Field(..., description="Confidence score (0-1)")
    estimated_value_range: Dict[str, float] = Field(..., description="Min and max value range")
    sample_size: int = Field(0, description="Number of comparable vehicles used")


class ValuationAnalysis(BaseModel):
    """Analysis details."""
    
    methodology: str = Field(..., description="Analysis methodology")
    data_points: int = Field(..., description="Number of data points analyzed")
    key_factors: List[str] = Field(default_factory=list, description="Key factors considered")
    market_trend: Optional[str] = Field(None, description="Market trend direction")
    market_conditions: Optional[str] = Field(None, description="Market conditions")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")


class Disclaimer(BaseModel):
    """Disclaimer text."""
    
    text: str = Field(..., description="Disclaimer text")
    type: str = Field("standard", description="Disclaimer type")


class ValuationReportResponse(BaseModel):
    """
    Comprehensive valuation report response.
    
    Used by the main /valuation/calculate endpoint.
    """
    
    report: ReportMetadata = Field(..., description="Report metadata")
    vehicle: VehicleDetails = Field(..., description="Vehicle information")
    valuation: ValuationResult = Field(..., description="Valuation results")
    comparables: List[ComparableVehicle] = Field(default_factory=list, description="Comparable vehicles")
    analysis: ValuationAnalysis = Field(..., description="Analysis details")
    disclaimer: Disclaimer = Field(..., description="Disclaimer")
    
    class Config:
        json_schema_extra = {
            "example": {
                "report": {
                    "report_number": "VAL-2024-001",
                    "generated_at": "2024-01-15T10:30:00",
                    "report_status": "completed",
                    "report_title": "Vehicle Valuation Report",
                    "report_description": "Comprehensive valuation report for Toyota Corolla 2020"
                },
                "vehicle": {
                    "variant_id": 123,
                    "make": "Toyota",
                    "model": "Corolla",
                    "variant": "1.8 GL",
                    "year": 2020,
                    "fuel_type": "Petrol",
                    "transmission": "Automatic",
                    "engine_size": 1.8,
                    "body_type": "Sedan"
                },
                "valuation": {
                    "estimated_vehicle_value": 3500000,
                    "retail_value": 3800000,
                    "trade_value": 3200000,
                    "dealer_value": 3400000,
                    "currency": "KES",
                    "confidence_score": 0.85,
                    "estimated_value_range": {
                        "min": 3300000,
                        "max": 3700000
                    },
                    "sample_size": 15
                },
                "comparables": [],
                "analysis": {
                    "methodology": "Market-based valuation using comparable sales",
                    "data_points": 15,
                    "key_factors": ["Mileage", "Condition", "Market Demand", "Location"],
                    "market_trend": "Stable",
                    "market_conditions": "Normal",
                    "recommendations": ["Get professional inspection", "Consider market timing"]
                },
                "disclaimer": {
                    "text": "This valuation is an estimate based on market data...",
                    "type": "standard"
                }
            }
        }


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
# STATS RESPONSE
# ================================================================

class ValuationStats(BaseModel):
    """Valuation statistics."""
    
    total_valuations: int = Field(0, description="Total number of valuations")
    average_value: float = Field(0, description="Average valuation value")
    highest_value: float = Field(0, description="Highest valuation value")
    lowest_value: float = Field(0, description="Lowest valuation value")
    last_valuation_date: Optional[datetime] = Field(None, description="Last valuation date")
    total_value: float = Field(0, description="Total value of all valuations")
    valuations_by_make: Dict[str, int] = Field(default_factory=dict, description="Valuations by make")
    valuations_by_month: Dict[str, int] = Field(default_factory=dict, description="Valuations by month")
    average_confidence: float = Field(0, description="Average confidence score")


# ================================================================
# HEALTH RESPONSE
# ================================================================

class ValuationHealthResponse(BaseModel):

    status: str

    service: str = "valuation"

    version: str = "1.0"

    timestamp: str


# ================================================================
# FACTORY FUNCTIONS
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


def create_valuation_report_response(
    vehicle: Dict[str, Any],
    valuation: Dict[str, Any],
    analysis: Dict[str, Any],
    comparables: Optional[List[Dict[str, Any]]] = None,
    report_number: Optional[str] = None
) -> ValuationReportResponse:
    """
    Create a valuation report response.
    
    Args:
        vehicle: Vehicle details
        valuation: Valuation results
        analysis: Analysis details
        comparables: List of comparable vehicles
        report_number: Optional report number (auto-generated if not provided)
    
    Returns:
        ValuationReportResponse
    """
    if not report_number:
        report_number = f"VAL-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{datetime.now(timezone.utc).timestamp():.0f}"
    
    return ValuationReportResponse(
        report=ReportMetadata(
            report_number=report_number,
            generated_at=datetime.now(timezone.utc),
            report_status="completed",
            report_title="Vehicle Valuation Report",
            report_description=f"Comprehensive valuation report for {vehicle.get('make', '')} {vehicle.get('model', '')} {vehicle.get('year', '')}"
        ),
        vehicle=VehicleDetails(**vehicle),
        valuation=ValuationResult(**valuation),
        comparables=[ComparableVehicle(**c) for c in (comparables or [])],
        analysis=ValuationAnalysis(**analysis),
        disclaimer=Disclaimer(
            text="This valuation is an estimate based on market data and should not be considered as a definitive appraisal. Actual market prices may vary based on vehicle condition, location, demand, and other factors. This report is for informational purposes only and does not constitute financial advice.",
            type="standard"
        )
    )


# ================================================================
# EXPORTS
# ================================================================

__all__ = [
    # Request schemas
    "ValuationRequest",
    
    # Response schemas
    "ValuationResponse",
    "ValuationReportResponse",
    "QuickValuationResponse",
    "ValuationHealthResponse",
    "ValuationHistoryResponse",
    "ValuationHistoryItem",
    "ValuationStats",
    
    # Component schemas
    "VehicleDetails",
    "ValuationAdjustment",
    "DepreciationDetails",
    "MarketComparison",
    "ComparableVehicle",
    "ReportMetadata",
    "ValuationResult",
    "ValuationAnalysis",
    "Disclaimer",
    
    # Factory functions
    "create_valuation_response",
    "create_valuation_report_response",
]
