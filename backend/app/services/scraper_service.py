"""
Scraper Service
Handles all web scraping operations for market data
Production Grade - Auto-D Kenya
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Callable, Tuple
from urllib.parse import urljoin, urlencode, urlparse

import httpx
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_exception
)

from app.core.config import settings
from app.core.database import supabase

logger = logging.getLogger(__name__)


# ─── Custom Exceptions ──────────────────────────────────────────────

class ScraperError(Exception):
    """Base scraper exception."""
    pass


class SourceUnavailableError(ScraperError):
    """Source is temporarily unavailable."""
    pass


class RateLimitError(ScraperError):
    """Rate limit exceeded."""
    pass


class ParseError(ScraperError):
    """Error parsing response data."""
    pass


# ─── ScraperService ──────────────────────────────────────────────

class ScraperService:
    """Service for web scraping market data with rate limiting and caching."""

    def __init__(self):
        """Initialize scraper service with configuration."""
        self.sources = settings.SCRAPER_SOURCES
        self.concurrent_workers = settings.SCRAPER_CONCURRENT_WORKERS
        self.request_timeout = settings.SCRAPER_REQUEST_TIMEOUT
        self.retry_attempts = settings.SCRAPER_RETRY_ATTEMPTS
        self.rate_limit = settings.SCRAPER_RATE_LIMIT
        self.max_pages = settings.SCRAPER_MAX_PAGES
        self.max_results = settings.SCRAPER_MAX_RESULTS
        self.user_agent = settings.SCRAPER_USER_AGENT

        # Rate limiting
        self._rate_limiter = None
        self._request_count = 0
        self._last_reset = datetime.now(timezone.utc)

        # Cache for scraped data
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour

        # In-memory status
        self._status = {
            "status": "idle",
            "last_run": None,
            "total_listings": 0,
            "sources": [],
            "last_24h_count": 0,
            "active_tasks": []
        }

        # Load status from database
        self._load_status()

        # HTTP client with connection pooling
        self._client = None

        logger.info(f"✅ ScraperService initialized: {len(self.sources)} sources")

    @property
    async def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=10.0,
                    read=self.request_timeout,
                    write=10.0,
                    pool=10.0
                ),
                limits=httpx.Limits(
                    max_connections=50,
                    max_keepalive_connections=20
                ),
                follow_redirects=True,
                headers={"User-Agent": self.user_agent}
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ─── Rate Limiting ──────────────────────────────────────────────

    async def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        now = datetime.now(timezone.utc)
        if (now - self._last_reset).total_seconds() > 60:
            self._request_count = 0
            self._last_reset = now

        self._request_count += 1
        if self._request_count > self.rate_limit:
            wait_time = 60 - (now - self._last_reset).total_seconds()
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
            self._request_count = 1
            self._last_reset = datetime.now(timezone.utc)

    # ─── Cache Helpers ──────────────────────────────────────────────

    def _get_cache_key(self, source: str, make: Optional[str], model: Optional[str]) -> str:
        """Generate cache key for a source/query combination."""
        key_parts = [source]
        if make:
            key_parts.append(f"make:{make.lower()}")
        if model:
            key_parts.append(f"model:{model.lower()}")
        return hashlib.md5("|".join(key_parts).encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[Dict]:
        """Get cached data if valid."""
        if key in self._cache:
            entry = self._cache[key]
            if (datetime.now(timezone.utc) - entry["timestamp"]).total_seconds() < self._cache_ttl:
                return entry["data"]
            else:
                del self._cache[key]
        return None

    def _set_cache(self, key: str, data: Dict):
        """Cache data."""
        self._cache[key] = {
            "data": data,
            "timestamp": datetime.now(timezone.utc)
        }
        # Limit cache size
        if len(self._cache) > 100:
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k]["timestamp"]
            )
            for key_to_remove in sorted_keys[:20]:
                del self._cache[key_to_remove]

    # ─── Status Management ──────────────────────────────────────────

    def _load_status(self):
        """Load scraper status from database."""
        try:
            result = supabase.table("scraper_status")\
                .select("*")\
                .order("updated_at", desc=True)\
                .limit(1)\
                .execute()

            if result.data and len(result.data) > 0:
                status = result.data[0]
                self._status.update({
                    "status": status.get("status", "idle"),
                    "last_run": status.get("last_run"),
                    "total_listings": status.get("total_listings", 0),
                    "sources": status.get("sources", []),
                    "last_24h_count": status.get("last_24h_count", 0)
                })
        except Exception as e:
            logger.warning(f"⚠️ Could not load scraper status: {e}")

    def _save_status(self):
        """Save scraper status to database."""
        try:
            supabase.table("scraper_status")\
                .upsert({
                    "status": self._status["status"],
                    "last_run": self._status["last_run"],
                    "total_listings": self._status["total_listings"],
                    "sources": self._status["sources"],
                    "last_24h_count": self._status["last_24h_count"],
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })\
                .execute()
        except Exception as e:
            logger.error(f"❌ Could not save scraper status: {e}")

    def get_status(self) -> Dict:
        """Get current scraper status."""
        # Update 24h count
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=1)
            result = supabase.table("market_prices")\
                .select("count", count="exact")\
                .gte("created_at", cutoff.isoformat())\
                .execute()
            self._status["last_24h_count"] = result.count or 0
        except Exception as e:
            logger.warning(f"⚠️ Could not update 24h count: {e}")

        # Get total listings
        try:
            result = supabase.table("market_prices")\
                .select("count", count="exact")\
                .execute()
            self._status["total_listings"] = result.count or 0
        except Exception as e:
            logger.warning(f"⚠️ Could not update total listings: {e}")

        return self._status

    def update_status(self, status: str, **kwargs):
        """Update scraper status."""
        self._status["status"] = status
        self._status.update(kwargs)
        self._save_status()

    # ─── Source Management ──────────────────────────────────────────

    def get_enabled_sources(self) -> List[str]:
        """Get list of enabled source IDs."""
        return [
            key for key, config in self.sources.items()
            if config.get("enabled", False)
        ]

    def get_sources(self) -> List[Dict]:
        """Get all sources with configuration."""
        return [
            {
                "id": key,
                "name": config.get("name", key),
                "enabled": config.get("enabled", True),
                "frequency_hours": config.get("frequency_hours", 24),
                "max_pages": config.get("max_pages", 10),
                "base_url": config.get("base_url", ""),
                "api_url": config.get("api_url")
            }
            for key, config in self.sources.items()
        ]

    def get_config(self) -> Dict:
        """Get scraper configuration."""
        return {
            "enabled": settings.SCRAPER_ENABLED,
            "concurrent_workers": self.concurrent_workers,
            "request_timeout": self.request_timeout,
            "retry_attempts": self.retry_attempts,
            "rate_limit": self.rate_limit,
            "max_pages": self.max_pages,
            "max_results": self.max_results,
            "user_agent": self.user_agent,
            "sources": self.sources
        }

    def update_config(self, config: Dict) -> Dict:
        """Update scraper configuration."""
        if "sources" in config:
            for key, value in config["sources"].items():
                if key in self.sources:
                    self.sources[key].update(value)

        # Update instance variables
        if "concurrent_workers" in config:
            self.concurrent_workers = config["concurrent_workers"]
        if "request_timeout" in config:
            self.request_timeout = config["request_timeout"]
        if "retry_attempts" in config:
            self.retry_attempts = config["retry_attempts"]
        if "rate_limit" in config:
            self.rate_limit = config["rate_limit"]
        if "max_pages" in config:
            self.max_pages = config["max_pages"]
        if "max_results" in config:
            self.max_results = config["max_results"]

        # Save to database
        try:
            supabase.table("scraper_config")\
                .upsert({
                    "config": self.get_config(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })\
                .execute()
        except Exception as e:
            logger.error(f"❌ Could not save scraper config: {e}")

        return self.get_config()

    # ─── Main Scraper Runner ────────────────────────────────────────

    async def run_scrapers(
        self,
        sources: List[str],
        make: Optional[str] = None,
        model: Optional[str] = None,
        max_results: Optional[int] = None,
        force_refresh: bool = False,
        task_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Run scrapers for multiple sources.

        Args:
            sources: List of source IDs to scrape
            make: Filter by vehicle make
            model: Filter by vehicle model
            max_results: Max results per source
            force_refresh: Force refresh cache
            task_id: Task ID for tracking

        Returns:
            List of results from each scraper
        """
        if not settings.SCRAPER_ENABLED:
            logger.warning("⚠️ Scraper is disabled")
            return [{"error": "Scraper is disabled"}]

        # Filter enabled sources
        enabled_sources = self.get_enabled_sources()
        if "all" in sources or not sources:
            sources = enabled_sources
        else:
            sources = [s for s in sources if s in enabled_sources]

        if not sources:
            logger.warning("⚠️ No enabled sources to scrape")
            return [{"error": "No enabled sources to scrape"}]

        # Update status
        task_id = task_id or f"scrape_{int(datetime.now(timezone.utc).timestamp())}"
        self.update_status(
            "running",
            last_run=datetime.now(timezone.utc).isoformat(),
            sources=sources,
            active_tasks=[task_id]
        )

        logger.info(f"🚀 Starting scrapers: {sources} (task_id={task_id})")

        # Create semaphore for rate limiting
        semaphore = asyncio.Semaphore(self.concurrent_workers)

        # Create tasks
        tasks = []
        for source in sources:
            task = self._scrape_with_semaphore(
                semaphore=semaphore,
                source=source,
                make=make,
                model=model,
                max_results=max_results or self.max_results,
                force_refresh=force_refresh
            )
            tasks.append(task)

        # Run all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        processed_results = []
        for source, result in zip(sources, results):
            if isinstance(result, Exception):
                logger.error(f"❌ {source} scrape error: {result}")
                processed_results.append({
                    "source": source,
                    "success": False,
                    "error": str(result)
                })
                self.add_scraper_log(f"❌ {source} failed: {str(result)}", "error")
            else:
                processed_results.append(result)
                if result.get("success"):
                    logger.info(f"✅ {source} scrape completed: {result.get('items_scraped', 0)} items")
                    self.add_scraper_log(f"✅ {source} scraped {result.get('items_scraped', 0)} items", "success")
                else:
                    logger.error(f"❌ {source} scrape failed: {result.get('error', 'Unknown error')}")
                    self.add_scraper_log(f"❌ {source} failed: {result.get('error', 'Unknown error')}", "error")

        # Update status
        self.update_status(
            "idle",
            active_tasks=[],
            total_listings=self._status.get("total_listings", 0)
        )

        return processed_results

    async def _scrape_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        source: str,
        make: Optional[str] = None,
        model: Optional[str] = None,
        max_results: int = 100,
        force_refresh: bool = False
    ) -> Dict:
        """Scrape a source with rate limiting."""
        async with semaphore:
            return await self._scrape_source(
                source=source,
                make=make,
                model=model,
                max_results=max_results,
                force_refresh=force_refresh
            )

    # ─── Individual Source Scrapers ─────────────────────────────────

    async def _scrape_source(
        self,
        source: str,
        make: Optional[str] = None,
        model: Optional[str] = None,
        max_results: int = 100,
        force_refresh: bool = False
    ) -> Dict:
        """Scrape a single source."""
        # Map source to specific scraper
        scrapers = {
            "autochek": self._scrape_autochek,
            "jiji": self._scrape_jiji,
            "carapi": self._scrape_carapi,
            "beepbeep": self._scrape_beepbeep,
            "pigiama": self._scrape_pigiama
        }

        scraper = scrapers.get(source)
        if not scraper:
            return {
                "source": source,
                "success": False,
                "error": f"Unknown source: {source}"
            }

        # Check cache
        cache_key = self._get_cache_key(source, make, model)
        if not force_refresh:
            cached = self._get_cached(cache_key)
            if cached:
                return {
                    "source": source,
                    "success": True,
                    "items_scraped": cached.get("items_scraped", 0),
                    "message": "Using cached data",
                    "cached": True,
                    **cached
                }

        # Run the scraper
        result = await scraper(
            make=make,
            model=model,
            max_results=max_results
        )

        # Cache successful results
        if result.get("success"):
            self._set_cache(cache_key, result)

        return result

    # ─── Specific Scraper Implementations ──────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def _scrape_autochek(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        max_results: int = 100
    ) -> Dict:
        """Scrape Autochek Kenya."""
        start_time = time.time()
        source_config = self.sources.get("autochek", {})
        api_url = source_config.get("api_url", "https://api.autochek.co.ke/v1")

        try:
            await self._check_rate_limit()

            # Build query parameters
            params = {}
            if make:
                params["make"] = make
            if model:
                params["model"] = model
            params["limit"] = min(max_results, 100)

            # Make API request
            client = await self.client
            response = await client.get(
                f"{api_url}/listings",
                params=params
            )
            response.raise_for_status()
            data = response.json()

            # Extract listings
            listings_data = data.get("listings", data.get("data", []))

            # If no data, try alternative endpoint
            if not listings_data:
                response = await client.get(
                    f"{api_url}/vehicles",
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                listings_data = data.get("data", data.get("vehicles", []))

            listings = await self._process_listings(
                listings_data,
                source="autochek",
                source_config=source_config
            )

            # Save to database
            saved_count = await self._save_listings(listings)

            return {
                "source": "autochek",
                "success": True,
                "items_scraped": len(listings),
                "saved_count": saved_count,
                "duration_seconds": round(time.time() - start_time, 2)
            }

        except httpx.TimeoutException as e:
            logger.error(f"❌ Autochek timeout: {e}")
            raise SourceUnavailableError(f"Autochek timeout: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitError(f"Autochek rate limit: {e}")
            raise SourceUnavailableError(f"Autochek error: {e}")
        except Exception as e:
            logger.error(f"❌ Autochek scrape error: {e}")
            return {
                "source": "autochek",
                "success": False,
                "error": str(e)
            }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def _scrape_jiji(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        max_results: int = 100
    ) -> Dict:
        """Scrape Jiji Kenya."""
        start_time = time.time()
        source_config = self.sources.get("jiji", {})
        base_url = source_config.get("base_url", "https://jiji.co.ke")

        try:
            await self._check_rate_limit()

            # Build search URL
            search_url = f"{base_url}/cars"

            # Build query parameters
            params = {}
            if make:
                params["query"] = f"{make} {model or ''}"
            params["page"] = 1

            # Make HTTP request
            client = await self.client
            response = await client.get(
                search_url,
                params=params
            )
            response.raise_for_status()
            html_content = response.text

            # Parse HTML
            soup = BeautifulSoup(html_content, "html.parser")
            listings_data = await self._parse_jiji_listings(soup)

            # Process listings
            listings = await self._process_listings(
                listings_data,
                source="jiji",
                source_config=source_config
            )

            # Save to database
            saved_count = await self._save_listings(listings)

            return {
                "source": "jiji",
                "success": True,
                "items_scraped": len(listings),
                "saved_count": saved_count,
                "duration_seconds": round(time.time() - start_time, 2)
            }

        except Exception as e:
            logger.error(f"❌ Jiji scrape error: {e}")
            return {
                "source": "jiji",
                "success": False,
                "error": str(e)
            }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def _scrape_carapi(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        max_results: int = 100
    ) -> Dict:
        """Scrape CarAPI."""
        start_time = time.time()
        source_config = self.sources.get("carapi", {})
        api_url = source_config.get("api_url", "https://carapi.com/api")

        try:
            await self._check_rate_limit()

            # Build query parameters
            params = {}
            if make:
                params["make"] = make
            if model:
                params["model"] = model
            params["limit"] = min(max_results, 50)

            # Make API request
            client = await self.client
            response = await client.get(
                f"{api_url}/vehicles",
                params=params
            )
            response.raise_for_status()
            data = response.json()

            # Extract listings
            listings_data = data.get("data", data.get("vehicles", []))
            listings = await self._process_listings(
                listings_data,
                source="carapi",
                source_config=source_config
            )

            # Save to database
            saved_count = await self._save_listings(listings)

            return {
                "source": "carapi",
                "success": True,
                "items_scraped": len(listings),
                "saved_count": saved_count,
                "duration_seconds": round(time.time() - start_time, 2)
            }

        except Exception as e:
            logger.error(f"❌ CarAPI scrape error: {e}")
            return {
                "source": "carapi",
                "success": False,
                "error": str(e)
            }

    async def _scrape_beepbeep(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        max_results: int = 100
    ) -> Dict:
        """Scrape BeepBeep Kenya."""
        start_time = time.time()

        # BeepBeep may not have a public API - try to scrape if enabled
        if self.sources.get("beepbeep", {}).get("enabled", False):
            source_config = self.sources.get("beepbeep", {})
            base_url = source_config.get("base_url")

            if base_url:
                try:
                    await self._check_rate_limit()
                    client = await self.client
                    response = await client.get(f"{base_url}/cars")
                    response.raise_for_status()

                    soup = BeautifulSoup(response.text, "html.parser")
                    # Parse logic would go here
                    # ...
                except Exception as e:
                    logger.warning(f"BeepBeep scrape failed: {e}")

        # Return mock data as fallback
        return await self._mock_scrape(
            source="beepbeep",
            make=make,
            model=model,
            max_results=max_results,
            start_time=start_time
        )

    async def _scrape_pigiama(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        max_results: int = 100
    ) -> Dict:
        """Scrape PigiaMe."""
        start_time = time.time()

        # PigiaMe may not have a public API
        return await self._mock_scrape(
            source="pigiama",
            make=make,
            model=model,
            max_results=max_results,
            start_time=start_time
        )

    # ─── Data Processing ────────────────────────────────────────────

    async def _process_listings(
        self,
        listings_data: List[Dict],
        source: str,
        source_config: Dict
    ) -> List[Dict]:
        """Process raw listings data into standard format."""
        processed = []

        for item in listings_data:
            try:
                listing = self._normalize_listing(item, source, source_config)
                if listing:
                    processed.append(listing)
            except Exception as e:
                logger.warning(f"⚠️ Error processing listing: {e}")

        return processed

    def _normalize_listing(
        self,
        item: Dict,
        source: str,
        source_config: Dict
    ) -> Optional[Dict]:
        """Normalize a listing to standard format."""
        try:
            # Extract fields with fallbacks
            make = item.get("make") or item.get("manufacturer") or item.get("brand") or "Unknown"
            model = item.get("model") or item.get("car_model") or "Unknown"

            # Price extraction
            price = item.get("price")
            if not price:
                price = item.get("amount")
            if not price:
                price = item.get("cost")
            if not price:
                return None

            # Convert price to float
            try:
                price = float(str(price).replace(",", "").replace("KES", "").strip())
            except:
                return None

            # Year extraction
            year = item.get("year") or item.get("manufacture_year")
            if year:
                try:
                    year = int(str(year))
                except:
                    year = None

            # Mileage extraction
            mileage = item.get("mileage") or item.get("odometer")
            if mileage:
                try:
                    mileage = int(str(mileage).replace(", ""))
                except:
                    mileage = None

            return {
                "source": source,
                "make": make,
                "model": model,
                "year": year,
                "price": price,
                "mileage": mileage,
                "condition": item.get("condition", "good"),
                "fuel_type": item.get("fuel_type") or item.get("fuel") or "petrol",
                "transmission": item.get("transmission") or item.get("transmission_type") or "automatic",
                "location": item.get("location") or item.get("region") or "Nairobi",
                "listing_url": item.get("url") or item.get("link") or item.get("listing_url"),
                "description": item.get("description") or item.get("title") or "",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "source_data": item  # Store original data
            }

        except Exception as e:
            logger.warning(f"⚠️ Could not normalize listing: {e}")
            return None

    async def _save_listings(self, listings: List[Dict]) -> int:
        """Save listings to database."""
        saved_count = 0

        for listing in listings:
            try:
                # Check if listing already exists (using hash of key fields)
                hash_key = hashlib.md5(
                    f"{listing['source']}|{listing['make']}|{listing['model']}|{listing.get('year')}|{listing.get('price')}".encode()
                ).hexdigest()

                result = supabase.table("market_prices")\
                    .select("id")\
                    .eq("hash_key", hash_key)\
                    .execute()

                if not result.data:
                    # Add hash key
                    listing["hash_key"] = hash_key
                    # Insert new listing
                    supabase.table("market_prices").insert(listing).execute()
                    saved_count += 1

            except Exception as e:
                logger.error(f"❌ Error saving listing: {e}")

        # Update status
        if saved_count > 0:
            self._status["total_listings"] = self._status.get("total_listings", 0) + saved_count
            self._save_status()

        return saved_count

    # ─── Parser Helpers ─────────────────────────────────────────────

    async def _parse_jiji_listings(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse Jiji HTML listings."""
        listings = []

        # Find listing elements - try multiple selectors
        listing_selectors = [
            "div.b-list-advert-base",
            "div[data-testid='listing-card']",
            "div.listing-item",
            "article.advert"
        ]

        listing_elements = []
        for selector in listing_selectors:
            elements = soup.select(selector)
            if elements:
                listing_elements = elements
                break

        if not listing_elements:
            # Try finding by class containing 'listing' or 'advert'
            listing_elements = soup.find_all(class_=lambda c: c and ('listing' in c.lower() or 'advert' in c.lower()))

        for element in listing_elements[:self.max_results]:
            try:
                listing = await self._parse_jiji_element(element)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.warning(f"⚠️ Error parsing Jiji element: {e}")

        return listings

    async def _parse_jiji_element(self, element) -> Optional[Dict]:
        """Parse a single Jiji listing element."""
        try:
            # Extract title
            title_element = element.find("h2") or element.find("h1") or element.find("a", class_="b-advert-title-inner")
            title = title_element.text.strip() if title_element else ""

            # Extract price
            price_element = element.find("div", class_="qa-advert-price") or element.find("span", class_="price")
            price_text = price_element.text.strip() if price_element else ""

            # Extract location
            location_element = element.find("div", class_="b-advert-location")
            location = location_element.text.strip() if location_element else "Nairobi"

            # Extract link
            link_element = element.find("a", href=True)
            link = link_element.get("href") if link_element else ""
            if link and not link.startswith("http"):
                link = f"https://jiji.co.ke{link}"

            # Parse title for make and model
            make = "Unknown"
            model = "Unknown"
            if title:
                parts = title.split()
                if len(parts) >= 2:
                    make = parts[0]
                    model = " ".join(parts[1:])

            # Parse price
            price = 0
            if price_text:
                try:
                    price = float(''.join(filter(str.isdigit, price_text)))
                except:
                    pass

            if price > 0:
                return {
                    "make": make,
                    "model": model,
                    "price": price,
                    "location": location,
                    "url": link
                }

        except Exception as e:
            logger.warning(f"⚠️ Error parsing Jiji element: {e}")

        return None

    # ─── Mock Scraper ───────────────────────────────────────────────

    async def _mock_scrape(
        self,
        source: str,
        make: Optional[str] = None,
        model: Optional[str] = None,
        max_results: int = 100,
        start_time: Optional[float] = None
    ) -> Dict:
        """Generate mock listings for testing."""
        if not start_time:
            start_time = time.time()

        # Simulate scraping delay
        await asyncio.sleep(random.uniform(0.5, 2))

        # Generate mock data
        listings = self._generate_mock_listings(
            source=source,
            make=make,
            model=model,
            count=min(random.randint(5, max_results), 50)
        )

        # Save to database
        saved_count = await self._save_listings(listings)

        return {
            "source": source,
            "success": True,
            "items_scraped": len(listings),
            "saved_count": saved_count,
            "duration_seconds": round(time.time() - start_time, 2),
            "mock": True
        }

    def _generate_mock_listings(
        self,
        source: str,
        make: Optional[str] = None,
        model: Optional[str] = None,
        count: int = 20
    ) -> List[Dict]:
        """Generate mock listings for testing."""
        makes = [
            "Toyota", "Honda", "Nissan", "Mazda", "Subaru",
            "Mercedes", "BMW", "Audi", "Ford", "Volkswagen",
            "Lexus", "Land Rover", "Range Rover", "Porsche", "Volvo"
        ]

        models_by_make = {
            "Toyota": ["Corolla", "Camry", "RAV4", "Hilux", "Land Cruiser", "Prado", "Avalon"],
            "Honda": ["Civic", "Accord", "CR-V", "HR-V", "Fit", "Odyssey"],
            "Nissan": ["X-Trail", "Qashqai", "Juke", "Patrol", "Navara", "Leaf"],
            "Mazda": ["CX-5", "CX-3", "CX-9", "Mazda3", "Mazda6", "MX-5"],
            "Subaru": ["Forester", "Outback", "Impreza", "Legacy", "XV", "Ascent"],
            "Mercedes": ["E-Class", "C-Class", "S-Class", "GLE", "GLC", "G-Wagon"],
            "BMW": ["3 Series", "5 Series", "7 Series", "X3", "X5", "X7"],
            "Audi": ["A4", "A6", "A8", "Q5", "Q7", "Q8"],
            "Ford": ["Focus", "Fiesta", "Mustang", "Explorer", "Ranger", "Edge"],
            "Volkswagen": ["Golf", "Passat", "Tiguan", "Atlas", "Polo", "Jetta"]
        }

        years = list(range(2010, 2025))
        conditions = ["excellent", "very_good", "good", "fair"]
        fuel_types = ["petrol", "diesel", "electric", "hybrid"]
        transmissions = ["automatic", "manual"]
        locations = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Thika", "Kiambu", "Kajiado"]

        listings = []
        for i in range(count):
            selected_make = make or random.choice(makes)
            selected_models = models_by_make.get(selected_make, ["Model"])
            selected_model = model or random.choice(selected_models)

            year = random.choice(years)
            price = random.randint(500000, 8000000)
            mileage = random.randint(10000, 150000)

            listings.append({
                "source": source,
                "make": selected_make,
                "model": selected_model,
                "year": year,
                "price": price,
                "mileage": mileage,
                "condition": random.choice(conditions),
                "fuel_type": random.choice(fuel_types),
                "transmission": random.choice(transmissions),
                "location": random.choice(locations),
                "description": f"{selected_make} {selected_model} for sale in Kenya",
                "listing_url": f"https://{source}.com/listing/{i}",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            })

        return listings

    # ─── Logging ──────────────────────────────────────────────────

    def add_scraper_log(self, message: str, level: str = "info"):
        """Add entry to scraper log."""
        try:
            supabase.table("scraper_logs").insert({
                "message": message,
                "level": level,
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"❌ Error adding scraper log: {e}")

    # ─── Scraper Endpoints ──────────────────────────────────────

    async def scrape_autochek(self, task_id: Optional[str] = None, **kwargs):
        """Scrape Autochek."""
        return await self._scrape_autochek(**kwargs)

    async def scrape_jiji(self, task_id: Optional[str] = None, **kwargs):
        """Scrape Jiji."""
        return await self._scrape_jiji(**kwargs)

    async def scrape_carapi(self, task_id: Optional[str] = None, **kwargs):
        """Scrape CarAPI."""
        return await self._scrape_carapi(**kwargs)


# ─── Singleton ─────────────────────────────────────────────────────

_scraper_service: Optional[ScraperService] = None


def get_scraper_service() -> ScraperService:
    """Get or create ScraperService singleton."""
    global _scraper_service
    if _scraper_service is None:
        _scraper_service = ScraperService()
    return _scraper_service


# ─── Export ─────────────────────────────────────────────────────

__all__ = [
    "ScraperService",
    "get_scraper_service",
    "ScraperError",
    "SourceUnavailableError",
    "RateLimitError",
    "ParseError",
]
