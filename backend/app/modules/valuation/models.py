# app/modules/valuation/models.py
# ================================================================
# Auto-D Kenya - Valuation Models
# ================================================================

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from decimal import Decimal

from pydantic import BaseModel, Field


class ValuationReport(BaseModel):
    """Valuation report model."""
    
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID = Field(..., description="Foreign key to User")
    vehicle_id: UUID = Field(..., description="Foreign key to UserVehicle")
    variant_id: UUID = Field(..., description="Foreign key to VehicleVariant")
    
    # Valuation results
    estimated_value: Decimal = Field(..., description="Estimated market value")
    min_value: Decimal = Field(..., description="Minimum estimated value")
    max_value: Decimal = Field(..., description="Maximum estimated value")
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence score")
    
    # Valuation details
    valuation_method: str = Field("market", description="Valuation method used")
    data_points: int = Field(0, description="Number of data points used")
    
    # Depreciation
    depreciation_rate: float = Field(0.15, description="Annual depreciation rate")
    original_value: Optional[Decimal] = Field(None, description="Original vehicle value")
    current_depreciation: Optional[Decimal] = Field(None, description="Current depreciation amount")
    
    # Market comparison
    market_average: Optional[Decimal] = Field(None, description="Market average price")
    market_low: Optional[Decimal] = Field(None, description="Market low price")
    market_high: Optional[Decimal] = Field(None, description="Market high price")
    comparable_listings: int = Field(0, description="Number of comparable listings")
    
    # Adjustments
    adjustments: Dict[str, Any] = Field(default_factory=dict, description="Valuation adjustments")
    adjustment_total: Decimal = Field(Decimal(0), description="Total adjustment value")
    
    # Status
    status: str = Field("completed", description="Report status")
    expires_at: Optional[datetime] = Field(None, description="Report expiration date")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Additional metadata
    notes: Optional[str] = Field(None, description="Additional notes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ValuationAnalysis(BaseModel):
    """Valuation analysis model."""
    
    id: UUID = Field(default_factory=uuid4)
    report_id: UUID = Field(..., description="Foreign key to ValuationReport")
    
    # Analysis results
    market_trend: str = Field("stable", description="Market trend direction")
    demand_level: str = Field("medium", description="Demand level")
    supply_level: str = Field("medium", description="Supply level")
    
    # Key factors
    key_factors: List[str] = Field(default_factory=list, description="Key valuation factors")
    factor_weights: Dict[str, float] = Field(default_factory=dict, description="Factor weights")
    
    # Risk assessment
    risk_factors: List[str] = Field(default_factory=list, description="Risk factors")
    risk_score: float = Field(0.0, ge=0, le=1, description="Overall risk score")
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    price_suggestion: Optional[Decimal] = Field(None, description="Suggested asking price")
    negotiation_range: Dict[str, Decimal] = Field(default_factory=dict, description="Negotiation range")
    
    # Market insights
    market_insights: Dict[str, Any] = Field(default_factory=dict, description="Market insights")
    seasonality_factor: Optional[float] = Field(None, description="Seasonality factor")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ValuationHistory(BaseModel):
    """Valuation history model."""
    
    id: UUID = Field(default_factory=uuid4)
    vehicle_id: UUID = Field(..., description="Foreign key to UserVehicle")
    valuation_date: datetime = Field(default_factory=datetime.utcnow)
    estimated_value: Decimal = Field(..., description="Estimated value at this time")
    confidence_score: float = Field(..., ge=0, le=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ValuationComparable(BaseModel):
    """Comparable vehicle for valuation."""
    
    id: UUID = Field(default_factory=uuid4)
    report_id: UUID = Field(..., description="Foreign key to ValuationReport")
    
    # Comparable vehicle details
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    variant: Optional[str] = Field(None, description="Vehicle variant")
    year: int = Field(..., description="Vehicle year")
    mileage: int = Field(..., ge=0, description="Vehicle mileage")
    price: Decimal = Field(..., description="Listing price")
    
    # Source
    source: str = Field(..., description="Data source")
    source_id: Optional[str] = Field(None, description="Source listing ID")
    listing_url: Optional[str] = Field(None, description="Listing URL")
    listing_date: Optional[datetime] = Field(None, description="Listing date")
    
    # Similarity
    similarity_score: float = Field(0.0, ge=0, le=1, description="Similarity score")
    distance: Optional[float] = Field(None, description="Distance in KM")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ValuationReportResponse(ValuationReport):
    """Valuation report response with full details."""
    
    analysis: Optional[ValuationAnalysis] = Field(None, description="Valuation analysis")
    comparables: List[ValuationComparable] = Field(default_factory=list, description="Comparable vehicles")
    vehicle_details: Optional[Dict[str, Any]] = Field(None, description="Vehicle details")


__all__ = [
    "ValuationReport",
    "ValuationAnalysis",
    "ValuationHistory",
    "ValuationComparable",
    "ValuationReportResponse",
]
