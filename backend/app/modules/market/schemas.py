# app/modules/market/schemas.py
# ================================================================
# Auto-D Kenya - Market Schemas
# ================================================================

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field


# ─── Request Schemas ──────────────────────────────────────────────

class MarketInsightsRequest(BaseModel):
    """Market insights request."""

    make: Optional[str] = Field(None, description="Filter by vehicle make")
    model: Optional[str] = Field(None, description="Filter by vehicle model")
    year_from: Optional[int] = Field(None, ge=1900, description="Year range start")
    year_to: Optional[int] = Field(None, ge=1900, description="Year range end")
    location: Optional[str] = Field(None, description="Filter by location")
    days: int = Field(30, ge=1, le=365, description="Days of data to analyze")


class MarketPricesRequest(BaseModel):
    """Market prices request."""

    variant_id: UUID = Field(..., description="Vehicle variant ID")
    days: int = Field(30, ge=1, le=365, description="Days of data to analyze")
    source: Optional[str] = Field(None, description="Filter by data source")


class MarketTrendsRequest(BaseModel):
    """Market trends request."""

    make: Optional[str] = Field(None, description="Filter by vehicle make")
    model: Optional[str] = Field(None, description="Filter by vehicle model")
    period: str = Field("6m", description="Time period: 1m, 3m, 6m, 1y, 2y")
    location: Optional[str] = Field(None, description="Filter by location")


class LocationFactorsRequest(BaseModel):
    """Location factors request."""

    location: str = Field(..., description="Location name")
    vehicle_type: Optional[str] = Field(None, description="Vehicle type")
    radius_km: int = Field(50, ge=1, le=500, description="Search radius in KM")


# ─── Response Schemas ─────────────────────────────────────────────

class MarketInsightsResponse(BaseModel):
    """Market insights response."""

    average_price: float = Field(..., description="Average market price")
    price_range: Dict[str, float] = Field(..., description="Min and max price")
    demand_score: float = Field(..., ge=0, le=100, description="Demand score")
    supply_score: float = Field(..., ge=0, le=100, description="Supply score")
    market_trend: str = Field(..., description="Market trend direction")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PriceDataResponse(BaseModel):
    """Price data response."""

    current_price: float = Field(..., description="Current market price")
    historical_prices: List[Dict[str, Any]] = Field(default_factory=list, description="Historical prices")
    price_trend: str = Field(..., description="Price trend direction")
    price_change_percentage: float = Field(..., description="Price change percentage")
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence score")
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class TrendDataResponse(BaseModel):
    """Trend data response."""

    trend_type: str = Field(..., description="Type of trend")
    data_points: List[Dict[str, Any]] = Field(default_factory=list, description="Data points")
    forecast: Optional[List[Dict[str, Any]]] = Field(None, description="Forecast data")
    seasonality: Optional[Dict[str, Any]] = Field(None, description="Seasonality analysis")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LocationFactorsResponse(BaseModel):
    """Location factors response."""

    location: str = Field(..., description="Location name")
    demand_factor: float = Field(..., ge=0, le=100, description="Demand factor")
    supply_factor: float = Field(..., ge=0, le=100, description="Supply factor")
    price_adjustment: float = Field(..., description="Price adjustment percentage")
    transportation_costs: float = Field(..., description="Transportation costs")
    market_maturity: str = Field(..., description="Market maturity level")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")


class SourceStatusResponse(BaseModel):
    """Data source status response."""

    source_name: str = Field(..., description="Source name")
    status: str = Field(..., description="Source status")
    last_update: Optional[datetime] = Field(None, description="Last update timestamp")
    data_points: int = Field(0, description="Number of data points")
    reliability_score: float = Field(..., ge=0, le=1, description="Reliability score")


class MarketPrice(BaseModel):
    """Market price item."""

    id: UUID = Field(..., description="Price record ID")
    variant_id: UUID = Field(..., description="Vehicle variant ID")
    price: Decimal = Field(..., description="Price")
    currency: str = Field("KES", description="Currency")
    source: str = Field(..., description="Data source")
    listing_url: Optional[str] = Field(None, description="Listing URL")
    location: Optional[str] = Field(None, description="Location")
    year: Optional[int] = Field(None, description="Vehicle year")
    mileage: Optional[int] = Field(None, description="Vehicle mileage")
    condition: Optional[str] = Field(None, description="Vehicle condition")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)


class MarketStatistic(BaseModel):
    """Market statistic."""

    metric: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    change: float = Field(0, description="Change percentage")
    period: str = Field(..., description="Time period")


class MarketComparison(BaseModel):
    """Market comparison."""

    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    average_price: float = Field(..., description="Average price")
    demand_score: float = Field(..., ge=0, le=100, description="Demand score")
    supply_score: float = Field(..., ge=0, le=100, description="Supply score")
    trend: str = Field(..., description="Market trend")


class MarketHealthResponse(BaseModel):
    """Market service health response."""

    status: str = Field(..., description="Service status")
    service: str = Field("market", description="Service name")
    version: str = Field("1.0", description="Service version")
    data_sources: List[str] = Field(default_factory=list, description="Active data sources")
    last_scrape: Optional[datetime] = Field(None, description="Last scrape timestamp")
    total_records: int = Field(0, description="Total market records")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


__all__ = [
    "MarketInsightsRequest",
    "MarketPricesRequest",
    "MarketTrendsRequest",
    "LocationFactorsRequest",
    "MarketInsightsResponse",
    "PriceDataResponse",
    "TrendDataResponse",
    "LocationFactorsResponse",
    "SourceStatusResponse",
    "MarketPrice",
    "MarketStatistic",
    "MarketComparison",
    "MarketHealthResponse",
]
