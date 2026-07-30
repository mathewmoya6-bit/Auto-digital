# app/modules/market/router.py
"""Market routes for Auto-D Kenya"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from datetime import datetime

from app.modules.market.service import MarketService
from app.modules.auth.dependencies import get_current_user

router = APIRouter()

# ─── SCHEMAS ──────────────────────────────────────────────────────

class MarketInsightsResponse(BaseModel):
    """Market insights response"""
    average_price: float
    price_range: Dict[str, float]
    demand_score: float
    supply_score: float
    market_trend: str
    recommendations: List[str]
    timestamp: datetime

class PriceDataResponse(BaseModel):
    """Price data response"""
    current_price: float
    historical_prices: List[Dict[str, Any]]
    price_trend: str
    price_change_percentage: float
    confidence_score: float
    last_updated: datetime

class TrendDataResponse(BaseModel):
    """Trend data response"""
    trend_type: str
    data_points: List[Dict[str, Any]]
    forecast: Optional[List[Dict[str, Any]]]
    seasonality: Optional[Dict[str, Any]]
    timestamp: datetime

class LocationFactorsResponse(BaseModel):
    """Location factors response"""
    location: str
    demand_factor: float
    supply_factor: float
    price_adjustment: float
    transportation_costs: float
    market_maturity: str
    recommendations: List[str]

class SourceStatusResponse(BaseModel):
    """Source status response"""
    source_name: str
    status: str
    last_update: Optional[datetime]
    data_points: int
    reliability_score: float

# ─── ENDPOINTS ───────────────────────────────────────────────────

@router.get("/market/insights", response_model=MarketInsightsResponse)
async def get_market_insights(
    make: Optional[str] = None,
    model: Optional[str] = None,
    year_from: Optional[int] = Query(None, ge=1900),
    year_to: Optional[int] = Query(None, ge=1900),
    current_user = Depends(get_current_user)
):
    """
    Get market insights for vehicle valuations.
    """
    service = MarketService()
    return await service.get_market_insights(
        make=make,
        model=model,
        year_from=year_from,
        year_to=year_to
    )

@router.get("/market/prices", response_model=PriceDataResponse)
async def get_market_prices(
    variant_id: int,
    days: Optional[int] = Query(30, ge=1, le=365),
    current_user = Depends(get_current_user)
):
    """
    Get market price data for a specific vehicle variant.
    """
    service = MarketService()
    return await service.get_market_prices(variant_id, days)

@router.get("/market/trends", response_model=TrendDataResponse)
async def get_market_trends(
    make: Optional[str] = None,
    model: Optional[str] = None,
    period: str = Query("6m", regex="^(1m|3m|6m|1y|2y)$"),
    current_user = Depends(get_current_user)
):
    """
    Get market trends for vehicle prices.
    """
    service = MarketService()
    return await service.get_market_trends(make, model, period)

@router.get("/market/location/factors", response_model=LocationFactorsResponse)
async def get_location_factors(
    location: str,
    vehicle_type: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Get location-based market factors affecting vehicle valuation.
    """
    service = MarketService()
    return await service.get_location_factors(location, vehicle_type)

@router.get("/market/sources/status", response_model=List[SourceStatusResponse])
async def get_source_status(
    current_user = Depends(get_current_user)
):
    """
    Get status of all market data sources.
    """
    service = MarketService()
    return await service.get_source_status()
