# app/modules/scraper/worker.py
# ================================================================
# Auto-D Kenya - Scraper Worker
# ================================================================

import asyncio
import logging
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.database import get_supabase
from app.scrapers.base_scraper import BaseScraper
from app.scrapers.jiji import JijiScraper
from app.scrapers.cheki import ChekiScraper
from app.scrapers.autochek import AutochekScraper
# BeepBeep scraper commented out until added to database
# from app.scrapers.beepbeep import BeepBeepScraper

logger = logging.getLogger(__name__)


class ScraperWorker:
    """Scraper worker for running scraping jobs."""

    def __init__(self):
        self.supabase = get_supabase()
        
        # Only include scrapers that exist in market_sources table
        self.scrapers = {
            "jiji": JijiScraper(),
            "cheki": ChekiScraper(),
            "autochek": AutochekScraper(),
            # "beepbeep": BeepBeepScraper(),  # Add when market_sources has beepbeep
        }
        self.results = {}
        self._make_cache = {}
        self._model_cache = {}
        self._source_cache = {}

    def get_sources(self) -> List[str]:
        """Get list of available sources."""
        return list(self.scrapers.keys())

    # ─── SOURCE VALIDATION ──────────────────────────────────────────

    async def is_source_enabled(self, source_name: str) -> bool:
        """
        Check if a source is enabled in the database.
        
        Args:
            source_name: Source name
            
        Returns:
            bool: True if enabled, False otherwise
        """
        try:
            response = (
                self.supabase
                .table("market_sources")
                .select("enabled")
                .eq("name", source_name)
                .single()
                .execute()
            )
            
            if response.data:
                return response.data.get("enabled", True)
            return False
            
        except Exception as e:
            logger.error(f"Error checking source {source_name}: {str(e)}")
            return False

    async def get_source_id(self, source_name: str) -> Optional[int]:
        """
        Get source ID by name.
        
        Args:
            source_name: Source name
            
        Returns:
            Optional[int]: Source ID or None
        """
        try:
            response = (
                self.supabase
                .table("market_sources")
                .select("id")
                .eq("name", source_name)
                .single()
                .execute()
            )
            
            if response.data:
                return response.data.get("id")
            return None
            
        except Exception as e:
            logger.error(f"Error getting source ID for {source_name}: {str(e)}")
            return None

    # ─── MAKE/MODEL MAPPING ─────────────────────────────────────────

    async def get_make_id(self, make_name: str) -> Optional[int]:
        """
        Get make ID by name with caching.
        
        Args:
            make_name: Make name
            
        Returns:
            Optional[int]: Make ID or None
        """
        if not make_name:
            return None
            
        make_name = make_name.strip().title()
        
        # Check cache
        if make_name in self._make_cache:
            return self._make_cache[make_name]
        
        try:
            # Try to find existing make
            response = (
                self.supabase
                .table("vehicle_makes")
                .select("id")
                .eq("name", make_name)
                .single()
                .execute()
            )
            
            if response.data:
                make_id = response.data.get("id")
                self._make_cache[make_name] = make_id
                return make_id
            
            # Create new make if not found
            insert_response = (
                self.supabase
                .table("vehicle_makes")
                .insert({"name": make_name, "created_at": datetime.utcnow().isoformat()})
                .execute()
            )
            
            if insert_response.data:
                make_id = insert_response.data[0].get("id")
                self._make_cache[make_name] = make_id
                logger.info(f"Created new make: {make_name} (ID: {make_id})")
                return make_id
                
        except Exception as e:
            logger.error(f"Error getting make ID for {make_name}: {str(e)}")
        
        return None

    async def get_model_id(self, model_name: str, make_id: int) -> Optional[int]:
        """
        Get model ID by name and make ID with caching.
        
        Args:
            model_name: Model name
            make_id: Make ID
            
        Returns:
            Optional[int]: Model ID or None
        """
        if not model_name or not make_id:
            return None
            
        model_name = model_name.strip().title()
        cache_key = f"{make_id}_{model_name}"
        
        # Check cache
        if cache_key in self._model_cache:
            return self._model_cache[cache_key]
        
        try:
            # Try to find existing model
            response = (
                self.supabase
                .table("vehicle_models")
                .select("id")
                .eq("make_id", make_id)
                .eq("name", model_name)
                .single()
                .execute()
            )
            
            if response.data:
                model_id = response.data.get("id")
                self._model_cache[cache_key] = model_id
                return model_id
            
            # Create new model if not found
            insert_response = (
                self.supabase
                .table("vehicle_models")
                .insert({
                    "make_id": make_id,
                    "name": model_name,
                    "created_at": datetime.utcnow().isoformat()
                })
                .execute()
            )
            
            if insert_response.data:
                model_id = insert_response.data[0].get("id")
                self._model_cache[cache_key] = model_id
                logger.info(f"Created new model: {model_name} (ID: {model_id})")
                return model_id
                
        except Exception as e:
            logger.error(f"Error getting model ID for {model_name}: {str(e)}")
        
        return None

    # ─── SAVE LISTING ───────────────────────────────────────────────

    async def save_listing(self, listing: Dict[str, Any], source_id: int) -> Optional[int]:
        """
        Save a listing to market_listings table.
        
        Args:
            listing: Listing data from scraper
            source_id: Source ID
            
        Returns:
            Optional[int]: Listing ID if saved, None otherwise
        """
        try:
            # Get or create make and model
            make_name = listing.get("make", "").strip()
            model_name = listing.get("model", "").strip()
            
            make_id = None
            model_id = None
            
            if make_name:
                make_id = await self.get_make_id(make_name)
                
            if make_id and model_name:
                model_id = await self.get_model_id(model_name, make_id)
            
            # Check for duplicate (same source + listing_id)
            listing_id = listing.get("listing_id") or listing.get("id")
            if listing_id:
                duplicate_check = (
                    self.supabase
                    .table("market_listings")
                    .select("id")
                    .eq("source_id", source_id)
                    .eq("listing_id", str(listing_id))
                    .execute()
                )
                
                if duplicate_check.data:
                    # Update existing listing
                    update_data = {
                        "price": listing.get("price"),
                        "mileage": listing.get("mileage"),
                        "year": listing.get("year"),
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    
                    # Only add optional fields if present
                    if listing.get("engine_size"):
                        update_data["engine_size"] = listing.get("engine_size")
                    if listing.get("fuel_type"):
                        update_data["fuel_type"] = listing.get("fuel_type")
                    if listing.get("transmission"):
                        update_data["transmission"] = listing.get("transmission")
                    if listing.get("location"):
                        update_data["location"] = listing.get("location")
                    
                    response = (
                        self.supabase
                        .table("market_listings")
                        .update(update_data)
                        .eq("id", duplicate_check.data[0]["id"])
                        .execute()
                    )
                    
                    if response.data:
                        logger.debug(f"Updated listing {listing_id} from {source_id}")
                        return response.data[0]["id"]
                    return None
            
            # Prepare listing data
            listing_data = {
                "source_id": source_id,
                "listing_id": str(listing_id) if listing_id else None,
                "url": listing.get("url") or listing.get("link", ""),
                "make_id": make_id,
                "model_id": model_id,
                "year": listing.get("year"),
                "price": listing.get("price"),
                "mileage": listing.get("mileage"),
                "engine_size": listing.get("engine_size"),
                "fuel_type": listing.get("fuel_type"),
                "transmission": listing.get("transmission"),
                "location": listing.get("location"),
                "title": listing.get("title", ""),
                "description": listing.get("description"),
                "image_url": listing.get("image_url") or listing.get("image"),
                "scraped_at": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Remove None values
            listing_data = {k: v for k, v in listing_data.items() if v is not None}
            
            # Insert listing
            response = (
                self.supabase
                .table("market_listings")
                .insert(listing_data)
                .execute()
            )
            
            if response.data:
                logger.debug(f"Saved listing {listing_id} from {source_id}")
                return response.data[0]["id"]
            
            return None
            
        except Exception as e:
            logger.error(f"Error saving listing: {str(e)}")
            return None

    # ─── LOGGING ─────────────────────────────────────────────────────

    async def log_job_event(
        self,
        job_id: int,
        event_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a scraper job event.
        
        Args:
            job_id: Job ID
            event_type: Event type (started, page_scraped, listing_found, error, completed)
            message: Log message
            details: Additional details
        """
        try:
            log_data = {
                "job_id": job_id,
                "event_type": event_type,
                "message": message,
                "details": details or {},
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.supabase.table("scraper_job_logs").insert(log_data).execute()
            
        except Exception as e:
            logger.error(f"Error logging job event: {str(e)}")

    # ─── RUN SOURCE ──────────────────────────────────────────────────

    async def run_source(
        self,
        source: str,
        pages: int = 3,
        limit_per_page: int = 20,
        job_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run a single scraper source.
        
        Args:
            source: Source name
            pages: Number of pages to scrape
            limit_per_page: Items per page
            job_id: Optional job ID for logging
            
        Returns:
            Dict[str, Any]: Result
        """
        if source not in self.scrapers:
            return {
                "source": source,
                "status": "failed",
                "error": f"Source '{source}' not found",
            }

        # Check if source is enabled
        if not await self.is_source_enabled(source):
            logger.warning(f"Source '{source}' is disabled in database")
            return {
                "source": source,
                "status": "skipped",
                "error": "Source is disabled in database",
            }

        # Get source ID
        source_id = await self.get_source_id(source)
        if not source_id:
            return {
                "source": source,
                "status": "failed",
                "error": "Source not found in database",
            }

        scraper = self.scrapers[source]
        logger.info(f"Running scraper: {source}")

        # Log job start
        if job_id:
            await self.log_job_event(
                job_id,
                "started",
                f"Starting scraper for {source}",
                {"pages": pages, "limit_per_page": limit_per_page}
            )

        try:
            # Run the scraper
            result = await scraper.run(
                pages=pages,
                limit_per_page=limit_per_page,
            )

            # Extract listings from result
            listings = result.get("listings", [])
            stats = result.get("stats", {})
            
            total_found = len(listings)
            saved_count = 0
            error_count = 0

            # Save each listing
            for i, listing in enumerate(listings):
                try:
                    saved = await self.save_listing(listing, source_id)
                    if saved:
                        saved_count += 1
                        
                        # Log every 10 listings
                        if i % 10 == 0 and job_id:
                            await self.log_job_event(
                                job_id,
                                "listing_found",
                                f"Saved listing {i+1}/{len(listings)}",
                                {"listing": listing.get("title", ""), "price": listing.get("price")}
                            )
                    else:
                        error_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error saving listing: {str(e)}")
                    
                    if job_id:
                        await self.log_job_event(
                            job_id,
                            "error",
                            f"Error saving listing: {str(e)}",
                            {"listing": listing.get("title", "")}
                        )

            self.results[source] = {
                "last_run": datetime.utcnow().isoformat(),
                "result": result,
                "saved_count": saved_count,
                "error_count": error_count,
            }

            # Log completion
            if job_id:
                await self.log_job_event(
                    job_id,
                    "completed",
                    f"Completed scraper for {source}",
                    {
                        "listings_found": total_found,
                        "listings_saved": saved_count,
                        "error_count": error_count,
                        "duration_seconds": stats.get("duration_seconds", 0)
                    }
                )

            return {
                "source": source,
                "status": "success",
                "listings_found": total_found,
                "listings_saved": saved_count,
                "listings_updated": stats.get("updated", 0),
                "error_count": error_count,
                "duration": stats.get("duration_seconds", 0),
                "result": result,
            }

        except Exception as e:
            logger.exception(f"Scraper {source} failed")

            if job_id:
                await self.log_job_event(
                    job_id,
                    "error",
                    f"Scraper failed: {str(e)}",
                    {"error": str(e)}
                )

            return {
                "source": source,
                "status": "failed",
                "error": str(e),
            }

    # ─── RUN ALL ─────────────────────────────────────────────────────

    async def run_all(
        self,
        pages: int = 3,
        limit_per_page: int = 20,
        delay: int = 2,
        job_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run all scraper sources.
        
        Args:
            pages: Number of pages to scrape
            limit_per_page: Items per page
            delay: Delay between sources in seconds
            job_id: Optional job ID for logging
            
        Returns:
            Dict[str, Any]: Results
        """
        results = {}
        total_found = 0
        total_saved = 0
        total_errors = 0

        sources = list(self.scrapers.keys())

        for index, source in enumerate(sources):
            result = await self.run_source(
                source,
                pages,
                limit_per_page,
                job_id
            )

            results[source] = result

            if result["status"] == "success":
                total_found += result.get("listings_found", 0)
                total_saved += result.get("listings_saved", 0)
                total_errors += result.get("error_count", 0)

            if index < len(sources) - 1:
                await asyncio.sleep(delay + random.uniform(0.5, 1.5))

        return {
            "total_found": total_found,
            "total_saved": total_saved,
            "total_errors": total_errors,
            "sources": results,
            "completed_at": datetime.utcnow().isoformat(),
        }

    # ─── RUN ─────────────────────────────────────────────────────────

    async def run(
        self,
        source: str = "all",
        pages: int = 3,
        limit_per_page: int = 20,
        delay: int = 2,
        job_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run scraper.
        
        Args:
            source: Source name or 'all'
            pages: Number of pages to scrape
            limit_per_page: Items per page
            delay: Delay between sources in seconds
            job_id: Optional job ID for logging
            
        Returns:
            Dict[str, Any]: Results
        """
        logger.info(f"Starting scraper for source: {source}, pages: {pages}, limit: {limit_per_page}")

        if source == "all":
            return await self.run_all(
                pages,
                limit_per_page,
                delay,
                job_id
            )

        return await self.run_source(
            source,
            pages,
            limit_per_page,
            job_id
        )

    # ─── CLEANUP ─────────────────────────────────────────────────────

    async def close(self):
        """Close all scraper sessions."""
        for scraper in self.scrapers.values():
            try:
                await scraper.close()
            except Exception as e:
                logger.error(f"Error closing scraper: {str(e)}")
