# app/modules/valuation/engine.py
# Auto-D Kenya - Valuation Engine v2.5
# ================================================================
# TYPE: MODULE - Production-ready vehicle valuation engine

import logging
import statistics
import time
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union
from collections import Counter, OrderedDict
from functools import lru_cache
import re

from app.core.database import get_supabase

logger = logging.getLogger(__name__)

# ─── RETRY HELPER ──────────────────────────────────────────────────

async def execute_with_retry(
    query,
    max_retries: int = 2,
    delay: float = 0.5
):
    """Execute a Supabase query with retry logic."""
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            # Run the synchronous execute in a thread
            return await asyncio.to_thread(query.execute)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                logger.debug(f"Retry {attempt + 1}/{max_retries} after error: {e}")
    
    raise last_error


class ValuationEngine:
    """
    Production-ready vehicle valuation engine v2.5.
    
    Features:
    - No double depreciation
    - Batch database queries
    - Async thread pooling
    - LRU cache with TTL
    - SQL injection safe
    - Retry logic
    - Lock-free profile loading
    - Performance optimized
    """

    def __init__(self):
        self.supabase = get_supabase()
        
        # ─── Cache ──────────────────────────────────────────────────
        self._variant_cache = OrderedDict()
        self._cache_ttl = 3600  # 1 hour
        self._cache_max_size = 5000
        
        # ─── Profile Cache ─────────────────────────────────────────
        self._location_profiles = {}
        self._dealer_profiles = {}
        self._demand_profiles = {}
        self._profiles_loaded = False
        self._profiles_lock = asyncio.Lock()
        self._profiles_timestamp = 0
        self._profiles_ttl = 86400  # 24 hours
        
        # ─── Fallback Location Factors ─────────────────────────────
        self._location_factors = {
            "nairobi": 1.03,
            "mombasa": 1.02,
            "kisumu": 1.00,
            "nakuru": 0.99,
            "eldoret": 0.98,
            "thika": 1.00,
            "kiambu": 1.01,
            "kajiado": 1.00,
            "machakos": 1.00,
            "meru": 0.98,
            "nyeri": 0.98,
            "embu": 0.97,
            "malindi": 1.00,
            "nanyuki": 1.00,
            "other": 1.00
        }

        # ─── Fallback Dealer Margins ──────────────────────────────
        self._dealer_margins = {
            "toyota": {"dealer": 0.95, "trade": 0.90},
            "lexus": {"dealer": 0.95, "trade": 0.90},
            "honda": {"dealer": 0.94, "trade": 0.89},
            "mazda": {"dealer": 0.94, "trade": 0.89},
            "subaru": {"dealer": 0.93, "trade": 0.88},
            "nissan": {"dealer": 0.94, "trade": 0.89},
            "mitsubishi": {"dealer": 0.93, "trade": 0.88},
            "suzuki": {"dealer": 0.93, "trade": 0.88},
            "volkswagen": {"dealer": 0.92, "trade": 0.87},
            "mercedes": {"dealer": 0.90, "trade": 0.85},
            "bmw": {"dealer": 0.91, "trade": 0.86},
            "audi": {"dealer": 0.91, "trade": 0.86},
            "land_rover": {"dealer": 0.90, "trade": 0.85},
            "ford": {"dealer": 0.93, "trade": 0.88},
            "chevrolet": {"dealer": 0.92, "trade": 0.87},
            "peugeot": {"dealer": 0.91, "trade": 0.86},
            "hyundai": {"dealer": 0.93, "trade": 0.88},
            "kia": {"dealer": 0.93, "trade": 0.88},
            "isuzu": {"dealer": 0.94, "trade": 0.89},
            "volvo": {"dealer": 0.92, "trade": 0.87},
            "porsche": {"dealer": 0.92, "trade": 0.87},
            "other": {"dealer": 0.93, "trade": 0.89}
        }

        # ─── Condition Factors ──────────────────────────────────────
        self._condition_factors = {
            "excellent": 1.02,
            "very_good": 1.01,
            "good": 1.00,
            "fair": 0.96,
            "poor": 0.90
        }

        # ─── Accident Factors ──────────────────────────────────────
        self._accident_factors = {
            "none": 1.00,
            "minor": 0.97,
            "moderate": 0.92,
            "major": 0.85,
            "structural": 0.75,
            "total_loss": 0.60
        }

        # ─── Demand Factors ─────────────────────────────────────────
        self._demand_factors = {
            "very_high": 1.04,
            "high": 1.02,
            "normal": 1.00,
            "low": 0.97,
            "very_low": 0.94
        }

        # ─── Feature Scores ─────────────────────────────────────────
        self._feature_scores = {
            "leather_seats": 0.008,
            "sunroof": 0.005,
            "panoramic_roof": 0.007,
            "navigation": 0.004,
            "alloy_wheels": 0.006,
            "safety_package": 0.010,
            "premium_sound": 0.004,
            "heated_seats": 0.004,
            "ventilated_seats": 0.005,
            "parking_sensors": 0.005,
            "reverse_camera": 0.006,
            "apple_carplay": 0.003,
            "android_auto": 0.003,
            "wireless_carplay": 0.004,
            "adaptive_cruise": 0.008,
            "lane_assist": 0.006,
            "blind_spot_monitor": 0.005,
            "premium_paint": 0.004,
            "360_camera": 0.007,
            "radar": 0.006,
            "tow_package": 0.005,
            "running_boards": 0.003,
            "roof_rack": 0.003,
            "power_tailgate": 0.004,
            "head_up_display": 0.005
        }

        # ─── Recency Weights ───────────────────────────────────────
        self._recency_weights = {
            0: 1.00,      # 0-30 days
            30: 0.95,     # 31-60 days
            60: 0.90,     # 61-90 days
            90: 0.75      # 90+ days
        }

    # ─── PROFILE LOADING ──────────────────────────────────────────

    async def _load_profiles(self):
        """Preload profiles from database with lock to prevent race conditions."""
        # Fast path: check if already loaded (no lock)
        if self._profiles_loaded:
            return
        
        async with self._profiles_lock:
            # Double-check inside lock
            if self._profiles_loaded:
                return
            
            try:
                # Load location profiles
                query = self.supabase.table("location_market_profiles").select("location, factor")
                response = await execute_with_retry(query)
                if response.data:
                    for item in response.data:
                        self._location_profiles[item.get("location", "").lower()] = float(item.get("factor", 1.0))

                # Load dealer margin profiles
                query = self.supabase.table("dealer_margin_profiles").select("make, dealer_margin, trade_margin")
                response = await execute_with_retry(query)
                if response.data:
                    for item in response.data:
                        self._dealer_profiles[item.get("make", "").lower()] = {
                            "dealer": float(item.get("dealer_margin", 0.93)),
                            "trade": float(item.get("trade_margin", 0.89))
                        }

                # Load demand profiles
                query = self.supabase.table("vehicle_market_demand_profiles").select("variant_id, demand_level")
                response = await execute_with_retry(query)
                if response.data:
                    for item in response.data:
                        self._demand_profiles[item.get("variant_id")] = item.get("demand_level", "normal").lower()

                self._profiles_loaded = True
                self._profiles_timestamp = time.time()
                logger.debug(f"Loaded {len(self._location_profiles)} location profiles, "
                           f"{len(self._dealer_profiles)} dealer profiles, "
                           f"{len(self._demand_profiles)} demand profiles")

            except Exception as e:
                logger.warning(f"Error loading profiles: {e}")
                self._profiles_loaded = True  # Don't retry on error

    # ─── TIMEZONE HELPERS ──────────────────────────────────────────

    def _get_now_utc(self) -> datetime:
        """Get current UTC datetime with timezone."""
        return datetime.now(timezone.utc)

    def _get_current_year(self) -> int:
        """Get current year in UTC."""
        return self._get_now_utc().year

    def _parse_datetime_safe(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string safely with timezone handling."""
        if not dt_str:
            return None
        try:
            if isinstance(dt_str, datetime):
                if dt_str.tzinfo is None:
                    dt_str = dt_str.replace(tzinfo=timezone.utc)
                return dt_str
            if dt_str.endswith('Z'):
                dt_str = dt_str[:-1] + '+00:00'
            dt = datetime.fromisoformat(dt_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    def _get_listing_age_days(self, scraped_at: Optional[Union[str, datetime]]) -> Optional[int]:
        """Calculate listing age in days safely."""
        if not scraped_at:
            return None
        
        dt = self._parse_datetime_safe(scraped_at)
        if not dt:
            return None
        
        now = self._get_now_utc()
        age = (now - dt).days
        return max(0, age)

    # ─── LRU CACHE ──────────────────────────────────────────────────

    async def _get_variant_data(self, variant_id: int) -> Optional[Dict[str, Any]]:
        """Get variant data from database with LRU cache and TTL."""
        # Check cache
        if variant_id in self._variant_cache:
            cached_data, timestamp = self._variant_cache[variant_id]
            if time.time() - timestamp < self._cache_ttl:
                return cached_data
            else:
                del self._variant_cache[variant_id]

        try:
            query = self.supabase.table("vehicle_variants").select("*").eq("id", variant_id).single()
            response = await execute_with_retry(query)
            if response.data:
                self._set_cache(variant_id, response.data)
                return response.data

            query = self.supabase.table("vehicle_master_specs").select("*").eq("variant_id", variant_id).single()
            response = await execute_with_retry(query)
            if response.data:
                self._set_cache(variant_id, response.data)
                return response.data

            return None

        except Exception as e:
            logger.error(f"Error getting variant data: {e}")
            return None

    def _set_cache(self, key: int, value: Dict[str, Any]):
        """Set cache with LRU eviction."""
        # Evict oldest if at capacity
        if len(self._variant_cache) >= self._cache_max_size:
            oldest_key = next(iter(self._variant_cache))
            del self._variant_cache[oldest_key]
        
        self._variant_cache[key] = (value, time.time())
        self._variant_cache.move_to_end(key)

    # ─── NORMALIZATION HELPERS ─────────────────────────────────────

    def _normalize_make(self, make: str) -> str:
        """Normalize make name for dictionary lookup."""
        if not make:
            return "other"
        normalized = make.lower().strip().replace(" ", "_")
        if normalized == "land_rover":
            return "land_rover"
        return normalized

    def _clamp_trend_factor(self, trend_percentage: float) -> float:
        """Clamp trend factor to reasonable range."""
        factor = 1.0 + (trend_percentage / 100)
        return max(0.80, min(1.20, factor))

    def _normalize_trim(self, trim: str) -> List[str]:
        """Normalize trim level into tokens for matching."""
        if not trim:
            return []
        # Sanitize: only allow alphanumeric and spaces
        clean = re.sub(r'[^a-zA-Z0-9\s-]', '', trim)
        return clean.lower().replace("-", " ").replace("_", " ").split()

    def _escape_sql_like(self, value: str) -> str:
        """Escape SQL LIKE pattern characters."""
        return value.replace('%', '\\%').replace('_', '\\_')

    # ─── NULL-SAFE INPUT HANDLING ─────────────────────────────────

    def _safe_string(self, value: Optional[str], default: str = "good") -> str:
        """Safely handle string inputs."""
        if value is None:
            return default
        if isinstance(value, str):
            return value.lower().strip() or default
        return default

    def _safe_int(self, value: Optional[Union[int, float]], default: int = 0) -> int:
        """Safely handle integer inputs."""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def _safe_float(self, value: Optional[Union[int, float]], default: float = 0.0) -> float:
        """Safely handle float inputs."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    # ─── DATABASE-DRIVEN FACTORS ──────────────────────────────────

    async def _get_location_factor(self, location: str) -> float:
        """Get location factor from preloaded profiles or fallback."""
        location = self._safe_string(location, "other")
        
        if location in self._location_profiles:
            return self._location_profiles[location]
        
        return self._location_factors.get(location, 1.00)

    async def _get_demand_factor(self, variant_id: int) -> float:
        """Get market demand factor from preloaded profiles."""
        if variant_id in self._demand_profiles:
            demand_level = self._demand_profiles[variant_id]
            return self._demand_factors.get(demand_level, 1.00)

        return 1.00

    async def _get_market_trend_factor(self, variant_id: int, year: int) -> float:
        """Get market trend factor with clamping and ordering."""
        try:
            query = (
                self.supabase
                .table("vehicle_market_history")
                .select("trend_percentage")
                .eq("variant_id", variant_id)
                .eq("year", year)
                .order("created_at", desc=True)
                .limit(1)
            )
            response = await execute_with_retry(query)
            if response.data:
                trend = response.data[0].get("trend_percentage", 0)
                return self._clamp_trend_factor(trend)
        except Exception as e:
            logger.warning(f"Error getting trend factor: {e}")

        return 1.00

    async def _get_dealer_margins(self, make: str) -> Dict[str, float]:
        """Get dealer margins from preloaded profiles or fallback."""
        make = self._normalize_make(make)
        
        if make in self._dealer_profiles:
            return self._dealer_profiles[make]
        
        if make in self._dealer_margins:
            return self._dealer_margins[make]
        
        return self._dealer_margins["other"]

    # ─── IQR OUTLIER DETECTION ────────────────────────────────────

    def _remove_outliers_iqr(self, prices: List[float]) -> List[float]:
        """Remove outliers using statistically correct IQR method."""
        if len(prices) < 4:
            return prices

        sorted_prices = sorted(prices)
        
        try:
            q1, _, q3 = statistics.quantiles(sorted_prices, n=4, method="inclusive")
            iqr = q3 - q1
            
            if iqr == 0:
                return prices
            
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            
            return [p for p in prices if lower <= p <= upper]
            
        except (statistics.StatisticsError, ValueError):
            if len(sorted_prices) < 4:
                return prices
            
            q1_index = len(sorted_prices) // 4
            q3_index = 3 * len(sorted_prices) // 4
            
            q1 = sorted_prices[q1_index]
            q3 = sorted_prices[q3_index]
            iqr = q3 - q1
            
            if iqr == 0:
                return prices
            
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            
            return [p for p in prices if lower <= p <= upper]

    # ─── RECENCY WEIGHT ────────────────────────────────────────────

    def _get_recency_weight(self, age_days: Optional[int]) -> float:
        """Get recency weight based on listing age."""
        if age_days is None:
            return 0.75
        
        if age_days <= 30:
            return 1.00
        elif age_days <= 60:
            return 0.95
        elif age_days <= 90:
            return 0.90
        else:
            return 0.75

    def _calculate_listing_confidence(
        self,
        count: int,
        listings: List[Dict[str, Any]],
        exact_match: bool,
        similarity_score: float = 1.0
    ) -> int:
        """Calculate confidence from listings with similarity."""
        score = 0

        # Listing count (max 30)
        if count >= 50:
            score += 30
        elif count >= 20:
            score += 25
        elif count >= 10:
            score += 20
        elif count >= 5:
            score += 15
        elif count >= 3:
            score += 10
        else:
            score += 5

        # Match quality (20)
        score += 20 if exact_match else 10

        # Year match (20) - already filtered
        score += 20

        # Price consistency (15)
        if len(listings) > 1:
            prices = [l["price"] for l in listings if l.get("price", 0) > 0]
            if len(prices) > 1:
                avg_price = sum(prices) / len(prices)
                if avg_price > 0:
                    try:
                        std_dev = statistics.stdev(prices)
                        cv = std_dev / avg_price
                        if cv < 0.10:
                            score += 15
                        elif cv < 0.20:
                            score += 10
                        else:
                            score += 5
                    except statistics.StatisticsError:
                        score += 5
            else:
                score += 5
        else:
            score += 5

        # Recency (15)
        ages = [l.get("age_days") for l in listings if l.get("age_days") is not None]
        if ages:
            avg_age = sum(ages) / len(ages)
            if avg_age < 30:
                score += 15
            elif avg_age < 60:
                score += 10
            elif avg_age < 90:
                score += 5
        
        # Similarity bonus (5)
        score += int(5 * similarity_score)

        return min(95, max(30, score))

    # ─── RECENCY-ADJUSTED MEDIAN ──────────────────────────────────

    async def _get_recency_adjusted_median(
        self,
        variant_id: int,
        year: int
    ) -> Optional[Dict[str, Any]]:
        """Get recency-adjusted median from market listings."""
        try:
            query = (
                self.supabase
                .table("market_listings")
                .select("price, scraped_at, created_at")
                .eq("variant_id", variant_id)
                .eq("year", year)
                .eq("status", "active")
                .eq("currency", "KES")
                .eq("country", "Kenya")
            )
            response = await execute_with_retry(query)

            if not response.data or len(response.data) < 3:
                return None

            prices_data = []
            for listing in response.data:
                price = listing.get("price")
                if price and float(price) > 0:
                    age_days = self._get_listing_age_days(
                        listing.get("scraped_at") or listing.get("created_at")
                    )
                    weight = self._get_recency_weight(age_days)
                    prices_data.append({
                        "price": float(price),
                        "weight": weight,
                        "age_days": age_days
                    })

            if len(prices_data) < 3:
                return None

            raw_prices = [p["price"] for p in prices_data]
            
            cleaned_prices = self._remove_outliers_iqr(raw_prices)
            
            if len(cleaned_prices) < 3:
                return None

            price_counter = Counter(cleaned_prices)
            filtered_prices = []
            for p in prices_data:
                if p["price"] in price_counter and price_counter[p["price"]] > 0:
                    filtered_prices.append(p)
                    price_counter[p["price"]] -= 1

            if len(filtered_prices) < 3:
                return None

            # Calculate weighted median
            sorted_prices = sorted(filtered_prices, key=lambda x: x["price"])
            total_weight = sum(p["weight"] for p in sorted_prices)
            
            if total_weight == 0:
                return None

            cumulative = 0
            median_weight = total_weight / 2
            
            weighted_median = sorted_prices[-1]["price"]
            for item in sorted_prices:
                cumulative += item["weight"]
                if cumulative >= median_weight:
                    weighted_median = item["price"]
                    break

            confidence = self._calculate_listing_confidence(
                len(filtered_prices),
                filtered_prices,
                True
            )

            return {
                "price": weighted_median,
                "confidence": confidence,
                "count": len(filtered_prices),
                "raw_count": len(response.data)
            }

        except Exception as e:
            logger.warning(f"Error getting recency-adjusted median: {e}")
            return None

    # ─── BATCH MARKET VALUES ──────────────────────────────────────

    async def _batch_get_market_values(
        self,
        variant_ids: List[int],
        year: int
    ) -> Dict[int, float]:
        """Get market values for multiple variants in a single query."""
        if not variant_ids:
            return {}

        try:
            query = (
                self.supabase
                .table("vehicle_market_values")
                .select("variant_id, current_market_value, median_price")
                .eq("year", year)
                .in_("variant_id", variant_ids)
            )
            response = await execute_with_retry(query)
            
            result = {}
            if response.data:
                for item in response.data:
                    vid = item.get("variant_id")
                    value = item.get("current_market_value") or item.get("median_price")
                    if vid and value and float(value) > 0:
                        result[vid] = float(value)
            return result

        except Exception as e:
            logger.warning(f"Batch market values failed: {e}")
            return {}

    # ─── BASE PRICE RETRIEVAL ─────────────────────────────────────

    async def get_base_price(
        self,
        variant_id: int,
        year: int,
        variant_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Determine the best available base price for valuation."""
        start_time = time.perf_counter()
        
        try:
            if not variant_data:
                variant_data = await self._get_variant_data(variant_id)

            # ─── 1. Current Market Value ────────────────────────────
            query = (
                self.supabase
                .table("vehicle_market_values")
                .select("*")
                .eq("variant_id", variant_id)
                .eq("year", year)
                .limit(1)
            )
            response = await execute_with_retry(query)

            if response.data:
                row = response.data[0]
                value = (
                    row.get("current_market_value") or
                    row.get("median_price") or
                    row.get("average_price")
                )
                if value and float(value) > 0:
                    return {
                        "price": float(value),
                        "source": "vehicle_market_values",
                        "confidence": row.get("confidence_score", 95),
                        "listing_count": row.get("listing_count", 0),
                        "is_market_value": True
                    }

            # ─── 2. Vehicle Market Prices ────────────────────────────
            query = (
                self.supabase
                .table("vehicle_market_prices")
                .select("*")
                .eq("variant_id", variant_id)
                .eq("year", year)
                .limit(1)
            )
            response = await execute_with_retry(query)

            if response.data:
                row = response.data[0]
                value = row.get("median_price") or row.get("average_price")
                if value and float(value) > 0:
                    return {
                        "price": float(value),
                        "source": "vehicle_market_prices",
                        "confidence": 90,
                        "listing_count": row.get("listing_count", 0),
                        "is_market_value": True
                    }

            # ─── 3. Market Listings ────────────────────────────────
            listings_result = await self._get_recency_adjusted_median(variant_id, year)
            if listings_result and listings_result.get("price", 0) > 0:
                return {
                    "price": listings_result["price"],
                    "source": "market_listings",
                    "confidence": listings_result.get("confidence", 85),
                    "listing_count": listings_result.get("count", 0),
                    "is_market_value": True
                }

            # ─── 4. Average Scraped Prices ───────────────────────────
            query = (
                self.supabase
                .table("market_prices")
                .select("*")
                .eq("variant_id", variant_id)
                .limit(1)
            )
            response = await execute_with_retry(query)

            if response.data:
                value = response.data[0].get("avg_price")
                if value and float(value) > 0:
                    return {
                        "price": float(value),
                        "source": "market_prices",
                        "confidence": 80,
                        "listing_count": response.data[0].get("listing_count", 0),
                        "is_market_value": True
                    }

            # ─── 5. Variant Base Price ───────────────────────────────
            if variant_data:
                price = variant_data.get("base_price") or variant_data.get("price")
                if price and float(price) > 0:
                    return {
                        "price": float(price),
                        "source": "vehicle_variants",
                        "confidence": 70,
                        "listing_count": 0,
                        "is_market_value": False
                    }

            # ─── 6. Similar Vehicles ──────────────────────────────────
            estimated = await self.estimate_similar_vehicle_price(
                variant_id,
                year,
                variant_data
            )

            if estimated and estimated > 0:
                return {
                    "price": float(estimated),
                    "source": "similar_vehicles",
                    "confidence": 50,
                    "listing_count": 0,
                    "is_market_value": True
                }

            # ─── 7. Default Fallback ──────────────────────────────────
            return {
                "price": 2500000.0,
                "source": "default",
                "confidence": 20,
                "listing_count": 0,
                "is_market_value": False
            }

        finally:
            elapsed = (time.perf_counter() - start_time) * 1000
            if elapsed > 100:
                logger.debug(f"get_base_price took {elapsed:.2f}ms for variant {variant_id}")

    # ─── MARKET VALUE RETRIEVAL ────────────────────────────────────

    async def _get_market_value(
        self,
        variant_id: int,
        year: int,
        variant_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get market value with proper depreciation handling."""
        start_time = time.perf_counter()
        
        try:
            base_result = await self.get_base_price(
                variant_id,
                year,
                variant_data
            )
            
            market_value = base_result["price"]
            is_market_value = base_result.get("is_market_value", False)
            
            # Only apply depreciation if source is NOT a market value
            if not is_market_value:
                age = max(0, self._get_current_year() - year)
                age_factor = self._calculate_age_factor_compound(age)
                market_value *= age_factor
                logger.debug(f"Applied age factor {age_factor:.3f} to {base_result['source']} source")
            
            return {
                "market_value": market_value,
                "source": base_result["source"],
                "confidence": base_result["confidence"],
                "listing_count": base_result["listing_count"],
                "is_market_value": is_market_value
            }
            
        finally:
            elapsed = (time.perf_counter() - start_time) * 1000
            if elapsed > 100:
                logger.debug(f"_get_market_value took {elapsed:.2f}ms for variant {variant_id}")

    # ─── SIMILAR VEHICLE ESTIMATOR ────────────────────────────────

    async def estimate_similar_vehicle_price(
        self,
        variant_id: int,
        year: int,
        variant_data: Optional[Dict[str, Any]] = None
    ) -> Optional[float]:
        """Estimate price from similar vehicles using batch queries."""
        try:
            if not variant_data:
                variant_data = await self._get_variant_data(variant_id)
            
            if not variant_data:
                return None

            make = variant_data.get("make_name", "")
            model = variant_data.get("model_name", "")
            generation_id = variant_data.get("generation_id")
            trim = variant_data.get("trim_level", "")
            engine_cc = variant_data.get("engine_size_cc", 0)
            fuel_type = variant_data.get("fuel_type_name", "")
            transmission = variant_data.get("transmission_type_name", "")
            body_type = variant_data.get("body_type_name", "")

            # ─── 1. Find similar variants ──────────────────────────
            similar_variants = await self._find_similar_variants(
                make=make,
                model=model,
                generation_id=generation_id,
                trim=trim,
                engine_cc=engine_cc,
                fuel_type=fuel_type,
                transmission=transmission
            )

            prices = []
            if similar_variants:
                # Batch fetch market values for all variants at once
                market_values = await self._batch_get_market_values(
                    [v for v in similar_variants if v != variant_id],
                    year
                )
                
                for vid, value in market_values.items():
                    if value > 0:
                        prices.append(value)

            if len(prices) >= 3:
                median_price = statistics.median(prices)
                adjustment = await self._get_variant_adjustment(variant_data)
                return median_price * adjustment

            # ─── 2. By body type ────────────────────────────────────
            if body_type:
                query = (
                    self.supabase
                    .table("vehicle_variants")
                    .select("id")
                    .eq("body_type_name", body_type)
                    .limit(20)
                )
                response = await execute_with_retry(query)
                if response.data:
                    variant_ids = [v.get("id") for v in response.data if v.get("id") != variant_id]
                    if variant_ids:
                        market_values = await self._batch_get_market_values(variant_ids, year)
                        prices = [v for v in market_values.values() if v > 0]
                    if len(prices) >= 3:
                        return statistics.median(prices)

            return None

        except Exception as e:
            logger.exception(f"Similar vehicle estimation failed: {e}")
            return None

    async def _find_similar_variants(
        self,
        make: str = None,
        model: str = None,
        generation_id: int = None,
        trim: str = None,
        engine_cc: int = None,
        fuel_type: str = None,
        transmission: str = None
    ) -> List[int]:
        """Find similar variants safely (SQL injection protected)."""
        try:
            query = self.supabase.table("vehicle_variants").select("id")

            if make:
                query = query.eq("make_name", make)
            if model:
                query = query.eq("model_name", model)
            if generation_id:
                query = query.eq("generation_id", generation_id)
            
            # Trim matching - safe approach using multiple filters
            if trim:
                trim_tokens = self._normalize_trim(trim)
                if trim_tokens:
                    # Use separate eq/ilike filters (safe)
                    for token in trim_tokens:
                        if len(token) > 2:
                            query = query.ilike("trim_level", f"%{token}%")
            
            if engine_cc and engine_cc > 0:
                min_cc = max(0, engine_cc - 200)
                max_cc = engine_cc + 200
                query = query.gte("engine_size_cc", min_cc).lte("engine_size_cc", max_cc)
            if fuel_type:
                query = query.eq("fuel_type_name", fuel_type)
            if transmission:
                query = query.eq("transmission_type_name", transmission)

            response = await execute_with_retry(query.limit(50))
            return [v.get("id") for v in response.data] if response.data else []

        except Exception as e:
            logger.warning(f"Error finding similar variants: {e}")
            return []

    async def _get_variant_adjustment(self, variant_data: Dict[str, Any]) -> float:
        """Calculate adjustment factor for variant differences."""
        adjustment = 1.0

        trim = variant_data.get("trim_level", "")
        trim_tokens = self._normalize_trim(trim)
        
        # FIXED: Proper if/elif/else blocks (syntax error fixed)
        if (
            "base" in trim_tokens
            or "std" in trim_tokens
            or "standard" in trim_tokens
        ):
            adjustment *= 0.92
        elif (
            "vx" in trim_tokens
            or "limited" in trim_tokens
            or "ultimate" in trim_tokens
            or "prestige" in trim_tokens
        ):
            adjustment *= 1.08
        elif (
            "sport" in trim_tokens
            or "rs" in trim_tokens
            or "gt" in trim_tokens
        ):
            adjustment *= 1.05

        engine_size = variant_data.get("engine_size_cc", 0)
        if engine_size > 3000:
            adjustment *= 1.10
        elif engine_size > 2000:
            adjustment *= 1.05
        elif engine_size < 1500:
            adjustment *= 0.95

        fuel = variant_data.get("fuel_type_name", "")
        if fuel == "diesel":
            adjustment *= 1.03
        elif fuel in ["electric", "ev"]:
            adjustment *= 1.08
        elif fuel == "hybrid":
            adjustment *= 1.05

        return round(adjustment, 3)

    # ─── FACTOR CALCULATIONS ──────────────────────────────────────

    def _calculate_age_factor_compound(self, age: int) -> float:
        """Calculate age depreciation using compound rates."""
        if age <= 0:
            return 1.0

        factor = 1.0
        yearly_rates = [0.08, 0.07, 0.06, 0.05, 0.05]

        for year in range(age):
            if year < len(yearly_rates):
                factor *= (1 - yearly_rates[year])
            else:
                factor *= 0.97

        return round(max(factor, 0.35), 3)

    def _calculate_mileage_penalty(self, mileage: int, year: int) -> float:
        """Calculate mileage penalty (no bonus for low mileage)."""
        if mileage <= 0:
            return 1.0

        age = max(1, self._get_current_year() - year)
        expected_mileage = age * 20000
        
        if expected_mileage <= 0:
            return 1.0

        ratio = mileage / expected_mileage

        if ratio <= 1.0:
            return 1.00
        elif ratio <= 1.2:
            return 0.98
        elif ratio <= 1.5:
            return 0.95
        elif ratio <= 2.0:
            return 0.90
        else:
            return 0.85

    def _calculate_feature_score(self, features: Optional[List[str]] = None) -> float:
        """Calculate score for optional features."""
        if not features:
            return 1.00
        
        total_bonus = 0.0
        for feature in features:
            key = feature.lower().replace(" ", "_")
            total_bonus += self._feature_scores.get(key, 0.0)
        
        total_bonus = min(total_bonus, 0.05)
        return 1.00 + total_bonus

    def _calculate_value_range(self, value: float, confidence: int) -> Dict[str, float]:
        """Calculate value range based on confidence."""
        if confidence >= 85:
            spread = 0.05
        elif confidence >= 70:
            spread = 0.08
        elif confidence >= 50:
            spread = 0.12
        else:
            spread = 0.18

        return {
            "minimum": round(value * (1 - spread), 2),
            "maximum": round(value * (1 + spread), 2)
        }

    def _build_summary(
        self,
        base_price: float,
        final_value: float,
        adjustments: List[Dict[str, Any]],
        confidence: int
    ) -> str:
        """Build a human-readable summary with explanations."""
        total_adjustment = final_value - base_price
        
        # Find the dominant adjustment
        dominant = None
        if adjustments:
            # Filter out factors that didn't change
            significant = [a for a in adjustments if a.get("value", 1.0) != 1.0]
            if significant:
                # Sort by absolute deviation
                significant.sort(key=lambda x: abs(x["value"] - 1.0), reverse=True)
                dominant = significant[0]["factor"] if significant else None
        
        # Build explanation
        if dominant:
            factor_names = {
                "mileage": "mileage adjustment",
                "condition": "condition",
                "accident": "accident history",
                "location": "location",
                "demand": "market demand",
                "trend": "market trend",
                "features": "optional features",
                "age": "age depreciation"
            }
            name = factor_names.get(dominant, dominant)
            
            if total_adjustment > 1000:
                summary = f"Value adjusted +{abs(total_adjustment):,.0f} KES primarily due to {name}"
            elif total_adjustment < -1000:
                summary = f"Value adjusted -{abs(total_adjustment):,.0f} KES primarily due to {name}"
            else:
                summary = "Value aligns with market base"
        else:
            if total_adjustment > 1000:
                summary = f"Value adjusted +{abs(total_adjustment):,.0f} KES from market base"
            elif total_adjustment < -1000:
                summary = f"Value adjusted -{abs(total_adjustment):,.0f} KES from market base"
            else:
                summary = "Value aligns with market base"
        
        # Add confidence note
        if confidence >= 85:
            summary += " (High confidence)"
        elif confidence >= 70:
            summary += " (Good confidence)"
        elif confidence >= 50:
            summary += " (Moderate confidence)"
        else:
            summary += " (Indicative estimate)"
        
        return summary

    # ─── MAIN CALCULATION ──────────────────────────────────────────

    async def calculate(
        self,
        variant_id: int,
        year: int,
        mileage: int,
        condition: str = "good",
        accident_history: str = "none",
        location: str = "nairobi",
        variant_data: Optional[Dict] = None,
        features: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Calculate vehicle valuation using market-driven approach.
        
        IMPORTANT: Age depreciation is applied ONLY ONCE in _get_market_value()
        for non-market sources. calculate() does NOT apply age depreciation again.
        """
        start_time = time.perf_counter()
        
        try:
            # ─── Load profiles ──────────────────────────────────────
            await self._load_profiles()

            # ─── Safe input handling ──────────────────────────────
            condition = self._safe_string(condition, "good")
            accident_history = self._safe_string(accident_history, "none")
            location = self._safe_string(location, "nairobi")
            mileage = self._safe_int(mileage, 0)
            year = self._safe_int(year, 2020)
            
            # Validate year
            current_year = self._get_current_year()
            if year < 1980 or year > current_year:
                year = 2020
                logger.warning(f"Invalid year, defaulting to {year}")
            
            # Validate mileage
            if mileage < 0 or mileage > 1000000:
                mileage = 50000
                logger.warning(f"Invalid mileage, defaulting to {mileage}")

            # ─── Get variant data ──────────────────────────────────
            if not variant_data:
                variant_data = await self._get_variant_data(variant_id)

            if not variant_data:
                logger.error(f"No variant data found for ID {variant_id}")
                raise ValueError(f"Variant {variant_id} not found")

            make = variant_data.get("make_name", "")

            # ─── Get market value (age depreciation applied here) ──
            market_result = await self._get_market_value(
                variant_id,
                year,
                variant_data
            )

            base_price = market_result["market_value"]
            listing_count = market_result.get("listing_count", 0)
            confidence = market_result.get("confidence", 75)
            is_market_value = market_result.get("is_market_value", False)

            logger.debug(f"Base market value: {base_price:,.0f} (source: {market_result['source']}, listings: {listing_count})")

            # ─── Apply adjustments ──────────────────────────────────
            estimated_value = base_price

            # Age factor is already applied in _get_market_value for non-market sources
            # Use 1.0 here to avoid double depreciation
            age_factor = 1.0

            mileage_factor = self._calculate_mileage_penalty(mileage, year)
            estimated_value *= mileage_factor

            condition_factor = self._condition_factors.get(condition, 1.00)
            estimated_value *= condition_factor

            accident_factor = self._accident_factors.get(accident_history, 1.00)
            estimated_value *= accident_factor

            location_factor = await self._get_location_factor(location)
            estimated_value *= location_factor

            demand_factor = await self._get_demand_factor(variant_id)
            estimated_value *= demand_factor

            trend_factor = await self._get_market_trend_factor(variant_id, year)
            estimated_value *= trend_factor

            feature_factor = self._calculate_feature_score(features)
            estimated_value *= feature_factor

            # ─── Dealer/trade/retail values ──────────────────────────
            margins = await self._get_dealer_margins(make)
            
            dealer_value = estimated_value * margins["dealer"]
            trade_value = estimated_value * margins["trade"]
            retail_value = estimated_value * 1.08

            # ─── Value range ────────────────────────────────────────
            value_range = self._calculate_value_range(estimated_value, confidence)

            # ─── Build adjustments list ─────────────────────────────
            adjustments = []
            
            # Only include age if it was actually applied
            if not is_market_value and age_factor != 1.0:
                adjustments.append({"factor": "age", "value": round(age_factor, 3)})
            
            adjustments.extend([
                {"factor": "mileage", "value": round(mileage_factor, 3)},
                {"factor": "condition", "value": round(condition_factor, 3)},
                {"factor": "accident", "value": round(accident_factor, 3)},
                {"factor": "location", "value": round(location_factor, 3)},
                {"factor": "demand", "value": round(demand_factor, 3)},
                {"factor": "trend", "value": round(trend_factor, 3)},
                {"factor": "features", "value": round(feature_factor, 3)}
            ])

            # ─── Build response ────────────────────────────────────
            response = {
                "variant_id": variant_id,
                "currency": "KES",

                "market_value": round(estimated_value, 2),
                "estimated_vehicle_value": round(estimated_value, 2),
                "retail_value": round(retail_value, 2),
                "trade_value": round(trade_value, 2),
                "dealer_value": round(dealer_value, 2),

                "estimated_value_range": value_range,

                "confidence_score": confidence,
                "listing_count": listing_count,

                "base_price": round(base_price, 2),
                "base_price_source": market_result["source"],
                "is_market_value_source": is_market_value,

                "age_factor": round(age_factor, 3),
                "mileage_factor": round(mileage_factor, 3),
                "condition_factor": round(condition_factor, 3),
                "accident_factor": round(accident_factor, 3),
                "location_factor": round(location_factor, 3),
                "demand_factor": round(demand_factor, 3),
                "trend_factor": round(trend_factor, 3),
                "feature_factor": round(feature_factor, 3),

                "total_factor": round(
                    age_factor * mileage_factor * condition_factor *
                    accident_factor * location_factor * demand_factor *
                    trend_factor * feature_factor, 3
                ),

                "dealer_margin": margins["dealer"],
                "trade_margin": margins["trade"],

                "vehicle": {
                    "variant_id": variant_id,
                    "make": variant_data.get("make_name", ""),
                    "model": variant_data.get("model_name", ""),
                    "variant": variant_data.get("variant_name", ""),
                    "year": year,
                    "mileage": mileage,
                    "condition": condition,
                    "location": location,
                    "fuel_type": variant_data.get("fuel_type_name", ""),
                    "transmission": variant_data.get("transmission_type_name", ""),
                    "engine_size_cc": variant_data.get("engine_size_cc", 0),
                    "body_type": variant_data.get("body_type_name", "")
                },

                "price_explanation": {
                    "base_price": round(base_price, 2),
                    "base_source": market_result["source"],
                    "adjustments": adjustments,
                    "final_value": round(estimated_value, 2),
                    "summary": self._build_summary(
                        base_price,
                        estimated_value,
                        adjustments,
                        confidence
                    )
                }
            }

            # ─── Log performance ───────────────────────────────────
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.debug(f"Valuation completed in {elapsed:.2f}ms for variant {variant_id}")
            
            return response

        except Exception as e:
            logger.exception(f"Valuation calculation failed: {e}")
            raise


# ─── FACTORY FUNCTION ─────────────────────────────────────────────

def get_valuation_engine() -> ValuationEngine:
    """Factory function to get valuation engine instance."""
    return ValuationEngine()
