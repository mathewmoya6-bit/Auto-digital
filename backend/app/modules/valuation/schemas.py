# app/modules/valuation/schemas.py
# ================================================================
# Auto-D Kenya - Valuation Schemas
# ================================================================

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


# ================================================================
# VALUATION REQUEST (Matches frontend payload)
# ================================================================

class ValuationRequest(BaseModel):
    """Vehicle valuation request - matches frontend payload."""
    
    make: str = Field(
        ...,
        description="Vehicle make (e.g., Toyota, Honda)"
    )
    
    model: str = Field(
        ...,
        description="Vehicle model (e.g., Corolla, Civic)"
    )
    
    trim: Optional[str] = Field(
        None,
        description="Vehicle trim level"
    )
    
    year: int = Field(
        ...,
        ge=1900,
        le=2100,
        description="Manufacture year"
    )
    
    mileage: int = Field(
        0,
        ge=0,
        description="Odometer reading in KM"
    )
    
    condition: str = Field(
        "good",
        description="Vehicle condition (excellent, very_good, good, fair, poor)"
    )
    
    accident_history: str = Field(
        "none",
        description="Accident history (none, minor, major, total_loss)"
    )
    
    previous_owners: int = Field(
        1,
        ge=0,
        description="Number of previous owners"
    )
    
    location: str = Field(
        "nairobi",
        description="Vehicle location"
    )
    
    fuel_type: Optional[str] = Field(
        None,
        description="Fuel type (petrol, diesel, electric, lpg)"
    )
    
    transmission: Optional[str] = Field(
        None,
        description="Transmission type (manual, automatic, cvt, amt)"
    )
    
    vehicle_type: Optional[str] = Field(
        None,
        description="Vehicle type (sedan, suv, hatchback, etc.)"
    )
    
    profit_margin: float = Field(
        0.0,
        ge=0,
        le=100,
        description="Profit margin percentage"
    )
    
    engine_capacity: Optional[str] = Field(
        None,
        description="Engine capacity in CC"
    )
    
    crsp_kes: Optional[float] = Field(
        None,
        description="CRSP base price in KES"
    )
    
    @field_validator("condition")
    @classmethod
    def validate_condition(cls, value: str) -> str:
        value = value.lower().strip()
        allowed = ["excellent", "very_good", "good", "fair", "poor"]
        if value not in allowed:
            raise ValueError(f"Condition must be one of {allowed}")
        return value
    
    @field_validator("accident_history")
    @classmethod
    def validate_accident(cls, value: str) -> str:
        value = value.lower().strip()
        allowed = ["none", "minor", "major", "total_loss"]
        if value not in allowed:
            raise ValueError(f"Accident history must be one of {allowed}")
        return value
    
    @field_validator("location")
    @classmethod
    def validate_location(cls, value: str) -> str:
        return value.lower().strip()
    
    @field_validator("vehicle_type")
    @classmethod
    def validate_vehicle_type(cls, value: Optional[str]) -> Optional[str]:
        if value:
            value = value.lower().strip()
            allowed = ["sedan", "suv", "hatchback", "wagon", "pickup", "van", "truck", "coupe", "motorcycle", "other"]
            if value not in allowed:
                raise ValueError(f"Vehicle type must be one of {allowed}")
        return value


# ================================================================
# LEGACY VALUATION REQUEST (Backward compatibility)
# ================================================================

class LegacyValuationRequest(BaseModel):
    """Legacy valuation request for backward compatibility."""
    
    variant_id: int = Field(..., gt=0, description="Vehicle variant ID")
    year: int = Field(..., ge=1980, description="Manufacturing year")
    mileage: int = Field(0, ge=0, description="Current mileage in KM")
    condition: str = Field("good", description="Vehicle condition")
    location: str = Field("nairobi", description="Vehicle location")
    fuel_type: Optional[str] = Field(None, description="Fuel type")
    transmission: Optional[str] = Field(None, description="Transmission type")
    accident_history: str = Field("none", description="Accident history")
    ownership_count: int = Field(1, ge=1, description="Number of previous owners")
    service_history: bool = Field(True, description="Has service records")
    profit_margin_percent: float = Field(5.00, ge=0, le=100, description="Profit margin")


# ================================================================
# VALUATION RESPONSE (Matches frontend expectations)
# ================================================================

class ValuationAdjustment(BaseModel):
    """Individual valuation adjustment."""
    factor: str = Field(..., description="Adjustment factor name")
    adjustment: float = Field(..., description="Amount adjusted")
    percentage: float = Field(..., description="Percentage adjustment")
    reason: str = Field(..., description="Reason for adjustment")
    factor_value: float = Field(1.0, description="Factor multiplier value")


class DepreciationResult(BaseModel):
    """Vehicle depreciation calculation."""
    rate: float = Field(..., description="Depreciation rate")
    age_years: int = Field(..., description="Vehicle age in years")
    remaining_value_percent: float = Field(..., description="Remaining value percentage")


class ValuationVehicle(BaseModel):
    """Vehicle information in valuation response."""
    crsp_id: Optional[int] = Field(None, description="CRSP ID")
    make: Optional[str] = Field(None, description="Vehicle make")
    model: Optional[str] = Field(None, description="Vehicle model")
    trim: Optional[str] = Field(None, description="Vehicle trim")
    year: Optional[int] = Field(None, description="Manufacture year")
    fuel_type: Optional[str] = Field(None, description="Fuel type")
    transmission: Optional[str] = Field(None, description="Transmission type")
    engine_capacity: Optional[str] = Field(None, description="Engine capacity")
    body_type: Optional[str] = Field(None, description="Body type")
    vehicle_type: Optional[str] = Field(None, description="Vehicle type")


class ValuationResponse(BaseModel):
    """Complete vehicle valuation response."""
    
    success: bool = Field(..., description="Whether valuation succeeded")
    status: str = Field(..., description="Status of valuation")
    crsp_found: bool = Field(False, description="Whether CRSP record was found")
    crsp_id: Optional[int] = Field(None, description="CRSP ID")
    crsp_value: float = Field(0.0, description="CRSP base value")
    
    # Core valuation values
    estimated_value: float = Field(..., description="Estimated vehicle value")
    estimated_value_min: float = Field(..., description="Minimum estimated value")
    estimated_value_max: float = Field(..., description="Maximum estimated value")
    
    # Market values (frontend expects these)
    market_value: float = Field(..., description="Estimated market value")
    retail_value: float = Field(..., description="Retail value")
    trade_value: float = Field(..., description="Trade-in value")
    dealer_value: float = Field(..., description="Dealer value")
    recommended_selling_price: Optional[float] = Field(None, description="Recommended selling price")
    
    confidence_score: int = Field(..., ge=0, le=100, description="Confidence score")
    
    adjustments: Dict[str, Any] = Field(default_factory=dict, description="Value adjustments")
    depreciation: Optional[DepreciationResult] = Field(None, description="Depreciation details")
    
    vehicle: ValuationVehicle = Field(..., description="Vehicle information")
    
    message: str = Field(..., description="Status message")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    
    currency: str = Field("KES", description="Currency code")
    calculated_at: str = Field(..., description="Calculation timestamp")
    
    comparables: List[Dict[str, Any]] = Field(default_factory=list, description="Comparable vehicles")
    sample_size: int = Field(0, description="Number of comparables used")
    recommendation: Optional[str] = Field(None, description="Recommendation")


# ================================================================
# VALUATION REPORT RESPONSE (Full report)
# ================================================================

class ReportMetadata(BaseModel):
    """Report metadata."""
    report_number: str = Field(..., description="Unique report number")
    generated_at: datetime = Field(..., description="Report generation timestamp")
    status: str = Field("completed", description="Report status")
    version: str = Field("2.0", description="Report version")


class ValuationReportResponse(BaseModel):
    """Full valuation report response."""
    report: ReportMetadata = Field(..., description="Report metadata")
    valuation: ValuationResponse = Field(..., description="Valuation results")
    disclaimer: str = Field(..., description="Disclaimer text")


# ================================================================
# VALUATION STATS
# ================================================================

class ValuationStats(BaseModel):
    """Valuation statistics."""
    total_valuations: int = Field(0, description="Total number of valuations")
    average_value: float = Field(0.0, description="Average valuation value")
    average_confidence_score: float = Field(0.0, description="Average confidence score")
    min_market_value: float = Field(0.0, description="Minimum market value")
    max_market_value: float = Field(0.0, description="Maximum market value")
    currency: str = Field("KES", description="Currency code")


# ================================================================
# VALUATION HISTORY
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
    make: Optional[str] = Field(None, description="Vehicle make")
    model: Optional[str] = Field(None, description="Vehicle model")


class ValuationHistoryResponse(BaseModel):
    """Valuation history response."""
    items: List[ValuationHistoryItem] = Field(default_factory=list, description="History items")
    total: int = Field(0, description="Total number of history items")


# ================================================================
# VALUATION HEALTH
# ================================================================

class ValuationHealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service health status")
    service: str = Field("valuation", description="Service name")
    version: str = Field("2.0", description="Service version")
    timestamp: str = Field(..., description="Health check timestamp")
    database: Optional[str] = Field(None, description="Database health status")
    error: Optional[str] = Field(None, description="Error message if any")


# ================================================================
# EXPORTS
# ================================================================

__all__ = [
    "ValuationRequest",
    "LegacyValuationRequest",
    "ValuationResponse",
    "ValuationReportResponse",
    "ValuationStats",
    "ValuationHistoryItem",
    "ValuationHistoryResponse",
    "ValuationHealthResponse",
    "ValuationAdjustment",
    "DepreciationResult",
    "ValuationVehicle",
    "ReportMetadata",
]
