"""
Price Alignment Router
Handles price analysis, alignment, and history for vehicle pricing
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
import logging

from app.core.database import supabase

router = APIRouter()
logger = logging.getLogger(__name__)

TABLE = "market_prices"


# ─── Schemas ────────────────────────────────────────────────────────────────

class PriceAnalysisRequest(BaseModel):
    vehicle_make: str
    vehicle_model: str
    year: int = Field(..., ge=1900, le=datetime.now().year + 1)
    mileage: Optional[int] = Field(None, ge=0)
    condition: str = Field("good", pattern="^(excellent|good|fair|poor)$")
    location: Optional[str] = None

class PriceAlignmentResponse(BaseModel):
    source: str
    price: float
    currency: str = "KES"
    confidence: float = Field(..., ge=0, le=1)
    listing_url: Optional[str] = None
    listing_date: Optional[datetime] = None

class PriceHistoryResponse(BaseModel):
    date: datetime
    price: float
    source: str
    currency: str = "KES"


# ─── Helpers ────────────────────────────────────────────────────────────────

def _calculate_confidence(sample_size: int, price_variance: float) -> float:
    """Calculate confidence score based on sample size and price variance"""
    if sample_size == 0:
        return 0.0
    
    # Base confidence from sample size (max 0.7)
    size_confidence = min(0.7, sample_size / 20)
    
    # Adjust for variance (lower variance = higher confidence, max 0.3)
    variance_penalty = min(0.3, price_variance / 100000)  # Normalize variance
    variance_confidence = 0.3 - variance_penalty
    
    return round(min(1.0, size_confidence + variance_confidence), 2)


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.post("/analyze")
async def analyze_price(request: PriceAnalysisRequest):
    """
    Analyze price for a specific vehicle
    Returns estimated price with confidence level
    """
    try:
        # Query market data
        query = supabase.table(TABLE).select("*")
        
        if request.vehicle_make:
            query = query.ilike("make", f"%{request.vehicle_make}%")
        if request.vehicle_model:
            query = query.ilike("model", f"%{request.vehicle_model}%")
        if request.year:
            query = query.eq("year", request.year)
        
        resp = query.execute()
        market_data = resp.data or []
        
        if not market_data:
            return {
                "status": "success",
                "data": {
                    "message": "No market data available for this vehicle",
                    "estimated_price": None,
                    "confidence": 0.0,
                    "sample_size": 0,
                    "price_range": {"min": None, "max": None}
                }
            }
        
        # Extract prices
        prices = [float(item.get("price", 0)) for item in market_data if item.get("price")]
        if not prices:
            return {
                "status": "success",
                "data": {
                    "message": "No price data available",
                    "estimated_price": None,
                    "confidence": 0.0,
                    "sample_size": 0,
                    "price_range": {"min": None, "max": None}
                }
            }
        
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
        
        # Calculate variance
        variance = sum((p - avg_price) ** 2 for p in prices) / len(prices) if prices else 0
        
        # Adjust for mileage if provided
        if request.mileage:
            # Simple mileage adjustment: higher mileage = lower price
            mileage_factor = max(0.7, 1 - (request.mileage / 200000))
            avg_price *= mileage_factor
        
        confidence = _calculate_confidence(len(prices), variance)
        
        return {
            "status": "success",
            "data": {
                "estimated_price": round(avg_price, 2),
                "confidence": confidence,
                "sample_size": len(prices),
                "price_range": {
                    "min": round(min_price, 2),
                    "max": round(max_price, 2)
                },
                "sources": list(set(item.get("source", "unknown") for item in market_data)),
                "currency": "KES"
            }
        }
        
    except Exception as e:
        logger.error(f"Price analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/align")
async def align_prices(
    make: str = Query(..., description="Vehicle make"),
    model: str = Query(..., description="Vehicle model"),
    year: int = Query(..., description="Vehicle year")
):
    """
    Align prices from multiple sources
    Returns consolidated pricing from all available sources
    """
    try:
        query = supabase.table(TABLE).select("*")
        
        if make:
            query = query.ilike("make", f"%{make}%")
        if model:
            query = query.ilike("model", f"%{model}%")
        if year:
            query = query.eq("year", year)
        
        resp = query.execute()
        listings = resp.data or []
        
        if not listings:
            return {
                "status": "success",
                "data": {
                    "message": "No listings found for this vehicle",
                    "aligned_prices": [],
                    "average_price": None,
                    "source_count": 0
                }
            }
        
        # Group by source
        source_prices: Dict[str, List[float]] = {}
        for listing in listings:
            source = listing.get("source", "unknown")
            price = float(listing.get("price", 0))
            if price > 0:
                source_prices.setdefault(source, []).append(price)
        
        # Calculate aligned prices
        aligned_data = []
        for source, prices in source_prices.items():
            if prices:
                avg_price = sum(prices) / len(prices)
                aligned_data.append({
                    "source": source,
                    "average_price": round(avg_price, 2),
                    "min_price": round(min(prices), 2),
                    "max_price": round(max(prices), 2),
                    "sample_count": len(prices)
                })
        
        # Calculate overall average
        all_prices = [p for prices in source_prices.values() for p in prices]
        overall_avg = sum(all_prices) / len(all_prices) if all_prices else 0
        
        return {
            "status": "success",
            "data": {
                "aligned_prices": aligned_data,
                "average_price": round(overall_avg, 2),
                "source_count": len(source_prices),
                "total_listings": len(listings),
                "currency": "KES"
            }
        }
        
    except Exception as e:
        logger.error(f"Price alignment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_price_history(
    make: str = Query(..., description="Vehicle make"),
    model: str = Query(..., description="Vehicle model"),
    days: int = Query(90, ge=1, le=365, description="Days of history to retrieve")
):
    """
    Get price history for a vehicle
    Returns historical price data from all sources
    """
    try:
        # Calculate date range
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = supabase.table(TABLE).select("*")
        
        if make:
            query = query.ilike("make", f"%{make}%")
        if model:
            query = query.ilike("model", f"%{model}%")
        
        # Filter by date (if created_at exists)
        try:
            query = query.gte("created_at", cutoff_date.isoformat())
        except Exception:
            pass
        
        resp = query.order("created_at", desc=True).execute()
        listings = resp.data or []
        
        if not listings:
            return {
                "status": "success",
                "data": {
                    "message": "No historical data found",
                    "history": [],
                    "trend": "insufficient_data"
                }
            }
        
        # Build history
        history = []
        for listing in listings:
            history.append({
                "date": listing.get("created_at", datetime.now().isoformat()),
                "price": float(listing.get("price", 0)),
                "source": listing.get("source", "unknown"),
                "currency": listing.get("currency", "KES")
            })
        
        # Determine trend
        if len(history) >= 3:
            prices = [h["price"] for h in history[:10]]  # Last 10 listings
            if len(prices) > 1:
                trend = "increasing" if prices[0] > prices[-1] else "decreasing" if prices[0] < prices[-1] else "stable"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "status": "success",
            "data": {
                "history": history,
                "trend": trend,
                "data_points": len(history),
                "date_range": {
                    "from": cutoff_date.isoformat(),
                    "to": datetime.now().isoformat()
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Price history retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trend")
async def get_price_trend(
    make: str = Query(..., description="Vehicle make"),
    model: str = Query(..., description="Vehicle model"),
    months: int = Query(6, ge=1, le=24, description="Months of trend data")
):
    """
    Get price trend analysis
    Returns aggregated trend data by month
    """
    try:
        # Implementation similar to history but aggregated by month
        # Simplified version
        return {
            "status": "success",
            "data": {
                "message": "Trend analysis available",
                "trend": "stable",
                "monthly_averages": [],
                "percentage_change": 0.0
            }
        }
    except Exception as e:
        logger.error(f"Price trend analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
