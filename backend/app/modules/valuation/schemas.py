# app/modules/valuation/schemas.py
# Auto-D Kenya - Valuation Schemas
# ================================================================
# TYPE: MODULE - Valuation data models

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


# ─── REQUEST SCHEMAS ──────────────────────────────────────────────

class ValuationRequest(BaseModel):
    """Valuation calculation request."""
    
    variant_id: int = Field(..., description="Vehicle variant ID", gt=0)
    year: int = Field(2020, description="Vehicle year of manufacture", ge=1980, le=2026)
    mileage: int = Field(50000, description="Odometer reading in km", ge=0)
    condition: str = Field("good", description="Vehicle condition: excellent, very_good, good, fair, poor")
    accident_history: str = Field("none", description="Accident history: none, minor, major, total_loss")
    previous_owners: int = Field(1, description="Number of previous owners", ge=0)
    service_history: bool = Field(True, description="Whether service history is available")
    location: str = Field("nairobi", description="Vehicle location/county")
    images: Optional[List[str]] = Field(None, description="List of image URLs or base64 encoded images")
    
    @field_validator('condition')
    @classmethod
    def validate_condition(cls, v: str) -> str:
        allowed = ["excellent", "very_good", "good", "fair", "poor"]
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Condition must be one of: {', '.join(allowed)}")
        return v
    
    @field_validator('accident_history')
    @classmethod
    def validate_accident(cls, v: str) -> str:
        allowed = ["none", "minor", "major", "total_loss"]
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Accident history must be one of: {', '.join(allowed)}")
        return v
    
    @field_validator('location')
    @classmethod
    def validate_location(cls, v: str) -> str:
        return v.lower().strip()


# ─── RESPONSE SCHEMAS ─────────────────────────────────────────────

# ─── LEGACY VALUATION RESPONSE (for backward compatibility) ─────

class ValuationResponse(BaseModel):
    """Legacy valuation response (deprecated - use ValuationReportResponse)."""
    variant_id: int
    market_value: float
    retail_value: float
    trade_value: float
    dealer_value: float = 0
    confidence_score: float = 0
    base_price: float = 0
    age_factor: float = 0
    mileage_factor: float = 0
    location_factor: float = 0
    condition_factor: float = 0
    accident_factor: float = 0


# ─── NEW REPORT STRUCTURE ─────────────────────────────────────────

class ReportMetadata(BaseModel):
    """Report metadata section."""
    title: str = Field(..., description="Report title")
    report_number: str = Field(..., description="Unique report identifier")
    generated_at: str = Field(..., description="ISO timestamp of generation")
    status: str = Field(..., description="Report status")
    version: str = Field(..., description="Report version")


class VehicleInfo(BaseModel):
    """Vehicle information section."""
    variant_id: int = Field(..., description="Vehicle variant ID")
    variant_name: str = Field(..., description="Variant name")
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    year: int = Field(..., description="Vehicle year")
    mileage: int = Field(..., description="Mileage in km")
    condition: str = Field(..., description="Vehicle condition")
    location: str = Field(..., description="Vehicle location")
    fuel_type: str = Field(..., description="Fuel type")
    transmission: str = Field(..., description="Transmission type")
    engine_size_cc: int = Field(..., description="Engine size in cc")
    body_type: str = Field(..., description="Body type")


class ValueRange(BaseModel):
    """Estimated value range."""
    minimum: float = Field(..., description="Minimum estimated value")
    maximum: float = Field(..., description="Maximum estimated value")


class ValuationResult(BaseModel):
    """Valuation results section."""
    estimated_vehicle_value: float = Field(..., description="Estimated vehicle value")
    retail_value: float = Field(..., description="Retail value")
    trade_value: float = Field(..., description="Trade-in value")
    dealer_value: float = Field(..., description="Dealer value")
    insurance_value: Optional[float] = Field(None, description="Insurance value")
    private_sale_value: Optional[float] = Field(None, description="Private sale value")
    currency: str = Field("KES", description="Currency code")
    confidence_score: int = Field(..., description="Confidence score (0-100)")
    estimated_value_range: ValueRange = Field(..., description="Value range")


class ValuationAnalysis(BaseModel):
    """Analysis section."""
    valuation_methodology: List[str] = Field(..., description="Methodology list")
    adjustments: Dict[str, float] = Field(default_factory=dict, description="Value adjustments")
    engine_version: str = Field(..., description="Engine version")
    explanation: Optional[str] = Field(None, description="AI-generated explanation")


class ValuationReportResponse(BaseModel):
    """Complete valuation report response."""
    report: ReportMetadata = Field(..., description="Report metadata")
    vehicle: VehicleInfo = Field(..., description="Vehicle information")
    valuation: ValuationResult = Field(..., description="Valuation results")
    analysis: ValuationAnalysis = Field(..., description="Analysis")
    disclaimer: str = Field(..., description="Legal disclaimer")


# ─── SIMPLE RESPONSE ──────────────────────────────────────────────

class SimpleValuationResponse(BaseModel):
    """Simple valuation response for quick lookups."""
    variant_id: int = Field(..., description="Vehicle variant ID")
    vehicle_name: str = Field(..., description="Vehicle display name")
    estimated_value: float = Field(..., description="Estimated vehicle value")
    confidence_score: int = Field(..., description="Confidence score (0-100)")
    currency: str = Field("KES", description="Currency code")
    generated_at: str = Field(..., description="ISO timestamp")


# ─── BULK VALUATION RESPONSE ─────────────────────────────────────

class BulkValuationItem(BaseModel):
    """Single item in bulk valuation response."""
    success: bool = Field(..., description="Whether the valuation succeeded")
    data: Optional[ValuationReportResponse] = Field(None, description="Valuation report if successful")
    error: Optional[str] = Field(None, description="Error message if failed")
    variant_id: int = Field(..., description="Variant ID")


class BulkValuationResponse(BaseModel):
    """Bulk valuation response."""
    status: str = Field(..., description="Overall status")
    total: int = Field(..., description="Total number of requests")
    successful: int = Field(..., description="Number of successful valuations")
    failed: int = Field(..., description="Number of failed valuations")
    results: List[BulkValuationItem] = Field(..., description="List of valuation results")


# ─── COMPARISON RESPONSE ──────────────────────────────────────────

class ComparisonItem(BaseModel):
    """Single item in valuation comparison."""
    variant_id: int = Field(..., description="Variant ID")
    vehicle: str = Field(..., description="Vehicle display name")
    estimated_value: Optional[float] = Field(None, description="Estimated value")
    confidence: Optional[int] = Field(None, description="Confidence score")
    error: Optional[str] = Field(None, description="Error message if failed")


class ComparisonResponse(BaseModel):
    """Valuation comparison response."""
    status: str = Field(..., description="Overall status")
    comparison: List[ComparisonItem] = Field(..., description="Comparison results")


# ─── HISTORY RESPONSE ─────────────────────────────────────────────

class HistoryResponse(BaseModel):
    """Valuation history response."""
    status: str = Field(..., description="Overall status")
    data: List[Dict[str, Any]] = Field(..., description="List of historical valuations")
    count: int = Field(..., description="Total number of records")
    user_id: str = Field(..., description="User ID")


class StatsResponse(BaseModel):
    """Valuation statistics response."""
    status: str = Field(..., description="Overall status")
    data: Dict[str, Any] = Field(..., description="Statistics data")
    user_id: str = Field(..., description="User ID")


# ─── HEALTH RESPONSE ──────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: str = Field(..., description="ISO timestamp")
    endpoints: List[str] = Field(..., description="Available endpoints")


# ─── FACTORY FUNCTIONS ────────────────────────────────────────────

def create_valuation_report(
    variant_id: int,
    variant_data: Dict[str, Any],
    valuation_result: Dict[str, Any],
    adjustments: Dict[str, float] = None,
    report_number: str = None
) -> ValuationReportResponse:
    """
    Factory function to create a valuation report response.
    """
    import secrets
    
    if not report_number:
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random_suffix = secrets.token_hex(4).upper()
        report_number = f"AUTO-VAL-{timestamp}-{random_suffix}"
    
    market_value = valuation_result.get("market_value", valuation_result.get("estimated_vehicle_value", 0))
    retail_value = valuation_result.get("retail_value", market_value * 1.08)
    trade_value = valuation_result.get("trade_value", market_value * 0.85)
    dealer_value = valuation_result.get("dealer_value", market_value * 0.92)
    confidence = valuation_result.get("confidence_score", 75)
    
    return ValuationReportResponse(
        report=ReportMetadata(
            title="AUTO-D Vehicle Valuation Report",
            report_number=report_number,
            generated_at=datetime.utcnow().isoformat(),
            status="Completed",
            version="1.0"
        ),
        vehicle=VehicleInfo(
            variant_id=variant_id,
            variant_name=variant_data.get("name", "Unknown"),
            make=variant_data.get("make_name", "Unknown"),
            model=variant_data.get("model_name", "Unknown"),
            year=valuation_result.get("year", 2020),
            mileage=valuation_result.get("mileage", 0),
            condition=valuation_result.get("condition", "Good"),
            location=valuation_result.get("location", "Nairobi"),
            fuel_type=variant_data.get("fuel_type_name", "Unknown"),
            transmission=variant_data.get("transmission_type_name", "Unknown"),
            engine_size_cc=variant_data.get("engine_size_cc", 0),
            body_type=variant_data.get("body_type_name", "Unknown")
        ),
        valuation=ValuationResult(
            estimated_vehicle_value=market_value,
            retail_value=retail_value,
            trade_value=trade_value,
            dealer_value=dealer_value,
            insurance_value=valuation_result.get("insurance_value", market_value * 1.05),
            private_sale_value=valuation_result.get("private_sale_value", market_value * 1.10),
            currency="KES",
            confidence_score=confidence,
            estimated_value_range=ValueRange(
                minimum=market_value * (0.95 if confidence >= 85 else 0.92),
                maximum=market_value * (1.05 if confidence >= 85 else 1.08)
            )
        ),
        analysis=ValuationAnalysis(
            valuation_methodology=[
                f"Vehicle age ({valuation_result.get('year', 2020)})",
                f"Mileage ({valuation_result.get('mileage', 0):,} km)",
                f"Vehicle condition ({valuation_result.get('condition', 'Good')})",
                "Vehicle specifications",
                f"Location ({valuation_result.get('location', 'Nairobi')})",
                "Depreciation model",
                "Market comparables analysis"
            ],
            adjustments=adjustments or {},
            engine_version="AUTO-D AI Valuation Engine v1.3",
            explanation=valuation_result.get("explanation", "Valuation based on standard market factors.")
        ),
        disclaimer=(
            "This valuation is generated using the AUTO-D vehicle valuation model. "
            "It represents an indicative estimate based on vehicle specifications, "
            "age, mileage, condition, depreciation modelling and regional factors. "
            "It should not be interpreted as the current market asking price, "
            "dealer retail price, trade-in value or guaranteed selling price. "
            "Actual transaction values may vary depending on inspection results, "
            "ownership history, maintenance records and prevailing market conditions."
        )
    )


# ─── LEGACY CONVERTER ─────────────────────────────────────────────

class LegacyValuationResponse(BaseModel):
    """Legacy flat response structure for backward compatibility."""
    report_number: str
    generated_at: str
    estimated_vehicle_value: float
    retail_value: float
    trade_value: float
    dealer_value: float
    currency: str
    confidence_score: int
    estimated_value_range: ValueRange
    vehicle: VehicleInfo
    analysis: ValuationAnalysis
    disclaimer: str
    
    @classmethod
    def from_report(cls, report: ValuationReportResponse) -> "LegacyValuationResponse":
        """Convert from new report format to legacy format."""
        return cls(
            report_number=report.report.report_number,
            generated_at=report.report.generated_at,
            estimated_vehicle_value=report.valuation.estimated_vehicle_value,
            retail_value=report.valuation.retail_value,
            trade_value=report.valuation.trade_value,
            dealer_value=report.valuation.dealer_value,
            currency=report.valuation.currency,
            confidence_score=report.valuation.confidence_score,
            estimated_value_range=report.valuation.estimated_value_range,
            vehicle=report.vehicle,
            analysis=report.analysis,
            disclaimer=report.disclaimer
        )
