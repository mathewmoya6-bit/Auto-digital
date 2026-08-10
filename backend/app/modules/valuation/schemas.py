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
    
    vehicle_crsp_id: int = Field(
        ...,
        gt=0,
        description="Vehicle CRSP ID"
    )
    
    manufacture_year: int = Field(
        ...,
        ge=1900,
        le=2100,
        description="Manufacturing year"
    )
    
    mileage_km: int = Field(
        0,
        ge=0,
        description="Current mileage in KM"
    )
    
    vehicle_type: str = Field(
        "SEDAN",
        description="Vehicle type (SEDAN, SUV, PICKUP, etc.)"
    )
    
    condition_name: str = Field(
        "GOOD",
        description="Vehicle condition (EXCELLENT, GOOD, FAIR, POOR)"
    )
    
    accident_status: str = Field(
        "NONE",
        description="Accident status (NONE, MINOR_REPAIR, ACCIDENT_REPAIRED, STRUCTURAL_DAMAGE)"
    )
    
    location_name: str = Field(
        "NAIROBI",
        description="Vehicle location"
    )
    
    profit_margin_percent: float = Field(
        5.00,
        ge=0,
        le=100,
        description="Profit margin percentage for dealer pricing"
    )
    
    @field_validator("condition_name")
    @classmethod
    def validate_condition(cls, value: str):
        value = value.upper().strip()
        allowed = ["EXCELLENT", "GOOD", "FAIR", "POOR"]
        
        if value not in allowed:
            raise ValueError(f"Condition must be one of {allowed}")
        
        return value
    
    @field_validator("accident_status")
    @classmethod
    def validate_accident(cls, value: str):
        value = value.upper().strip()
        allowed = ["NONE", "MINOR_REPAIR", "ACCIDENT_REPAIRED", "STRUCTURAL_DAMAGE"]
        
        if value not in allowed:
            raise ValueError(f"Accident status must be one of {allowed}")
        
        return value
    
    @field_validator("vehicle_type")
    @classmethod
    def validate_vehicle_type(cls, value: str):
        value = value.upper().strip()
        allowed = ["SEDAN", "SUV", "PICKUP", "VAN", "HATCHBACK", "COUPE", "CONVERTIBLE"]
        
        if value not in allowed:
            raise ValueError(f"Vehicle type must be one of {allowed}")
        
        return value
    
    @field_validator("location_name")
    @classmethod
    def validate_location(cls, value: str):
        return value.upper().strip()


# ================================================================
# LEGACY REQUEST SCHEMA (for backward compatibility)
# ================================================================

class LegacyValuationRequest(BaseModel):
    """
    Legacy valuation request for backward compatibility.
    Maps to the new ValuationRequest.
    """
    
    variant_id: int = Field(
        ...,
        gt=0,
        description="Vehicle variant database ID"
    )
    
    year: int = Field(
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
        description="Vehicle condition (excellent, very_good, good, fair, poor)"
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
    
    accident_history: str = Field(
        "none",
        description="none | minor | major | total_loss"
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
    
    profit_margin_percent: float = Field(
        5.00,
        ge=0,
        le=100,
        description="Profit margin percentage"
    )
    
    def to_valuation_request(self) -> ValuationRequest:
        """Convert to new ValuationRequest format."""
        # Map condition
        condition_map = {
            "excellent": "EXCELLENT",
            "very_good": "EXCELLENT",
            "good": "GOOD",
            "fair": "FAIR",
            "poor": "POOR"
        }
        
        # Map accident status
        accident_map = {
            "none": "NONE",
            "minor": "MINOR_REPAIR",
            "major": "ACCIDENT_REPAIRED",
            "total_loss": "STRUCTURAL_DAMAGE"
        }
        
        # Map vehicle type based on body type (if available)
        # This would normally be resolved from the database
        vehicle_type = "SEDAN"
        
        return ValuationRequest(
            vehicle_crsp_id=self.variant_id,
            manufacture_year=self.year,
            mileage_km=self.mileage,
            vehicle_type=vehicle_type,
            condition_name=condition_map.get(self.condition.lower(), "GOOD"),
            accident_status=accident_map.get(self.accident_history.lower(), "NONE"),
            location_name=self.location.upper(),
            profit_margin_percent=self.profit_margin_percent
        )


# ================================================================
# VEHICLE DETAILS
# ================================================================

class VehicleDetails(BaseModel):
    """Vehicle details for valuation responses."""
    
    vehicle_crsp_id: int = Field(..., description="Vehicle CRSP ID")
    variant_id: Optional[int] = Field(None, description="Vehicle variant ID")
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    variant_name: Optional[str] = Field(None, description="Variant name")
    year: int = Field(..., description="Manufacturing year")
    fuel_type: Optional[str] = Field(None, description="Fuel type")
    transmission: Optional[str] = Field(None, description="Transmission type")
    engine_size_cc: Optional[int] = Field(None, description="Engine size in CC")
    body_type: Optional[str] = Field(None, description="Body type")
    vehicle_type: Optional[str] = Field(None, description="Vehicle type category")


# ================================================================
# VALUATION BREAKDOWN
# ================================================================

class ValuationAdjustment(BaseModel):
    """Individual valuation adjustment."""
    
    factor: str = Field(..., description="Adjustment factor name")
    adjustment: float = Field(..., description="Amount adjusted")
    percentage: float = Field(..., description="Percentage adjustment")
    reason: str = Field(..., description="Reason for adjustment")


class DepreciationDetails(BaseModel):
    """Depreciation details."""
    
    original_value: float = Field(..., description="Original vehicle value")
    current_value: float = Field(..., description="Current depreciated value")
    depreciation_amount: float = Field(..., description="Total depreciation amount")
    depreciation_percentage: float = Field(..., description="Depreciation percentage")
    annual_rate: float = Field(..., description="Annual depreciation rate")


class MarketComparison(BaseModel):
    """Market comparison details."""
    
    average_price: float = Field(..., description="Average market price")
    lowest_price: float = Field(..., description="Lowest market price")
    highest_price: float = Field(..., description="Highest market price")
    listings_count: int = Field(0, description="Number of listings analyzed")


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
# VALUATION RESPONSE SCHEMAS
# ================================================================

class ValuationResult(BaseModel):
    """Core valuation result details."""
    
    # Core value
    estimated_vehicle_value: float = Field(..., description="Estimated vehicle value")
    retail_value: float = Field(..., description="Retail value")
    trade_value: float = Field(..., description="Trade-in value")
    dealer_value: float = Field(..., description="Dealer value")
    
    # Currency
    currency: str = Field("KES", description="Currency code")
    
    # Confidence
    confidence_score: float = Field(..., ge=0, le=100, description="Confidence score (0-100)")
    
    # Range
    estimated_value_range: Dict[str, float] = Field(
        ...,
        description="Min and max value range"
    )
    
    # Sample
    sample_size: int = Field(0, description="Number of comparable vehicles used")
    
    # Additional database fields
    crsp_value: Optional[float] = Field(None, description="CRSP reference value")
    vehicle_age: Optional[int] = Field(None, description="Vehicle age in years")
    depreciation_rate: Optional[float] = Field(None, description="Depreciation rate")
    depreciated_value: Optional[float] = Field(None, description="Value after depreciation")
    fair_market_value: Optional[float] = Field(None, description="Fair market value")
    profit_margin_rate: Optional[float] = Field(None, description="Profit margin rate")
    profit_margin_amount: Optional[float] = Field(None, description="Profit margin amount")


class ValuationAnalysis(BaseModel):
    """Analysis details."""
    
    valuation_methodology: List[str] = Field(
        default_factory=list,
        description="Valuation methodology used"
    )
    adjustments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Adjustments applied"
    )
    engine_version: str = Field(
        "AUTO-D AI Valuation Engine v2.0",
        description="Engine version used"
    )


class ReportMetadata(BaseModel):
    """Report metadata."""
    
    title: str = Field("AUTO-D Vehicle Valuation Report", description="Report title")
    report_number: str = Field(..., description="Unique report number")
    generated_at: datetime = Field(..., description="Report generation timestamp")
    status: str = Field("completed", description="Report status")
    version: str = Field("2.0", description="Report version")
    description: Optional[str] = Field(None, description="Report description")


class ValuationReportResponse(BaseModel):
    """
    Comprehensive valuation report response.
    
    Used by the main /valuation/calculate endpoint.
    """
    
    report: ReportMetadata = Field(..., description="Report metadata")
    vehicle: VehicleDetails = Field(..., description="Vehicle information")
    valuation: ValuationResult = Field(..., description="Valuation results")
    comparables: List[ComparableVehicle] = Field(
        default_factory=list,
        description="Comparable vehicles"
    )
    analysis: ValuationAnalysis = Field(..., description="Analysis details")
    disclaimer: str = Field(..., description="Disclaimer text")
    
    class Config:
        json_schema_extra = {
            "example": {
                "report": {
                    "title": "AUTO-D Vehicle Valuation Report",
                    "report_number": "AUTO-VAL-20260115103000-ABCD",
                    "generated_at": "2026-01-15T10:30:00Z",
                    "status": "completed",
                    "version": "2.0"
                },
                "vehicle": {
                    "vehicle_crsp_id": 123,
                    "variant_id": 123,
                    "make": "Toyota",
                    "model": "Corolla",
                    "variant_name": "1.8 GL",
                    "year": 2020,
                    "fuel_type": "Petrol",
                    "transmission": "Automatic",
                    "engine_size_cc": 1800,
                    "body_type": "Sedan",
                    "vehicle_type": "SEDAN"
                },
                "valuation": {
                    "estimated_vehicle_value": 3500000.00,
                    "retail_value": 3800000.00,
                    "trade_value": 3200000.00,
                    "dealer_value": 3400000.00,
                    "currency": "KES",
                    "confidence_score": 85.0,
                    "estimated_value_range": {
                        "minimum": 3325000.00,
                        "maximum": 3675000.00
                    },
                    "sample_size": 15,
                    "crsp_value": 4000000.00,
                    "vehicle_age": 4,
                    "depreciation_rate": 0.15,
                    "depreciated_value": 3400000.00,
                    "fair_market_value": 3500000.00,
                    "profit_margin_rate": 0.05,
                    "profit_margin_amount": 175000.00
                },
                "comparables": [],
                "analysis": {
                    "valuation_methodology": [
                        "Vehicle age (2020)",
                        "Mileage (50,000 km)",
                        "Vehicle condition (Good)",
                        "Vehicle specifications",
                        "Location (Nairobi)",
                        "Depreciation model",
                        "Market comparables analysis"
                    ],
                    "adjustments": {
                        "mileage": -50000.00,
                        "condition": 0.05,
                        "accident": 0.00,
                        "location": 0.02,
                        "market": 0.01
                    },
                    "engine_version": "AUTO-D AI Valuation Engine v2.0"
                },
                "disclaimer": "This valuation is generated using the AUTO-D vehicle valuation model. It represents an indicative estimate based on vehicle specifications, age, mileage, condition, depreciation modelling and regional factors. It should not be interpreted as the current market asking price, dealer retail price, trade-in value or guaranteed selling price. Actual transaction values may vary depending on inspection results, ownership history, maintenance records and prevailing market conditions."
            }
        }


# ================================================================
# SIMPLE VALUE CHECK RESPONSE
# ================================================================

class QuickValuationResponse(BaseModel):
    """Quick valuation response for simple value checks."""
    
    vehicle_crsp_id: int = Field(..., description="Vehicle CRSP ID")
    estimated_value: float = Field(..., description="Estimated market value")
    currency: str = Field("KES", description="Currency code")
    confidence_score: float = Field(..., ge=0, le=100, description="Confidence score")
    calculated_at: str = Field(..., description="Calculation timestamp")


# ================================================================
# HISTORY RESPONSE
# ================================================================

class ValuationHistoryItem(BaseModel):
    """Single history item."""
    
    id: str = Field(..., description="History entry ID")
    vehicle_id: str = Field(..., description="Vehicle ID")
    market_value: float = Field(..., description="Market value at time of valuation")
    mileage: int = Field(..., description="Mileage at time of valuation")
    valuation_date: datetime = Field(..., description="Valuation date")
    report_number: Optional[str] = Field(None, description="Valuation report number")
    confidence_score: Optional[float] = Field(None, description="Confidence score")


class ValuationHistoryResponse(BaseModel):
    """Valuation history response."""
    
    items: List[ValuationHistoryItem] = Field(default_factory=list, description="History items")
    total: int = Field(0, description="Total number of history items")


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
    valuations_by_make: Dict[str, int] = Field(
        default_factory=dict,
        description="Valuations by make"
    )
    valuations_by_month: Dict[str, int] = Field(
        default_factory=dict,
        description="Valuations by month"
    )
    average_confidence: float = Field(0, description="Average confidence score")


# ================================================================
# HEALTH RESPONSE
# ================================================================

class ValuationHealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Service health status")
    service: str = Field("valuation", description="Service name")
    version: str = Field("2.0", description="Service version")
    timestamp: str = Field(..., description="Health check timestamp")
    database: Optional[str] = Field(None, description="Database health status")


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
) -> Dict[str, Any]:
    """
    Create a valuation response dict.
    (Legacy function for backward compatibility)
    """
    return {
        "vehicle": vehicle,
        "market_value": round(market_value, 2),
        "price_range_low": round(price_range_low, 2),
        "price_range_high": round(price_range_high, 2),
        "confidence_score": round(confidence_score, 2),
        "depreciation": depreciation,
        "adjustments": adjustments or [],
        "market_comparison": market_comparison,
        "recommendation": recommendation,
        "currency": "KES",
        "calculated_at": datetime.now(timezone.utc).isoformat()
    }


def create_valuation_report_response(
    vehicle: Dict[str, Any],
    valuation: Dict[str, Any],
    analysis: Dict[str, Any],
    comparables: Optional[List[Dict[str, Any]]] = None,
    report_number: Optional[str] = None,
    disclaimer_text: Optional[str] = None
) -> ValuationReportResponse:
    """
    Create a valuation report response.
    
    Args:
        vehicle: Vehicle details
        valuation: Valuation results
        analysis: Analysis details
        comparables: List of comparable vehicles
        report_number: Optional report number (auto-generated if not provided)
        disclaimer_text: Optional custom disclaimer text
    
    Returns:
        ValuationReportResponse
    """
    if not report_number:
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
        report_number = f"AUTO-VAL-{timestamp}-0000"
    
    if not disclaimer_text:
        disclaimer_text = (
            "This valuation is generated using the AUTO-D vehicle valuation model. "
            "It represents an indicative estimate based on vehicle specifications, "
            "age, mileage, condition, depreciation modelling and regional factors. "
            "It should not be interpreted as the current market asking price, "
            "dealer retail price, trade-in value or guaranteed selling price. "
            "Actual transaction values may vary depending on inspection results, "
            "ownership history, maintenance records and prevailing market conditions."
        )
    
    return ValuationReportResponse(
        report=ReportMetadata(
            title="AUTO-D Vehicle Valuation Report",
            report_number=report_number,
            generated_at=datetime.now(timezone.utc),
            status="completed",
            version="2.0",
            description=f"Valuation report for {vehicle.get('make', '')} {vehicle.get('model', '')} {vehicle.get('year', '')}"
        ),
        vehicle=VehicleDetails(**vehicle),
        valuation=ValuationResult(**valuation),
        comparables=[ComparableVehicle(**c) for c in (comparables or [])],
        analysis=ValuationAnalysis(**analysis),
        disclaimer=disclaimer_text
    )


def create_valuation_from_database(
    db_result: Dict[str, Any],
    vehicle_details: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create valuation dictionary from database result.
    
    Args:
        db_result: Database valuation result
        vehicle_details: Vehicle details
        
    Returns:
        Dict[str, Any]: Formatted valuation dictionary
    """
    final_value = float(db_result.get("final_value", 0))
    fair_market_value = float(db_result.get("fair_market_value", final_value))
    
    return {
        "market_value": final_value,
        "retail_value": final_value * 1.08,
        "trade_value": final_value * 0.85,
        "dealer_value": final_value * 0.95,
        "confidence_score": float(db_result.get("confidence_score", 65)),
        "estimated_value_range": {
            "minimum": final_value * 0.90,
            "maximum": final_value * 1.10
        },
        "sample_size": 0,
        "crsp_value": float(db_result.get("crsp_value", 0)),
        "vehicle_age": int(db_result.get("vehicle_age", 0)),
        "depreciation_rate": float(db_result.get("depreciation_rate", 0)),
        "depreciated_value": float(db_result.get("depreciated_value", 0)),
        "fair_market_value": fair_market_value,
        "profit_margin_rate": float(db_result.get("profit_margin_rate", 0)),
        "profit_margin_amount": float(db_result.get("profit_margin_amount", 0)),
        "adjustments": {
            "mileage": float(db_result.get("mileage_adjustment", 0)),
            "condition": float(db_result.get("condition_adjustment", 0)),
            "accident": float(db_result.get("accident_adjustment", 0)),
            "location": float(db_result.get("location_adjustment", 0)),
            "market": float(db_result.get("market_adjustment", 0)),
        }
    }


# ================================================================
# EXPORTS
# ================================================================

__all__ = [
    # Request schemas
    "ValuationRequest",
    "LegacyValuationRequest",
    
    # Response schemas
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
    
    # Factory functions
    "create_valuation_response",
    "create_valuation_report_response",
    "create_valuation_from_database",
]
