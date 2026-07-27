"""
market_pricing.py
==================
Turns raw rows in Supabase's `scraped_listings` table into market-price
insight: given a make/model/year(/mileage), what's the going rate?

Reads only - this module never scrapes or writes listings itself (that's
scrapers/*), it just aggregates what's already there. It does, however,
optionally write its aggregate results to a `market_prices` cache table so
callers (e.g. a valuation endpoint) don't recompute stats on every request.

Expected Supabase schema (in addition to scraped_listings - see base_scraper.py):
    market_prices (
        id bigserial primary key,
        make text, model text, year int,
        sample_size int,
        min_price numeric, max_price numeric,
        median_price numeric, mean_price numeric,
        p25_price numeric, p75_price numeric,
        currency text,
        computed_at timestamptz,
        unique (make, model, year, currency)
    )
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from services.scraper_logger import get_logger

logger = get_logger(__name__)

# Outlier guard: listings priced below/above these multiples of the sample median
# are dropped before computing stats (catches obvious data-entry errors like a
# car listed at "1" or a decimal-point typo blowing up the average).
OUTLIER_LOW_MULTIPLE = 0.15
OUTLIER_HIGH_MULTIPLE = 6.0
MIN_SAMPLE_SIZE_FOR_CONFIDENCE = 5


@dataclass
class PriceEstimate:
    make: str
    model: str
    year: Optional[int]
    currency: str
    sample_size: int
    min_price: Optional[float]
    max_price: Optional[float]
    median_price: Optional[float]
    mean_price: Optional[float]
    p25_price: Optional[float]
    p75_price: Optional[float]
    confidence: str  # "low" | "medium" | "high", based purely on sample size

    def to_dict(self) -> dict:
        return {
            "make": self.make,
            "model": self.model,
            "year": self.year,
            "currency": self.currency,
            "sample_size": self.sample_size,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "median_price": self.median_price,
            "mean_price": self.mean_price,
            "p25_price": self.p25_price,
            "p75_price": self.p75_price,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }


class MarketPricingService:
    def __init__(self, supabase_client):
        """`supabase_client` is a supabase.Client, typically shared with the
        scrapers via the same SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY env vars."""
        self.supabase = supabase_client

    # ------------------------------------------------------------------ #
    # Data access
    # ------------------------------------------------------------------ #

    def _fetch_prices(
        self,
        make: str,
        model: str,
        year: Optional[int] = None,
        year_tolerance: int = 0,
        mileage_km: Optional[int] = None,
        mileage_tolerance_km: int = 30_000,
        currency: str = "KES",
    ) -> list[float]:
        query = (
            self.supabase.table("scraped_listings")
            .select("price, mileage_km, year")
            .ilike("make", make)
            .ilike("model", model)
            .eq("currency", currency)
            .not_.is_("price", "null")
        )
        if year is not None:
            query = query.gte("year", year - year_tolerance).lte("year", year + year_tolerance)

        resp = query.execute()
        rows = resp.data or []

        if mileage_km is not None:
            rows = [
                r
                for r in rows
                if r.get("mileage_km") is None
                or abs(r["mileage_km"] - mileage_km) <= mileage_tolerance_km
            ]

        return [float(r["price"]) for r in rows if r.get("price") is not None]

    # ------------------------------------------------------------------ #
    # Stats
    # ------------------------------------------------------------------ #

    @staticmethod
    def _strip_outliers(prices: list[float]) -> list[float]:
        if len(prices) < 3:
            return prices
        median = statistics.median(prices)
        low = median * OUTLIER_LOW_MULTIPLE
        high = median * OUTLIER_HIGH_MULTIPLE
        return [p for p in prices if low <= p <= high]

    @staticmethod
    def _percentile(sorted_prices: list[float], pct: float) -> float:
        if not sorted_prices:
            return 0.0
        idx = int(round(pct * (len(sorted_prices) - 1)))
        return sorted_prices[idx]

    def estimate(
        self,
        make: str,
        model: str,
        year: Optional[int] = None,
        mileage_km: Optional[int] = None,
        currency: str = "KES",
        widen_year_search: bool = True,
    ) -> PriceEstimate:
        """Compute a price estimate for a make/model(/year/mileage).

        If the exact year has too few comparable listings, `widen_year_search`
        progressively widens the year window (+-1, then +-2) before giving up -
        better to say "here's a rough estimate from nearby years" than nothing.
        """
        tolerance = 0
        prices: list[float] = []
        while True:
            prices = self._fetch_prices(
                make, model, year=year, year_tolerance=tolerance, mileage_km=mileage_km, currency=currency
            )
            clean = self._strip_outliers(prices)
            if len(clean) >= MIN_SAMPLE_SIZE_FOR_CONFIDENCE or not widen_year_search or tolerance >= 2 or year is None:
                prices = clean
                break
            tolerance += 1

        if not prices:
            logger.info("No comparable listings found for %s %s (%s)", make, model, year)
            return PriceEstimate(
                make=make, model=model, year=year, currency=currency, sample_size=0,
                min_price=None, max_price=None, median_price=None, mean_price=None,
                p25_price=None, p75_price=None, confidence="low",
            )

        prices_sorted = sorted(prices)
        n = len(prices_sorted)
        confidence = (
            "high" if n >= 20 else "medium" if n >= MIN_SAMPLE_SIZE_FOR_CONFIDENCE else "low"
        )

        estimate = PriceEstimate(
            make=make,
            model=model,
            year=year,
            currency=currency,
            sample_size=n,
            min_price=prices_sorted[0],
            max_price=prices_sorted[-1],
            median_price=statistics.median(prices_sorted),
            mean_price=statistics.fmean(prices_sorted),
            p25_price=self._percentile(prices_sorted, 0.25),
            p75_price=self._percentile(prices_sorted, 0.75),
            confidence=confidence,
        )
        return estimate

    # ------------------------------------------------------------------ #
    # Cache write-through
    # ------------------------------------------------------------------ #

    def refresh_cache(self, make: str, model: str, year: Optional[int] = None, currency: str = "KES") -> PriceEstimate:
        """Compute an estimate and upsert it into `market_prices` for fast reads elsewhere."""
        estimate = self.estimate(make, model, year=year, currency=currency)
        if self.supabase is not None:
            row = estimate.to_dict()
            self.supabase.table("market_prices").upsert(
                row, on_conflict="make,model,year,currency"
            ).execute()
        return estimate
