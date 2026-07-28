"""
app/api/v1/price_alignment.py
==============================
Endpoints (mounted by main.py at {api_prefix}/price):
    POST /align    - is a proposed asking price above/below/within market?
    POST /analyze  - full market-price estimate for a vehicle
    GET  /history   - raw price points over time, for charting
    GET  /trend     - price points bucketed by month, for a trend line

Built on services/market_pricing.py's MarketPricingService (already
implemented). Comparable listings come from the `scraped_listings` table,
populated by scrapers/autochek_scraper.py, scrapers/jiji_scraper.py, etc.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.database import supabase
from services.market_pricing import MarketPricingService

router = APIRouter()


class PriceAnalyzeRequest(BaseModel):
    make: str
    model: str
    year: Optional[int] = None
    mileage_km: Optional[int] = None
    currency: str = "KES"


class PriceAlignRequest(BaseModel):
    make: str
    model: str
    asking_price: float = Field(..., gt=0)
    year: Optional[int] = None
    mileage_km: Optional[int] = None
    currency: str = "KES"


def _svc() -> MarketPricingService:
    return MarketPricingService(supabase)


@router.post("/analyze")
def analyze_price(payload: PriceAnalyzeRequest):
    estimate = _svc().estimate(
        make=payload.make,
        model=payload.model,
        year=payload.year,
        mileage_km=payload.mileage_km,
        currency=payload.currency,
    )
    if estimate.sample_size == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No comparable listings found for {payload.make} {payload.model} ({payload.year}).",
        )
    result = estimate.to_dict()
    result["confidence"] = estimate.confidence
    return result


@router.post("/align")
def align_price(payload: PriceAlignRequest):
    """Tells the caller whether a proposed asking price sits below, within,
    or above the market's p25-p75 range for comparable listings."""
    estimate = _svc().estimate(
        make=payload.make,
        model=payload.model,
        year=payload.year,
        mileage_km=payload.mileage_km,
        currency=payload.currency,
    )
    if estimate.sample_size == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No comparable listings found for {payload.make} {payload.model} ({payload.year}).",
        )

    if payload.asking_price < estimate.p25_price:
        verdict = "below_market"
    elif payload.asking_price > estimate.p75_price:
        verdict = "above_market"
    else:
        verdict = "within_market"

    pct_vs_median = (
        round((payload.asking_price - estimate.median_price) / estimate.median_price * 100, 1)
        if estimate.median_price
        else None
    )

    return {
        "asking_price": payload.asking_price,
        "verdict": verdict,
        "pct_vs_median": pct_vs_median,
        "market_estimate": estimate.to_dict(),
    }


@router.get("/history")
def price_history(
    make: str,
    model: str,
    year: Optional[int] = None,
    limit: int = Query(200, le=1000),
):
    """Raw (price, scraped_at) points, unaggregated, for a frontend chart
    that wants to do its own bucketing/smoothing."""
    query = (
        supabase.table("scraped_listings")
        .select("price, scraped_at, mileage_km, source")
        .ilike("make", make)
        .ilike("model", model)
        .not_.is_("price", "null")
        .order("scraped_at", desc=True)
        .limit(limit)
    )
    if year is not None:
        query = query.eq("year", year)
    resp = query.execute()
    rows = resp.data or []
    if not rows:
        raise HTTPException(status_code=404, detail=f"No price history found for {make} {model}.")
    return {"make": make, "model": model, "year": year, "points": rows}


@router.get("/trend")
def price_trend(
    make: str,
    model: str,
    year: Optional[int] = None,
    months: int = Query(12, le=36, description="How many recent months to bucket"),
):
    """Same underlying data as /history, but pre-bucketed by month (median
    price per month) - convenient when the caller just wants a trend line
    without doing its own aggregation."""
    query = (
        supabase.table("scraped_listings")
        .select("price, scraped_at")
        .ilike("make", make)
        .ilike("model", model)
        .not_.is_("price", "null")
    )
    if year is not None:
        query = query.eq("year", year)
    rows = query.execute().data or []

    if not rows:
        raise HTTPException(status_code=404, detail=f"No price history found for {make} {model}.")

    buckets: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        try:
            dt = datetime.fromisoformat(r["scraped_at"].replace("Z", "+00:00"))
        except (KeyError, ValueError, AttributeError):
            continue
        key = f"{dt.year}-{dt.month:02d}"
        buckets[key].append(float(r["price"]))

    sorted_months = sorted(buckets.keys())[-months:]
    trend = [
        {
            "month": m,
            "median_price": statistics.median(buckets[m]),
            "sample_size": len(buckets[m]),
        }
        for m in sorted_months
    ]
    return {"make": make, "model": model, "trend": trend}
