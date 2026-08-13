# app/modules/valuation/models.py
# ================================================================
# Auto-D Kenya - Valuation Models
# ================================================================

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict, field_validator


# ================================================================
# VALUATION REQUEST (Frontend-compatible)
# ================================================================

class ValuationRequest(BaseModel):
    """
    Vehicle valuation request - matches frontend payload.
    """
    
    # Frontend fields
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    trim: Optional[str] = Field(None, description="Vehicle trim")
    year: int = Field(..., ge=1900, le=2100, description="Manufacture year")
    mileage: int = Field(0, ge=0, description="Odometer reading in KM")
    condition: str = Field("good", description="Vehicle condition")
    accident_history: str = Field("none", description="Accident history")
    previous_owners: int = Field(1, ge=0, description="Number of previous owners")
    location: str = Field("nairobi", description="Vehicle location")
    fuel_type: Optional[str] = Field(None, description="Fuel type")
    transmission: Optional[str] = Field(None, description="Transmission type")
    vehicle_type: Optional[str] = Field(None, description="Vehicle type")
    engine_capacity: Optional[str] = Field(None, description="Engine capacity")
    profit_margin: float = Field(0.0, ge=0, le=100, description="Profit margin percentage")
    crsp_kes: Optional[float] = Field(None, description="CRSP price if known")
    
    # Backend fields (derived or for internal use)
    vehicle_crsp_id: Optional[int] = Field(None, description="CRSP ID if known")
    manufacture_year: Optional[int] = Field(None, description="Alias for year")
    service_history: bool = Field(False, description="Service history available")
    ownership_count: int = Field(1, ge=1, description="Number of previous owners")
    profit_margin_percent: float = Field(5.0, ge=0, le=50, description="Profit margin")
    
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
    
    @model_validator(mode="after")
    def set_manufacture_year(self):
        if self.manufacture_year is None and self.year is not None:
            self.manufacture_year = self.year
        return self


# ================================================================
# LEGACY VALUATION REQUEST
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
# VALUATION ADJUSTMENT
# ================================================================

class ValuationAdjustment(BaseModel):
    """Individual valuation adjustment."""
    
    factor: str = Field(..., description="Adjustment factor name")
    adjustment: float = Field(..., description="Amount adjusted")
    percentage: float = Field(..., description="Percentage adjustment")
    factor_value: float = Field(1.0, description="Factor multiplier value")
    reason: Optional[str] = Field(None, description="Reason for adjustment")


# ================================================================
# DEPRECIATION
# ================================================================

class DepreciationResult(BaseModel):
    """Depreciation calculation result."""
    
    manufacture_year: int = Field(..., description="Manufacture year")
    vehicle_age: int = Field(..., description="Vehicle age in years")
    original_value: float = Field(..., description="Original vehicle value")
    depreciation_rate: float = Field(..., description="Depreciation rate")
    depreciation_value: float = Field(..., description="Depreciation amount")
    value_after_depreciation: float = Field(..., description="Value after depreciation")


# ================================================================
# VALUATION REPORT
# ================================================================

class ValuationReport(BaseModel):
    """Complete Auto-D Kenya vehicle valuation."""
    
    model_config = ConfigDict(from_attributes=True)
    
    # Vehicle info
    vehicle_crsp_id: Optional[int] = None
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    variant: Optional[str] = Field(None, description="Vehicle variant")
    manufacture_year: int = Field(..., description="Manufacture year")
    vehicle_age: int = Field(..., description="Vehicle age in years")
    
    # CRSP value
    crsp_value: float = Field(0.0, description="CRSP base value")
    crsp_found: bool = Field(False, description="Whether CRSP record was found")
    
    # Depreciation
    depreciation_rate: float = Field(0.0, description="Depreciation rate")
    depreciation_value: float = Field(0.0, description="Depreciation amount")
    value_after_depreciation: float = Field(0.0, description="Value after depreciation")
    
    # Market adjustments
    mileage_adjustment: float = Field(0.0, description="Mileage adjustment")
    condition_adjustment: float = Field(0.0, description="Condition adjustment")
    accident_adjustment: float = Field(0.0, description="Accident adjustment")
    location_adjustment: float = Field(0.0, description="Location adjustment")
    market_adjustment: float = Field(0.0, description="Market adjustment")
    
    # Final market value
    final_market_value: float = Field(..., description="Final estimated market value")
    
    # Selling price
    profit_margin_percent: float = Field(5.0, description="Profit margin percentage")
    profit_margin_value: float = Field(0.0, description="Profit margin amount")
    recommended_selling_price: float = Field(..., description="Recommended selling price")
    
    # Confidence
    confidence_score: float = Field(..., ge=0, le=100, description="Confidence score")
    
    # Market values (frontend expects these)
    retail_value: float = Field(..., description="Retail value")
    trade_value: float = Field(..., description="Trade-in value")
    dealer_value: float = Field(..., description="Dealer value")
    estimated_value_min: float = Field(..., description="Minimum estimated value")
    estimated_value_max: float = Field(..., description="Maximum estimated value")
    
    # Metadata
    valuation_method: str = Field("crsp_market", description="Valuation method used")
    data_points: int = Field(0, description="Number of data points used")
    comparable_listings: int = Field(0, description="Number of comparable listings")
    valuation_reference: Optional[str] = Field(None, description="Valuation reference")
    status: str = Field("completed", description="Valuation status")
    
    adjustments: List[ValuationAdjustment] = Field(default_factory=list, description="Value adjustments")
    notes: Optional[str] = Field(None, description="Additional notes")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last updated timestamp")


# ================================================================
# VALUATION RESPONSE (API response wrapper)
# ================================================================

class ValuationResponse(BaseModel):
    """API response wrapper for valuation."""
    
    success: bool = Field(True, description="Whether valuation succeeded")
    status: str = Field("completed", description="Status of valuation")
    message: str = Field("Valuation completed successfully.", description="Status message")
    
    # Core valuation data
    estimated_value: float = Field(..., description="Estimated vehicle value")
    market_value: float = Field(..., description="Market value")
    retail_value: float = Field(..., description="Retail value")
    trade_value: float = Field(..., description="Trade-in value")
    dealer_value: float = Field(..., description="Dealer value")
    recommended_selling_price: Optional[float] = Field(None, description="Recommended selling price")
    confidence_score: int = Field(..., ge=0, le=100, description="Confidence score")
    
    # CRSP info
    crsp_found: bool = Field(False, description="Whether CRSP record was found")
    crsp_id: Optional[int] = Field(None, description="CRSP ID")
    crsp_value: float = Field(0.0, description="CRSP base value")
    
    # Adjustments and depreciation
    adjustments: Dict[str, Any] = Field(default_factory=dict, description="Value adjustments")
    depreciation: Dict[str, Any] = Field(default_factory=dict, description="Depreciation details")
    
    # Vehicle info
    vehicle: Dict[str, Any] = Field(..., description="Vehicle information")
    
    # Warnings and metadata
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    currency: str = Field("KES", description="Currency code")
    calculated_at: str = Field(..., description="Calculation timestamp")
    comparables: List[Dict[str, Any]] = Field(default_factory=list, description="Comparable vehicles")
    sample_size: int = Field(0, description="Number of comparables used")
    recommendation: Optional[str] = Field(None, description="Recommendation")


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
# VALUATION COMPARABLE
# ================================================================

class ValuationComparable(BaseModel):
    """Real market comparable used in valuation."""
    
    id: Optional[int] = None
    valuation_id: Optional[int] = None
    vehicle_crsp_id: Optional[int] = None
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    variant: Optional[str] = Field(None, description="Vehicle variant")
    year: int = Field(..., description="Vehicle year")
    mileage: int = Field(0, ge=0, description="Vehicle mileage")
    price: float = Field(..., description="Listing price")
    source: str = Field(..., description="Data source")
    source_id: Optional[str] = Field(None, description="Source ID")
    listing_url: Optional[str] = Field(None, description="Listing URL")
    listing_date: Optional[datetime] = Field(None, description="Listing date")
    location: Optional[str] = Field(None, description="Vehicle location")
    similarity_score: float = Field(0, ge=0, le=100, description="Similarity score")
    distance_km: Optional[float] = Field(None, description="Distance in KM")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")


# ================================================================
# EXPORTS
# ================================================================

__all__ = [
    "ValuationRequest",
    "LegacyValuationRequest",
    "ValuationReport",
    "ValuationResponse",
    "ValuationStats",
    "ValuationHistoryItem",
    "ValuationHistoryResponse",
    "ValuationHealthResponse",
    "ValuationAdjustment",
    "DepreciationResult",
    "ValuationComparable",
]
