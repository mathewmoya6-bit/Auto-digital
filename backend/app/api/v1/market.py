"""
app/api/v1/market.py
======================
Endpoints (mounted by main.py at {api_prefix}/market):
    POST /scrape          - on-demand, synchronous scrape of ONE listing URL
    GET  /insights         - cross-make/model overview of the scraped catalog
    GET  /location/factors - per-location price multipliers

For bulk/scheduled scraping, see app/api/v1/scraper.py (POST /scraper/run,
/autochek, /jiji, /carapi) - this module's /scrape is deliberately limited to
a single URL, synchronous fetch (e.g. "refresh this one listing" or testing a
selector), not a batch job.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.database import supabase
from scrapers.autochek_scraper import AutochekScraper
from scrapers.jiji_scraper import JijiScraper
from services.location_factors import LocationFactorsService

router = APIRouter()

SINGLE_SCRAPER_REGISTRY = {
    "autochek": AutochekScraper,
    "jiji": JijiScraper,
}


class ScrapeOneRequest(BaseModel):
    source: str  # "autochek" | "jiji"
    url: str


@router.post("/scrape")
def scrape_one(payload: ScrapeOneRequest):
    scraper_cls = SINGLE_SCRAPER_REGISTRY.get(payload.source)
    if scraper_cls is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown source '{payload.source}'. Known: {list(SINGLE_SCRAPER_REGISTRY)}",
        )

    scraper = scraper_cls(dry_run=True)  # parse only; caller decides whether/how to persist
    try:
        resp = scraper.get(payload.url)
        resp.raise_for_status()
        record = scraper.parse_listing(resp.text, payload.url)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Failed to scrape {payload.url}: {exc}") from exc

    if record is None:
        raise HTTPException(status_code=422, detail="Page fetched but could not be parsed as a listing.")
    return record.to_dict()


@router.get("/insights")
def market_insights(limit_makes: int = Query(10, le=50)):
    """Coarse cross-catalog overview: which makes have the most listings and
    roughly what they trade for. For a precise single-vehicle valuation use
    POST /api/v1/price/analyze instead."""
    resp = supabase.table("scraped_listings").select("make, price").not_.is_("price", "null").execute()
    rows = resp.data or []
    if not rows:
        return {"makes": []}

    by_make: dict[str, list[float]] = {}
    for r in rows:
        make = (r.get("make") or "Unknown").title()
        by_make.setdefault(make, []).append(float(r["price"]))

    summary = [
        {
            "make": make,
            "sample_size": len(prices),
            "median_price": sorted(prices)[len(prices) // 2],
            "min_price": min(prices),
            "max_price": max(prices),
        }
        for make, prices in by_make.items()
    ]
    summary.sort(key=lambda m: m["sample_size"], reverse=True)
    return {"makes": summary[:limit_makes]}


@router.get("/location/factors")
def location_factors(
    make: Optional[str] = None,
    model: Optional[str] = None,
    year: Optional[int] = None,
):
    svc = LocationFactorsService(supabase)
    results = svc.compute(make=make, model=model, year=year)
    return {
        "filter": {"make": make, "model": model, "year": year},
        "locations": [
            {
                "location": r.location,
                "sample_size": r.sample_size,
                "median_price": r.median_price,
                "factor": r.factor,
            }
            for r in results
        ],
    }
