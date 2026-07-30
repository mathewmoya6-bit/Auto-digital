# app/modules/market/router.py
# Auto-D Kenya - Market Routes
# ================================================================
# TYPE: MODULE - Market API routes

from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.core.dependencies import get_current_user
from app.modules.market.service import MarketService

router = APIRouter()
market_service = MarketService()


@router.get("/market/insights")
async def get_market_insights(
    make: Optional[str] = None,
    model: Optional[str] = None
):
    """Get market insights for vehicles."""
    return await market_service.get_market_insights(make, model)


@router.get("/market/prices")
async def get_market_prices(
    make: str,
    model: str,
    year: Optional[int] = None
):
    """Get market prices for a vehicle."""
    return await market_service.get_market_prices(make, model, year)


@router.get("/market/trends")
async def get_market_trends(
    make: str,
    model: str,
    period: str = "90d"
):
    """Get market trends for a vehicle."""
    return await market_service.get_market_trends(make, model, period)


@router.get("/market/location/factors")
async def get_location_factors(
    location: str = "nairobi"
):
    """Get location factors for valuation."""
    return await market_service.get_location_factors(location)


@router.get("/market/sources/status")
async def get_source_status(current_user: dict = Depends(get_current_user)):
    """Get status of all market data sources."""
    return await market_service.get_source_status()
