# app/modules/valuation/schemas.py
# ================================================================
# Auto-D Kenya - Valuation Schemas
# ================================================================
# TYPE: MODULE - Vehicle Valuation Pydantic schemas
# Compatible with Pydantic v2
# ================================================================

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator, model_validator


# ================================================================
# VALUATION REQUEST
# ================================================================

class ValuationRequest(BaseModel):
    """Vehicle valuation request aligned to CRSP database."""
    
    vehicle_crsp_id: int = Field(
        ...,
        gt=0,
        description="CRSP vehicle ID"
    )

    manufacture_year: int = Field(
        ...,
        ge=1980,
        description="Vehicle manufacture year"
    )

    year: Optional[int] = Field(
        None,
        description="Valuation year"
    )

    mileage_km: int = Field(
        ...,
        ge=0,
        description="Vehicle mileage in kilometres"
    )

    vehicle_type: str = Field(
        "SEDAN",
        description="Vehicle type"
    )

    condition_name: str = Field(
        "GOOD",
        description="Vehicle condition"
    )

    accident_status: str = Field(
        "NONE",
        description="Accident status"
    )

    location_name: str = Field(
        "NAIROBI",
        description="Vehicle location"
    )

    profit_margin_percent: float = Field(
        5.0,
        ge=0,
        description="Profit margin percentage"
    )

    @field_validator(
        "vehicle_type",
        "condition_name",
        "accident_status",
        "location_name"
    )
    @classmethod
    def normalize_strings(cls, value: str) -> str:
        return value.strip().upper()
    
    @field_validator("year")
    @classmethod
    def validate_year(cls, value: Optional[int]) -> Optional[int]:
        if value is not None:
            current_year = datetime.now(timezone.utc).year
            if value > current_year + 1:
                raise ValueError("Vehicle year cannot be in the future")
        return value


# ================================================================
# LEGACY VALUATION REQUEST (backward compatibility)
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

    def to_valuation_request(self) -> ValuationRequest:
        """Convert to new ValuationRequest format."""
        condition_map = {
            "excellent": "EXCELLENT",
            "very_good": "EXCELLENT",
            "good": "GOOD",
            "fair": "FAIR",
            "poor": "POOR"
        }
        
        accident_map = {
            "none": "NONE",
            "minor": "MINOR_REPAIR",
            "major": "ACCIDENT_REPAIRED",
            "total_loss": "STRUCTURAL_DAMAGE"
        }
        
        return ValuationRequest(
            vehicle_crsp_id=self.variant_id,
            manufacture_year=self.year,
            year=self.year,
            mileage_km=self.mileage,
            vehicle_type="SEDAN",
            condition_name=condition_map.get(self.condition.lower(), "GOOD"),
            accident_status=accident_map.get(self.accident_history.lower(), "NONE"),
            location_name=self.location.upper(),
            profit_margin_percent=self.profit_margin_percent
        )


# ================================================================
# ADJUSTMENT
# ================================================================

class ValuationAdjustment(BaseModel):
    """Individual valuation adjustment."""

    factor: str = Field(..., description="Adjustment factor name")
    adjustment: float = Field(..., description="Amount adjusted")
    percentage: float = Field(..., description="Percentage adjustment")
    reason: str = Field(..., description="Reason for adjustment")
    factor_value: float = Field(1.0, description="Factor multiplier value")


# ================================================================
# DEPRECIATION
# ================================================================

class DepreciationResult(BaseModel):
    """Vehicle depreciation calculation."""

    original_value: float = Field(..., description="Original vehicle value")
    current_value: float = Field(..., description="Current depreciated value")
    depreciation_amount: float = Field(..., description="Total depreciation amount")
    depreciation_percentage: float = Field(..., description="Depreciation percentage")
    annual_rate: float = Field(..., description="Annual depreciation rate")
    age: int = Field(..., description="Vehicle age in years")


# ================================================================
# VEHICLE DETAILS
# ================================================================

class ValuationVehicle(BaseModel):
    """Authoritative vehicle information from vehicle_crsp_lookup."""

    crsp_id: int = Field(..., description="Vehicle CRSP ID")
    variant_id: Optional[int] = Field(None, description="Vehicle variant ID")

    make: Optional[str] = Field(None, description="Vehicle make")
    make_id: Optional[int] = Field(None, description="Make ID")

    model: Optional[str] = Field(None, description="Vehicle model")
    normalized_model: Optional[str] = Field(None, description="Normalized model name")

    model_id: Optional[int] = Field(None, description="Model ID")

    master_model_id: Optional[int] = Field(None, description="Master model ID")
    master_model_name: Optional[str] = Field(None, description="Master model name")

    generation_id: Optional[int] = Field(None, description="Generation ID")

    engine_capacity_id: Optional[int] = Field(None, description="Engine capacity ID")
    engine_capacity: Optional[str] = Field(None, description="Engine capacity (cc)")

    fuel: Optional[str] = Field(None, description="Fuel type")
    transmission: Optional[str] = Field(None, description="Transmission type")
    drive_configuration: Optional[str] = Field(None, description="Drive configuration")
    body_type: Optional[str] = Field(None, description="Body type")

    manufacture_year: Optional[int] = Field(None, description="Manufacture year")
    crsp_year: Optional[int] = Field(None, description="CRSP reference year")

    crsp_kes: Optional[float] = Field(None, description="CRSP base price in KES")

    currency: str = Field("KES", description="Currency code")

    effective_date: Optional[str] = Field(None, description="Effective date")

    is_inferred: bool = Field(False, description="Whether data is inferred")
    is_duplicate: bool = Field(False, description="Whether this is a duplicate")

    model_config = {"protected_namespaces": ()}


# ================================================================
# COMPARABLE VEHICLE
# ================================================================

class ValuationComparable(BaseModel):
    """Comparable market vehicle."""

    id: Optional[int] = Field(None, description="Comparable ID")
    make: Optional[str] = Field(None, description="Vehicle make")
    model: Optional[str] = Field(None, description="Vehicle model")
    variant: Optional[str] = Field(None, description="Vehicle variant")
    year: Optional[int] = Field(None, description="Vehicle year")
    mileage: Optional[int] = Field(None, description="Vehicle mileage")
    price: float = Field(..., description="Listing price")
    source: Optional[str] = Field(None, description="Data source")
    location: Optional[str] = Field(None, description="Vehicle location")
    date: Optional[str] = Field(None, description="Listing date")
    url: Optional[str] = Field(None, description="Listing URL")
    difference: Optional[float] = Field(None, description="Price difference")
    similarity_score: Optional[float] = Field(None, description="Similarity score (0-1)")


# ================================================================
# VALUATION RESPONSE
# ================================================================

class ValuationResponse(BaseModel):
    """Complete vehicle valuation response."""

    vehicle: ValuationVehicle = Field(..., description="Vehicle information")

    # Primary valuation
    market_value: float = Field(..., description="Estimated market value")

    # Market bands
    retail_value: float = Field(..., description="Retail value")
    trade_value: float = Field(..., description="Trade-in value")
    dealer_value: float = Field(..., description="Dealer value")

    recommended_selling_price: Optional[float] = Field(None, description="Recommended selling price")

    # Confidence
    confidence_score: float = Field(..., ge=0, le=100, description="Confidence score")

    # Depreciation
    depreciation: Optional[DepreciationResult] = Field(None, description="Depreciation details")

    # Adjustments
    adjustments: List[ValuationAdjustment] = Field(
        default_factory=list,
        description="Value adjustments"
    )

    # Market information
    sample_size: int = Field(0, description="Number of comparables used")
    market_trend: str = Field("Stable", description="Market trend indicator")
    comparables: List[ValuationComparable] = Field(
        default_factory=list,
        description="Comparable vehicles"
    )

    # Explanation
    recommendation: Optional[str] = Field(None, description="Recommendation")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")

    # Metadata
    currency: str = Field("KES", description="Currency code")
    calculated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Calculation timestamp"
    )

    # Additional fields for compatibility
    price_range_low: Optional[float] = Field(None, description="Lower price range")
    price_range_high: Optional[float] = Field(None, description="Upper price range")
    estimated_value_range: Optional[Dict[str, float]] = Field(None, description="Value range")

    @model_validator(mode="after")
    def set_price_range(self):
        if self.price_range_low is None and self.market_value:
            self.price_range_low = self.market_value * 0.90
            self.price_range_high = self.market_value * 1.10
        if self.estimated_value_range is None and self.market_value:
            self.estimated_value_range = {
                "minimum": self.market_value * 0.90,
                "maximum": self.market_value * 1.10
            }
        return self


# ================================================================
# VALUATION SUMMARY
# ================================================================

class ValuationSummary(BaseModel):
    """Compact valuation summary."""

    crsp_id: int = Field(..., description="Vehicle CRSP ID")
    market_value: float = Field(..., description="Estimated market value")
    retail_value: float = Field(..., description="Retail value")
    trade_value: float = Field(..., description="Trade-in value")
    confidence_score: float = Field(..., ge=0, le=100, description="Confidence score")
    currency: str = Field("KES", description="Currency code")
    calculated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Calculation timestamp"
    )


# ================================================================
# VALUATION REPORT RESPONSE
# ================================================================

class ValuationReportResponse(BaseModel):
    """Full valuation report response."""

    # Report metadata
    report_number: str = Field(..., description="Unique report number")
    generated_at: datetime = Field(..., description="Report generation timestamp")
    status: str = Field("completed", description="Report status")
    version: str = Field("2.0", description="Report version")

    # Vehicle information
    vehicle: ValuationVehicle = Field(..., description="Vehicle information")

    # Valuation results
    valuation: ValuationResponse = Field(..., description="Valuation results")

    # Value breakdown (for quick access)
    market_value: float = Field(..., description="Estimated market value")
    retail_value: float = Field(..., description="Retail value")
    trade_value: float = Field(..., description="Trade-in value")
    dealer_value: float = Field(..., description="Dealer value")
    confidence_score: float = Field(..., ge=0, le=100, description="Confidence score")

    # Depreciation
    depreciation: Optional[DepreciationResult] = Field(None, description="Depreciation details")

    # Adjustments
    adjustments: List[ValuationAdjustment] = Field(
        default_factory=list,
        description="Value adjustments"
    )

    # Comparables
    comparables: List[ValuationComparable] = Field(
        default_factory=list,
        description="Comparable vehicles"
    )

    # Analysis
    recommendation: Optional[str] = Field(None, description="Recommendation")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")

    # Metadata
    currency: str = Field("KES", description="Currency code")
    calculated_at: datetime = Field(..., description="Calculation timestamp")

    # Disclaimer
    disclaimer: str = Field(
        default=(
            "This valuation is generated using the AUTO-D vehicle valuation model. "
            "It represents an indicative estimate based on vehicle specifications, "
            "age, mileage, condition, depreciation modelling and regional factors. "
            "It should not be interpreted as the current market asking price, "
            "dealer retail price, trade-in value or guaranteed selling price. "
            "Actual transaction values may vary depending on inspection results, "
            "ownership history, maintenance records and prevailing market conditions."
        ),
        description="Disclaimer text"
    )

    @model_validator(mode="after")
    def validate_consistency(self):
        """Ensure valuation fields are consistent."""
        if self.valuation:
            if self.market_value != self.valuation.market_value:
                self.market_value = self.valuation.market_value
            if self.retail_value != self.valuation.retail_value:
                self.retail_value = self.valuation.retail_value
            if self.trade_value != self.valuation.trade_value:
                self.trade_value = self.valuation.trade_value
            if self.dealer_value != self.valuation.dealer_value:
                self.dealer_value = self.valuation.dealer_value
            if self.confidence_score != self.valuation.confidence_score:
                self.confidence_score = self.valuation.confidence_score
        return self


# ================================================================
# VALUATION STATS
# ================================================================

class ValuationStats(BaseModel):
    """Statistics returned by valuation endpoints."""

    total_valuations: int = Field(0, description="Total number of valuations")
    average_value: float = Field(0.0, description="Average valuation value")
    average_market_value: float = Field(0.0, description="Average market value")
    average_confidence_score: float = Field(0.0, description="Average confidence score")
    min_market_value: float = Field(0.0, description="Minimum market value")
    max_market_value: float = Field(0.0, description="Maximum market value")
    highest_value: float = Field(0.0, description="Highest valuation value")
    lowest_value: float = Field(0.0, description="Lowest valuation value")
    total_value: float = Field(0.0, description="Total value of all valuations")
    last_valuation_date: Optional[datetime] = Field(None, description="Last valuation date")
    valuations_by_make: Dict[str, int] = Field(
        default_factory=dict,
        description="Valuations by make"
    )
    valuations_by_month: Dict[str, int] = Field(
        default_factory=dict,
        description="Valuations by month"
    )
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

    items: List[ValuationHistoryItem] = Field(
        default_factory=list,
        description="History items"
    )
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
# QUICK VALUATION RESPONSE
# ================================================================

class QuickValuationResponse(BaseModel):
    """Quick valuation response for simple value checks."""

    crsp_id: int = Field(..., description="Vehicle CRSP ID")
    estimated_value: float = Field(..., description="Estimated market value")
    currency: str = Field("KES", description="Currency code")
    confidence_score: float = Field(..., ge=0, le=100, description="Confidence score")
    calculated_at: str = Field(..., description="Calculation timestamp")


# ================================================================
# FACTORY FUNCTIONS
# ================================================================

def create_valuation_response(
    vehicle: Dict[str, Any],
    market_value: float,
    price_range_low: Optional[float] = None,
    price_range_high: Optional[float] = None,
    confidence_score: float = 75,
    depreciation: Optional[Dict[str, Any]] = None,
    adjustments: Optional[List[Dict[str, Any]]] = None,
    comparables: Optional[List[Dict[str, Any]]] = None,
    recommendation: Optional[str] = None,
    warnings: Optional[List[str]] = None,
    sample_size: int = 0,
    market_trend: str = "Stable"
) -> ValuationResponse:
    """
    Create a valuation response from component parts.
    
    Args:
        vehicle: Vehicle details dictionary
        market_value: Estimated market value
        price_range_low: Lower price range
        price_range_high: Upper price range
        confidence_score: Confidence score (0-100)
        depreciation: Depreciation details
        adjustments: List of adjustments
        comparables: List of comparable vehicles
        recommendation: Recommendation text
        warnings: List of warnings
        sample_size: Number of comparables used
        market_trend: Market trend indicator
        
    Returns:
        ValuationResponse
    """
    vehicle_obj = ValuationVehicle(**vehicle)
    
    retail_value = market_value * 1.08
    trade_value = market_value * 0.85
    dealer_value = market_value * 0.95
    
    depreciation_obj = None
    if depreciation:
        depreciation_obj = DepreciationResult(**depreciation)
    
    adjustment_objs = []
    if adjustments:
        for adj in adjustments:
            if isinstance(adj, dict):
                adjustment_objs.append(ValuationAdjustment(**adj))
            else:
                adjustment_objs.append(adj)
    
    comparable_objs = []
    if comparables:
        for comp in comparables:
            if isinstance(comp, dict):
                comparable_objs.append(ValuationComparable(**comp))
            else:
                comparable_objs.append(comp)
    
    return ValuationResponse(
        vehicle=vehicle_obj,
        market_value=market_value,
        retail_value=retail_value,
        trade_value=trade_value,
        dealer_value=dealer_value,
        recommended_selling_price=market_value * 1.10,
        confidence_score=confidence_score,
        depreciation=depreciation_obj,
        adjustments=adjustment_objs,
        sample_size=sample_size,
        market_trend=market_trend,
        comparables=comparable_objs,
        recommendation=recommendation,
        warnings=warnings or [],
        price_range_low=price_range_low or market_value * 0.90,
        price_range_high=price_range_high or market_value * 1.10,
        estimated_value_range={
            "minimum": price_range_low or market_value * 0.90,
            "maximum": price_range_high or market_value * 1.10
        }
    )


def create_valuation_report_response(
    vehicle: Dict[str, Any],
    valuation: Dict[str, Any],
    report_number: Optional[str] = None,
    disclaimer_text: Optional[str] = None
) -> ValuationReportResponse:
    """
    Create a valuation report response.
    
    Args:
        vehicle: Vehicle details dictionary
        valuation: Valuation results dictionary
        report_number: Optional report number
        disclaimer_text: Optional custom disclaimer text
        
    Returns:
        ValuationReportResponse
    """
    vehicle_obj = ValuationVehicle(**vehicle)
    
    # Build valuation response
    val_response = ValuationResponse(
        vehicle=vehicle_obj,
        market_value=valuation.get("market_value", 0),
        retail_value=valuation.get("retail_value", valuation.get("market_value", 0) * 1.08),
        trade_value=valuation.get("trade_value", valuation.get("market_value", 0) * 0.85),
        dealer_value=valuation.get("dealer_value", valuation.get("market_value", 0) * 0.95),
        recommended_selling_price=valuation.get("recommended_selling_price"),
        confidence_score=valuation.get("confidence_score", 75),
        depreciation=DepreciationResult(**valuation["depreciation"]) if valuation.get("depreciation") else None,
        adjustments=[ValuationAdjustment(**adj) for adj in valuation.get("adjustments", [])],
        sample_size=valuation.get("sample_size", 0),
        market_trend=valuation.get("market_trend", "Stable"),
        comparables=[ValuationComparable(**comp) for comp in valuation.get("comparables", [])],
        recommendation=valuation.get("recommendation"),
        warnings=valuation.get("warnings", []),
        price_range_low=valuation.get("price_range_low"),
        price_range_high=valuation.get("price_range_high"),
        estimated_value_range=valuation.get("estimated_value_range")
    )
    
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
    
    now = datetime.now(timezone.utc)
    
    return ValuationReportResponse(
        report_number=report_number,
        generated_at=now,
        status="completed",
        version="2.0",
        vehicle=vehicle_obj,
        valuation=val_response,
        market_value=val_response.market_value,
        retail_value=val_response.retail_value,
        trade_value=val_response.trade_value,
        dealer_value=val_response.dealer_value,
        confidence_score=val_response.confidence_score,
        depreciation=val_response.depreciation,
        adjustments=val_response.adjustments,
        comparables=val_response.comparables,
        recommendation=val_response.recommendation,
        warnings=val_response.warnings,
        currency="KES",
        calculated_at=now,
        disclaimer=disclaimer_text
    )


def create_valuation_from_database(
    db_result: Dict[str, Any],
    vehicle_details: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create valuation dictionary from database result.
    
    This function is used by the router to convert database results
    into the expected valuation format.
    
    Args:
        db_result: Database valuation result from stored procedure
        vehicle_details: Vehicle details dictionary
        
    Returns:
        Dict[str, Any]: Formatted valuation dictionary
    """
    final_value = float(db_result.get("final_value", 0))
    fair_market_value = float(db_result.get("fair_market_value", final_value))
    
    # Extract adjustments
    adjustments = {}
    
    # Mileage adjustment
    mileage_adj = float(db_result.get("mileage_adjustment", 0))
    if mileage_adj != 0:
        adjustments["mileage"] = mileage_adj
    
    # Condition adjustment
    condition_adj = float(db_result.get("condition_adjustment", 0))
    if condition_adj != 0:
        adjustments["condition"] = condition_adj
    
    # Accident adjustment
    accident_adj = float(db_result.get("accident_adjustment", 0))
    if accident_adj != 0:
        adjustments["accident"] = accident_adj
    
    # Location adjustment
    location_adj = float(db_result.get("location_adjustment", 0))
    if location_adj != 0:
        adjustments["location"] = location_adj
    
    # Market adjustment
    market_adj = float(db_result.get("market_adjustment", 0))
    if market_adj != 0:
        adjustments["market"] = market_adj
    
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
        "adjustments": adjustments
    }


# ================================================================
# EXPORTS
# ================================================================

__all__ = [
    # Request schemas
    "ValuationRequest",
    "LegacyValuationRequest",
    
    # Response schemas
    "ValuationResponse",
    "ValuationReportResponse",
    "ValuationSummary",
    "ValuationStats",
    "ValuationHistoryItem",
    "ValuationHistoryResponse",
    "ValuationHealthResponse",
    "QuickValuationResponse",
    
    # Component schemas
    "ValuationAdjustment",
    "DepreciationResult",
    "ValuationVehicle",
    "ValuationComparable",
    
    # Factory functions
    "create_valuation_response",
    "create_valuation_report_response",
    "create_valuation_from_database",
]
