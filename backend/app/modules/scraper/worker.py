# app/modules/scraper/worker.py

import logging
import asyncio
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.database import get_supabase
from app.modules.scraper.vehicle_lookup import VehicleLookup

from app.modules.scraper.jiji import JijiScraper
from app.modules.scraper.cheki import ChekiScraper
from app.modules.scraper.autochek import AutochekScraper
from app.modules.scraper.beepbeep import BeepBeepScraper

logger = logging.getLogger(__name__)


class ScraperWorker:
    """Production-ready scraper worker with batch processing and error recovery"""

    # Valid statuses for runs
    VALID_STATUSES = ("pending", "running", "completed", "failed")

    def __init__(self, batch_size: int = 250, max_concurrent_lookups: int = 20):
        self.supabase = get_supabase()
        self.lookup = VehicleLookup()
        self.batch_size = batch_size
        self.max_concurrent_lookups = max_concurrent_lookups
        self.lookup_semaphore = asyncio.Semaphore(max_concurrent_lookups)
        
        # Minimum percentage of existing listings to consider a successful scrape
        self.MIN_DEACTIVATION_PERCENTAGE = 0.70  # 70% of existing listings must be found
        self.MIN_DEACTIVATION_ABSOLUTE = 50  # At least 50 listings must be found

        # FIX 1: Store scraper CLASSES, not instances
        self.scrapers = {
            "jiji": JijiScraper,
            "cheki": ChekiScraper,
            "autochek": AutochekScraper,
            "beepbeep": BeepBeepScraper,
        }

        # Cache source IDs to avoid repeated queries
        self.source_ids = self._load_source_ids()
        
        # In-memory lock for preventing concurrent runs (single-process only)
        # For multi-process/multi-container, use Redis or PostgreSQL advisory locks
        self._running_sources = set()

    def _load_source_ids(self) -> Dict[str, int]:
        """Cache market source IDs for performance"""
        try:
            result = (
                self.supabase
                .table("market_sources")
                .select("id,name")
                .execute()
            )
            
            source_map = {
                row["name"]: row["id"]
                for row in (result.data or [])
            }
            
            logger.info(f"Loaded {len(source_map)} market sources")
            return source_map
            
        except Exception as e:
            logger.error(f"Failed to load source IDs: {e}")
            return {}

    def _get_source_id(self, source: str) -> Optional[int]:
        """Get cached source ID with fallback refresh"""
        source_id = self.source_ids.get(source)
        
        if not source_id:
            # Attempt to refresh cache
            self.source_ids = self._load_source_ids()
            source_id = self.source_ids.get(source)
            
        return source_id

    def _get_existing_listing_count(self, source_id: int) -> int:
        """Get count of active listings for a source"""
        try:
            result = (
                self.supabase
                .table("market_listings")
                .select("id", count="exact")
                .eq("source_id", source_id)
                .eq("active", True)
                .execute()
            )
            return result.count or 0
        except Exception as e:
            logger.error(f"Failed to get listing count: {e}")
            return 0

    def _create_run_record(self, source: str, run_started: datetime) -> Optional[int]:
        """
        Create a run record.

        Supports both:
        - scraper_runs (new)
        - scraper_jobs (legacy)
        """
        source_id = self._get_source_id(source)

        # Try new table first
        try:
            result = (
                self.supabase
                .table("scraper_runs")
                .insert({
                    "source_id": source_id,
                    "status": "pending",
                    "started_at": run_started.isoformat(),
                })
                .execute()
            )

            if result.data:
                run_id = result.data[0]["id"]
                logger.info(f"Created run record {run_id} in scraper_runs for {source}")
                return run_id

        except Exception as e:
            logger.warning(f"scraper_runs missing or failed: {e}, falling back to scraper_jobs")

        # Fallback to legacy table
        try:
            result = (
                self.supabase
                .table("scraper_jobs")
                .insert({
                    "source_id": source_id,
                    "status": "pending",
                    "started_at": run_started.isoformat(),
                })
                .execute()
            )

            if result.data:
                run_id = result.data[0]["id"]
                logger.info(f"Created run record {run_id} in scraper_jobs for {source}")
                return run_id

        except Exception as e:
            logger.error(f"Failed to create run record in scraper_jobs: {e}")

        logger.error(f"Failed to create run record for {source}")
        return None

    def _update_run_status(
        self,
        run_id: int,
        status: str,
        listings_found: Optional[int] = None,
        listings_saved: Optional[int] = None,
        listings_failed: Optional[int] = None,
        deactivated: Optional[int] = None,
        error: Optional[str] = None
    ):
        """
        Update run status.

        Supports both:
        - scraper_runs (new)
        - scraper_jobs (legacy)
        """
        if not run_id:
            logger.error("Cannot update run with None ID")
            return

        now = datetime.now(timezone.utc)
        payload = {
            "status": status,
            "updated_at": now.isoformat(),
        }

        if listings_found is not None:
            payload["listings_found"] = listings_found

        if listings_saved is not None:
            payload["listings_saved"] = listings_saved

        if listings_failed is not None:
            payload["listings_failed"] = listings_failed

        if deactivated is not None:
            payload["deactivated"] = deactivated

        if error:
            payload["error"] = str(error)[:500]

        if status in ("completed", "failed"):
            payload["completed_at"] = now.isoformat()

        # Try scraper_runs first
        try:
            (
                self.supabase
                .table("scraper_runs")
                .update(payload)
                .eq("id", run_id)
                .execute()
            )
            return
        except Exception as e:
            logger.debug(f"scraper_runs update failed: {e}, trying scraper_jobs")

        # Fallback to scraper_jobs
        try:
            (
                self.supabase
                .table("scraper_jobs")
                .update(payload)
                .eq("id", run_id)
                .execute()
            )
        except Exception as e:
            logger.error(f"Failed to update run {run_id} in both tables: {e}")

    def _deactivate_stale_listings(
        self,
        source_id: int,
        run_started: datetime,
        active_listing_ids: Set[str],
        total_existing: int
    ) -> Tuple[int, bool]:
        """
        Deactivate listings that weren't seen in this scrape.
        
        Only deactivates if we found a reasonable percentage and absolute count.
        Returns (deactivated_count, was_safe)
        """
        if not active_listing_ids:
            logger.warning(f"No active listings for source {source_id}, skipping deactivation")
            return 0, False
        
        # Calculate percentage found
        found_count = len(active_listing_ids)
        found_percentage = found_count / total_existing if total_existing > 0 else 1.0
        
        # Only deactivate if we found enough listings (both percentage AND absolute)
        if found_count < self.MIN_DEACTIVATION_ABSOLUTE:
            logger.warning(
                f"Skipping deactivation for source {source_id}: found {found_count} "
                f"< {self.MIN_DEACTIVATION_ABSOLUTE} minimum absolute threshold"
            )
            return 0, False
            
        if found_percentage < self.MIN_DEACTIVATION_PERCENTAGE:
            logger.warning(
                f"Skipping deactivation for source {source_id}: found {found_count}/{total_existing} "
                f"({found_percentage:.1%}) < {self.MIN_DEACTIVATION_PERCENTAGE:.0%} threshold"
            )
            return 0, False
            
        try:
            # Use last_seen < run_started instead of NOT IN
            result = (
                self.supabase
                .table("market_listings")
                .update({
                    "active": False,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                .eq("source_id", source_id)
                .eq("active", True)
                .lt("last_seen", run_started.isoformat())
                .execute()
            )
            
            deactivated = len(result.data) if result.data else 0
            if deactivated:
                logger.info(
                    f"Deactivated {deactivated} stale listings for source {source_id} "
                    f"({found_count} active found, {found_percentage:.1%} coverage)"
                )
            
            return deactivated, True
            
        except Exception as e:
            logger.error(f"Failed to deactivate stale listings: {e}")
            return 0, False

    def _clean_string_field(self, value: Any, max_length: int = 500) -> Optional[str]:
        """Clean string fields, handling None properly"""
        if value is None:
            return None
        if isinstance(value, str):
            return value[:max_length] if max_length else value
        return str(value)[:max_length] if max_length else str(value)

    def _clean_price(self, price) -> Optional[int]:
        """Clean and validate price - handles KES 1,250,000 format"""
        if not price:
            return None
        try:
            # Remove non-numeric characters except decimal point
            cleaned = re.sub(r"[^\d.]", "", str(price))
            if not cleaned:
                return None
            return int(float(cleaned))
        except (ValueError, TypeError):
            return None

    def _clean_year(self, year) -> Optional[int]:
        """Clean and validate year"""
        if not year:
            return None
        try:
            year = int(year)
            if 1900 <= year <= datetime.now().year + 1:
                return year
            return None
        except (ValueError, TypeError):
            return None

    def _clean_mileage(self, mileage) -> Optional[int]:
        """Clean and validate mileage"""
        if not mileage:
            return None
        try:
            # Remove non-numeric characters
            cleaned = re.sub(r"[^\d]", "", str(mileage))
            if not cleaned:
                return None
            return int(cleaned)
        except (ValueError, TypeError):
            return None

    def _clean_engine_size(self, engine_size) -> Optional[int]:
        """
        Clean and validate engine size
        Handles: 1.5 → 1500, 2.0 → 2000, 1800cc → 1800, 1,800 → 1800
        """
        if not engine_size:
            return None
        try:
            # Remove non-numeric except decimal point
            cleaned = re.sub(r"[^\d.]", "", str(engine_size))
            if not cleaned:
                return None
                
            # Convert to int (cc)
            if "." in cleaned:
                # Handle decimal (1.5L → 1500cc)
                return int(float(cleaned) * 1000)
            else:
                # Handle integer (1800 → 1800cc)
                return int(cleaned)
        except (ValueError, TypeError):
            return None

    async def save_listing(
        self,
        source_id: int,
        listing: Dict[str, Any],
        run_started: datetime,
        batch_timestamp: str
    ) -> Optional[Dict[str, Any]]:
        """Prepare listing for upsert with first_seen preservation via DB trigger"""
        
        # FIX 9: Support multiple ID field names
        listing_id = (
            listing.get("listing_id")
            or listing.get("id")
            or listing.get("uuid")
            or listing.get("slug")
        )
        
        if not listing_id:
            logger.warning(f"Missing listing_id in listing: {listing}")
            return None

        # Use semaphore to limit concurrent vehicle lookups
        async with self.lookup_semaphore:
            try:
                # FIX 4: Increase timeout for vehicle lookup
                vehicle = await asyncio.wait_for(
                    self.lookup.resolve(listing, create_missing=False),
                    timeout=15.0  # Was 5.0 - increased to 15 seconds
                )
            except asyncio.TimeoutError:
                logger.debug(f"Vehicle lookup timeout for {listing_id}")
                vehicle = {}
            except Exception as e:
                logger.debug(f"Vehicle lookup failed for {listing_id}: {e}")
                vehicle = {}

        # FIX 6: Fallback to listing values if vehicle lookup returns nothing
        make = vehicle.get("make") or listing.get("make")
        model = vehicle.get("model") or listing.get("model")
        
        # Clean string fields properly (None stays None)
        title = self._clean_string_field(listing.get("title"), 500)
        url = self._clean_string_field(listing.get("url"))
        seller_name = self._clean_string_field(listing.get("seller_name"), 200)

        # Build payload
        payload = {
            "source_id": source_id,
            "listing_id": listing_id,
            "title": title,
            "url": url,
            "price": self._clean_price(listing.get("price")),
            "currency": self._clean_string_field(listing.get("currency", "KES"), 10) or "KES",
            "make": make,
            "model": model,
            "make_id": vehicle.get("make_id"),
            "model_id": vehicle.get("model_id"),
            "year": self._clean_year(listing.get("year")),
            "mileage": self._clean_mileage(listing.get("mileage")),
            "engine_size": self._clean_engine_size(listing.get("engine_size")),
            "fuel_type": self._clean_string_field(listing.get("fuel_type"), 50),
            "transmission": self._clean_string_field(listing.get("transmission"), 50),
            "body_type": self._clean_string_field(listing.get("body_type"), 50),
            "location": self._clean_string_field(listing.get("location"), 255),
            "seller_name": seller_name,
            "seller_type": self._clean_string_field(listing.get("seller_type"), 50),
            "condition": self._clean_string_field(listing.get("condition"), 50),
            "active": True,
            "first_seen": run_started.isoformat(),
            "last_seen": batch_timestamp,
        }
        
        # FIX 7: Remove None values to avoid constraint violations
        payload = {k: v for k, v in payload.items() if v is not None}
        
        return payload

    async def _process_batch(
        self,
        source_id: int,
        listings: List[Dict[str, Any]],
        run_started: datetime,
        batch_timestamp: str,
        active_listing_ids: Set[str],
        stats: Dict[str, Any]
    ) -> int:
        """Process a batch of listings with parallel vehicle lookups"""
        
        # FIX 3: Skip listings without IDs
        valid_listings = [
            x for x in listings 
            if x.get("listing_id") or x.get("id") or x.get("uuid") or x.get("slug")
        ]
        
        if not valid_listings:
            logger.warning(f"Batch had {len(listings)} listings, but none had valid IDs")
            return 0
        
        # Parallel vehicle lookups with semaphore
        save_tasks = [
            self.save_listing(source_id, listing, run_started, batch_timestamp) 
            for listing in valid_listings
        ]
        results = await asyncio.gather(*save_tasks, return_exceptions=True)
        
        payloads = []
        failed_count = 0
        
        for result in results:
            if isinstance(result, Exception):
                failed_count += 1
                logger.debug(f"Failed to process listing: {result}")
                continue
            if result:
                payloads.append(result)
                active_listing_ids.add(result["listing_id"])
            else:
                failed_count += 1
        
        if payloads:
            try:
                # Batch upsert - Postgres trigger preserves first_seen
                (
                    self.supabase
                    .table("market_listings")
                    .upsert(
                        payloads,
                        on_conflict="source_id,listing_id"
                    )
                    .execute()
                )
                
                stats["listings_saved"] += len(payloads)
                
            except Exception as e:
                logger.error(f"Batch upsert failed: {e}")
                
                # Try binary search to isolate bad records
                await self._retry_with_binary_split(
                    payloads,
                    stats
                )
        
        # Count failed from the save step
        if failed_count:
            stats["listings_failed"] = stats.get("listings_failed", 0) + failed_count
        
        return len(payloads)

    async def _retry_with_binary_split(
        self,
        payloads: List[Dict[str, Any]],
        stats: Dict[str, Any]
    ):
        """Binary search to isolate bad records when batch upsert fails"""
        if len(payloads) == 1:
            # FIX 8: Upsert expects a list, not a dict
            try:
                (
                    self.supabase
                    .table("market_listings")
                    .upsert([payloads[0]], on_conflict="source_id,listing_id")
                    .execute()
                )
                stats["listings_saved"] += 1
            except Exception as e:
                stats["listings_failed"] = stats.get("listings_failed", 0) + 1
                logger.debug(f"Failed to insert listing {payloads[0].get('listing_id')}: {e}")
            return
        
        # Split in half
        mid = len(payloads) // 2
        left = payloads[:mid]
        right = payloads[mid:]
        
        # Try left half
        try:
            (
                self.supabase
                .table("market_listings")
                .upsert(left, on_conflict="source_id,listing_id")
                .execute()
            )
            stats["listings_saved"] += len(left)
        except Exception:
            # Left half failed - recurse
            await self._retry_with_binary_split(left, stats)
        
        # Try right half
        try:
            (
                self.supabase
                .table("market_listings")
                .upsert(right, on_conflict="source_id,listing_id")
                .execute()
            )
            stats["listings_saved"] += len(right)
        except Exception:
            # Right half failed - recurse
            await self._retry_with_binary_split(right, stats)

    # ─── PUBLIC METHODS ──────────────────────────────────────

    async def get_available_sources(self) -> List[str]:
        """Get list of available scraper sources."""
        return list(self.scrapers.keys())

    async def get_valid_statuses(self) -> tuple:
        """Get valid run statuses."""
        return self.VALID_STATUSES

    async def get_source_id(self, source: str) -> Optional[int]:
        """Public async method to get source ID by name with lazy loading."""
        if not self.source_ids:
            self.source_ids = self._load_source_ids()
        return self.source_ids.get(source)

    async def get_dashboard_status(self) -> Dict[str, Any]:
        """
        Get dashboard status with optimized queries.
        Supports both scraper_runs and scraper_jobs.
        """
        status = {
            "pending_count": 0,
            "running_count": 0,
            "completed_count": 0,
            "failed_count": 0,
            "last_status": "idle",
            "last_run": {},
            "sources": list(self.scrapers.keys()),
            "total_listings": 0,
        }

        # Try to get runs from scraper_runs first
        table = "scraper_runs"
        runs = []

        try:
            result = (
                self.supabase
                .table(table)
                .select("*")
                .order("started_at", desc=True)
                .execute()
            )
            runs = result.data or []
        except Exception as e:
            logger.debug(f"scraper_runs query failed: {e}, trying scraper_jobs")
            # Fallback to scraper_jobs
            try:
                table = "scraper_jobs"
                result = (
                    self.supabase
                    .table(table)
                    .select("*")
                    .order("started_at", desc=True)
                    .execute()
                )
                runs = result.data or []
            except Exception as e2:
                logger.error(f"Failed to query both tables: {e2}")

        # Count statuses
        for run in runs:
            s = run.get("status")
            if s == "pending":
                status["pending_count"] += 1
            elif s == "running":
                status["running_count"] += 1
            elif s == "completed":
                status["completed_count"] += 1
            elif s == "failed":
                status["failed_count"] += 1

        if runs:
            status["last_run"] = runs[0]
            status["last_status"] = runs[0].get("status", "idle")

        # Get total listings count
        try:
            listing_count = (
                self.supabase
                .table("market_listings")
                .select("id", count="exact")
                .execute()
            )
            status["total_listings"] = listing_count.count or 0
        except Exception as e:
            logger.warning(f"Failed to count listings: {e}")

        return status

    async def get_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific run by ID. Supports both tables."""
        # Try scraper_runs first
        try:
            result = (
                self.supabase
                .table("scraper_runs")
                .select(
                    """
                    id,
                    source_id,
                    status,
                    started_at,
                    completed_at,
                    updated_at,
                    listings_found,
                    listings_saved,
                    listings_failed,
                    deactivated,
                    error,
                    market_sources (
                        id,
                        name
                    )
                    """
                )
                .eq("id", run_id)
                .single()
                .execute()
            )
            if result.data:
                return result.data
        except Exception as e:
            logger.debug(f"scraper_runs get_run failed: {e}, trying scraper_jobs")

        # Fallback to scraper_jobs
        try:
            result = (
                self.supabase
                .table("scraper_jobs")
                .select(
                    """
                    id,
                    source_id,
                    status,
                    started_at,
                    completed_at,
                    updated_at,
                    listings_found,
                    listings_saved,
                    error
                    """
                )
                .eq("id", run_id)
                .single()
                .execute()
            )
            return result.data if result.data else None
        except Exception as e:
            logger.debug(f"scraper_jobs get_run failed: {e}")

        return None

    async def get_run_history(
        self,
        limit: int = 20,
        offset: int = 0,
        source: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get run history with pagination and filters.
        Supports both tables.
        """
        # Try scraper_runs first
        table = "scraper_runs"
        
        try:
            q = (
                self.supabase
                .table(table)
                .select("*", count="exact")
            )

            if status:
                if status not in self.VALID_STATUSES:
                    return {
                        "runs": [],
                        "total": 0,
                        "limit": limit,
                        "offset": offset,
                        "has_more": False,
                        "error": f"Invalid status '{status}'. Valid: {', '.join(self.VALID_STATUSES)}"
                    }
                q = q.eq("status", status)

            result = (
                q.order("started_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )

            return {
                "runs": result.data or [],
                "total": result.count or 0,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < (result.count or 0),
            }

        except Exception as e:
            logger.debug(f"scraper_runs history failed: {e}, trying scraper_jobs")

        # Fallback to scraper_jobs
        table = "scraper_jobs"
        
        try:
            q = (
                self.supabase
                .table(table)
                .select("*", count="exact")
            )

            if status:
                q = q.eq("status", status)

            result = (
                q.order("started_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )

            return {
                "runs": result.data or [],
                "total": result.count or 0,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < (result.count or 0),
            }

        except Exception as e:
            logger.error(f"Failed to get run history from both tables: {e}")
            return {
                "runs": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "has_more": False,
                "error": str(e),
            }

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for the worker."""
        try:
            # Check database connection
            self.supabase.table("market_sources").select("id").limit(1).execute()
            db_connected = True
            
            # Get listing count
            listings = (
                self.supabase
                .table("market_listings")
                .select("id", count="exact")
                .execute()
            )
            listing_count = listings.count or 0
            
            # Get run count
            run_history = await self.get_run_history(limit=1)
            run_count = run_history.get("total", 0)
            latest_run = run_history.get("runs", [])[0] if run_history.get("runs") else None
            
            return {
                "healthy": True,
                "database_status": "connected" if db_connected else "disconnected",
                "source_count": len(self.scrapers),
                "run_count": run_count,
                "listing_count": listing_count,
                "latest_run": latest_run,
            }
            
        except Exception as e:
            logger.exception("Worker health check failed")
            return {
                "healthy": False,
                "database_status": str(e),
                "source_count": 0,
                "run_count": 0,
                "listing_count": 0,
                "latest_run": None,
                "error": str(e),
            }

    # ─── RUN METHODS ────────────────────────────────────────

    async def run_source(
        self,
        source: str,
        pages: int = 3,
        limit_per_page: int = 20,
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """
        Run a single scraper source - creates its own run record
        """
        # Prevent concurrent runs of the same source (single-process only)
        if source in self._running_sources:
            logger.warning(f"Source {source} already running, skipping")
            return {
                "status": "skipped",
                "source": source,
                "error": "Source already running",
                "run_id": None,
            }
        
        # FIX 11: Check if source IDs are loaded
        if not self.source_ids:
            raise RuntimeError("market_sources table is empty - cannot run scraper")
        
        # FIX 1: Instantiate fresh scraper each run
        scraper_class = self.scrapers.get(source)
        if not scraper_class:
            raise ValueError(f"Unknown scraper: {source}")
        
        scraper = scraper_class()  # Fresh instance each run

        source_id = self._get_source_id(source)
        if not source_id:
            raise ValueError(f"Unknown source ID for: {source}")

        # Acquire lock
        self._running_sources.add(source)
        run_started = datetime.now(timezone.utc)
        
        # Initialize variables for finally block
        run_id = None
        stats = {
            "listings_found": 0,
            "listings_saved": 0,
            "listings_failed": 0,
            "deactivated": 0,
            "status": "pending",
            "error": None,
        }
        
        try:
            # Get existing listing count for deactivation safety
            existing_count = self._get_existing_listing_count(source_id)
            
            # Create run record
            run_id = self._create_run_record(source, run_started)
            
            if not run_id:
                raise RuntimeError(f"Failed to create run record for {source}")
            
            active_listing_ids = set()

            # Mark as running
            self._update_run_status(
                run_id, 
                "running",
                listings_found=0,
                listings_saved=0,
                listings_failed=0
            )
            
            for attempt in range(max_retries + 1):
                try:
                    logger.info(f"[{source}] Starting scrape (run {run_id}, attempt {attempt + 1})")
                    
                    # Dynamic timeout based on pages
                    timeout = max(180, pages * 60)
                    
                    # Run scraper with timeout
                    scrape_start = datetime.now(timezone.utc)
                    result = await asyncio.wait_for(
                        scraper.scrape(
                            pages=pages,
                            limit_per_page=limit_per_page,
                        ),
                        timeout=timeout
                    )
                    scrape_duration = (datetime.now(timezone.utc) - scrape_start).total_seconds()
                    
                    # FIX 2: Validate scraper output
                    if not isinstance(result, dict):
                        raise RuntimeError(
                            f"{source} scraper returned {type(result)} instead of dict"
                        )
                    
                    if "listings" not in result:
                        raise RuntimeError(
                            f"{source} scraper returned no listings key"
                        )
                    
                    listings = result["listings"]
                    
                    if not isinstance(listings, list):
                        raise RuntimeError(
                            f"{source} listings is not a list (got {type(listings)})"
                        )
                    
                    # FIX 10: Log every scrape result
                    logger.info(f"[{source}] Scraper returned {len(listings)} listings")
                    
                    if listings:
                        logger.info(f"[{source}] First listing: {listings[0]}")
                    else:
                        logger.warning(f"[{source}] Scraper returned zero listings - check CSS selectors")
                    
                    stats["listings_found"] = len(listings)
                    
                    logger.info(
                        f"[{source}] Found {len(listings)} listings "
                        f"(scrape took {scrape_duration:.2f}s)"
                    )
                    
                    # Process listings in batches with parallel lookups
                    batch_start = datetime.now(timezone.utc)
                    batch_timestamp = batch_start.isoformat()
                    
                    for i in range(0, len(listings), self.batch_size):
                        batch = listings[i:i + self.batch_size]
                        await self._process_batch(
                            source_id, 
                            batch, 
                            run_started, 
                            batch_timestamp,
                            active_listing_ids, 
                            stats
                        )
                        logger.debug(
                            f"[{source}] Processed batch {i//self.batch_size + 1}, "
                            f"saved {stats['listings_saved']} so far"
                        )
                    batch_duration = (datetime.now(timezone.utc) - batch_start).total_seconds()
                    
                    # Only deactivate if we found enough listings
                    if existing_count > 0:
                        deactivated, was_safe = self._deactivate_stale_listings(
                            source_id,
                            run_started,
                            active_listing_ids,
                            existing_count
                        )
                        stats["deactivated"] = deactivated
                        if not was_safe and deactivated == 0:
                            logger.warning(
                                f"[{source}] Skipped deactivation due to low coverage "
                                f"({len(active_listing_ids)}/{existing_count})"
                            )
                    else:
                        logger.info(f"[{source}] No existing listings to deactivate (first run?)")
                    
                    # Success - break retry loop
                    stats["status"] = "completed"
                    break
                    
                except asyncio.TimeoutError:
                    logger.warning(f"[{source}] Timeout on attempt {attempt + 1}")
                    if attempt >= max_retries:
                        stats["status"] = "failed"
                        stats["error"] = f"Scraper timed out after {max_retries} retries"
                        raise TimeoutError(stats["error"])
                        
                except Exception as e:
                    logger.warning(f"[{source}] Attempt {attempt + 1} failed: {e}")
                    if attempt >= max_retries:
                        stats["status"] = "failed"
                        stats["error"] = str(e)
                        raise
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
                    
        except Exception as e:
            stats["status"] = "failed"
            if not stats["error"]:
                stats["error"] = str(e)
            logger.exception(f"[{source}] Failed: {e}")
        finally:
            # Always update the run record if it was created
            duration = (datetime.now(timezone.utc) - run_started).total_seconds()
            stats["duration_seconds"] = duration
            
            if run_id:
                self._update_run_status(
                    run_id,
                    stats["status"],
                    listings_found=stats["listings_found"],
                    listings_saved=stats["listings_saved"],
                    listings_failed=stats.get("listings_failed", 0),
                    deactivated=stats.get("deactivated", 0),
                    error=stats.get("error")
                )
                
                logger.info(
                    f"[{source}] Run {run_id} completed: {stats['status']} "
                    f"(found: {stats['listings_found']}, saved: {stats['listings_saved']}, "
                    f"failed: {stats.get('listings_failed', 0)}, deactivated: {stats.get('deactivated', 0)})"
                )
            
            # Release lock
            self._running_sources.discard(source)

        return {
            "run_id": run_id,
            "source": source,
            "status": stats["status"],
            "listings_found": stats["listings_found"],
            "listings_saved": stats["listings_saved"],
            "listings_failed": stats.get("listings_failed", 0),
            "deactivated": stats.get("deactivated", 0),
            "duration_seconds": stats.get("duration_seconds", 0),
            "error": stats.get("error"),
        }

    async def run_all(
        self,
        pages: int = 3,
        limit_per_page: int = 20,
        parallel: bool = True,
        max_concurrent: int = 4,
    ) -> Dict[str, Any]:
        """
        Run all scrapers - each gets its own run record
        """
        start_time = datetime.now(timezone.utc)
        results = {}
        total_found = 0
        total_saved = 0
        total_failed = 0
        total_deactivated = 0

        if parallel:
            # Run scrapers in parallel with semaphore
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def run_with_semaphore(source):
                async with semaphore:
                    result = await self.run_source(
                        source,
                        pages=pages,
                        limit_per_page=limit_per_page,
                    )
                return source, result
            
            tasks = [run_with_semaphore(source) for source in self.scrapers.keys()]
            completed = await asyncio.gather(*tasks, return_exceptions=True)
            
            for item in completed:
                if isinstance(item, Exception):
                    logger.error(f"Scraper failed: {item}")
                    continue
                source, result = item
                results[source] = result
                total_found += result.get("listings_found", 0)
                total_saved += result.get("listings_saved", 0)
                total_failed += result.get("listings_failed", 0)
                total_deactivated += result.get("deactivated", 0)
        
        else:
            # Run sequentially
            for source in self.scrapers.keys():
                result = await self.run_source(
                    source,
                    pages=pages,
                    limit_per_page=limit_per_page,
                )
                results[source] = result
                total_found += result.get("listings_found", 0)
                total_saved += result.get("listings_saved", 0)
                total_failed += result.get("listings_failed", 0)
                total_deactivated += result.get("deactivated", 0)

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        sources_run = len(results)
        sources_failed = sum(1 for r in results.values() if r.get("status") == "failed")
        
        # Determine overall status
        if sources_failed == sources_run:
            overall_status = "failed"
        elif sources_failed > 0:
            overall_status = "partial"
        else:
            overall_status = "success"

        return {
            "status": overall_status,
            "results": results,
            "total_found": total_found,
            "total_saved": total_saved,
            "total_failed": total_failed,
            "total_deactivated": total_deactivated,
            "duration_seconds": duration,
            "sources_run": sources_run,
            "sources_failed": sources_failed,
        }

    async def run(
        self,
        source: str = "all",
        pages: int = 3,
        limit_per_page: int = 20,
        parallel: bool = True,
        max_concurrent: int = 4,
    ) -> Dict[str, Any]:
        """
        Public API - run scraper for specific source or all sources
        """
        if source == "all":
            return await self.run_all(
                pages=pages,
                limit_per_page=limit_per_page,
                parallel=parallel,
                max_concurrent=max_concurrent,
            )
        
        return await self.run_source(
            source=source,
            pages=pages,
            limit_per_page=limit_per_page,
        )

    async def recover_stuck_jobs(self, max_age_minutes: int = 60) -> Dict[str, Any]:
        """
        Recover stuck scraper runs (status='running' or 'pending' for too long)
        Supports both scraper_runs and scraper_jobs.
        """
        try:
            now = datetime.now(timezone.utc)
            cutoff = (now - timedelta(minutes=max_age_minutes)).isoformat()
            
            # Try scraper_runs first
            try:
                result = (
                    self.supabase
                    .table("scraper_runs")
                    .select("id, source_id, status, started_at")
                    .in_("status", ["running", "pending"])
                    .lt("started_at", cutoff)
                    .execute()
                )
                stuck_jobs = result.data or []
                table_used = "scraper_runs"
            except Exception as e:
                logger.debug(f"scraper_runs recovery failed: {e}, trying scraper_jobs")
                # Fallback to scraper_jobs
                result = (
                    self.supabase
                    .table("scraper_jobs")
                    .select("id, source_id, status, started_at")
                    .in_("status", ["running", "pending"])
                    .lt("started_at", cutoff)
                    .execute()
                )
                stuck_jobs = result.data or []
                table_used = "scraper_jobs"
            
            if not stuck_jobs:
                return {"status": "success", "recovered": 0, "message": "No stuck jobs found"}
            
            logger.info(f"Found {len(stuck_jobs)} stuck jobs to recover from {table_used}")
            
            recovered = []
            for job in stuck_jobs:
                try:
                    # Mark as failed with updated_at
                    update_payload = {
                        "status": "failed",
                        "error": f"Job recovered after {max_age_minutes} minutes timeout",
                        "completed_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                    }
                    
                    try:
                        (
                            self.supabase
                            .table("scraper_runs")
                            .update(update_payload)
                            .eq("id", job["id"])
                            .execute()
                        )
                    except Exception:
                        # Fallback to scraper_jobs
                        (
                            self.supabase
                            .table("scraper_jobs")
                            .update(update_payload)
                            .eq("id", job["id"])
                            .execute()
                        )
                    
                    recovered.append(job["id"])
                    logger.info(f"Recovered job {job['id']} (source_id: {job['source_id']})")
                    
                except Exception as e:
                    logger.error(f"Failed to recover job {job['id']}: {e}")
            
            return {
                "status": "success",
                "recovered": len(recovered),
                "total_stuck": len(stuck_jobs),
                "recovered_ids": recovered,
                "table_used": table_used,
            }
            
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            return {"status": "failed", "error": str(e)}
