# app/modules/scraper/worker.py
# ================================================================
# Auto-D Kenya - Scraper Worker
# ================================================================

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.core.database import get_supabase

from app.modules.scraper.jiji import JijiScraper
from app.modules.scraper.cheki import ChekiScraper
from app.modules.scraper.autochek import AutochekScraper
from app.modules.scraper.beepbeep import BeepBeepScraper  # Uncommented


logger = logging.getLogger(__name__)


# ─── SCRAPER WORKER ──────────────────────────────────────

class ScraperWorker:
    """
    Orchestrates web scrapers and saves results to database.
    """

    def __init__(self):
        self.supabase = get_supabase()

        # All sources configured
        self.scrapers = {
            "jiji": JijiScraper(),
            "cheki": ChekiScraper(),
            "autochek": AutochekScraper(),
            "beepbeep": BeepBeepScraper(),
        }

    def get_sources(self) -> List[str]:
        """Get list of available scraper sources."""
        return list(self.scrapers.keys())

    # ─── SAVE LISTING ─────────────────────────────────────

    async def save_listing(
        self,
        source: str,
        listing: Dict[str, Any]
    ) -> bool:
        """
        Save a listing to the database with upsert support.
        
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # Get source ID
            source_row = (
                self.supabase
                .table("market_sources")
                .select("id")
                .eq("name", source)
                .execute()
            )

            if not source_row.data:
                logger.error(f"Market source '{source}' not found in database")
                return False

            source_id = source_row.data[0]["id"]

            # Build data object - only include columns that exist
            # Added 'make' and 'model' fields
            data = {
                "source_id": source_id,
                "listing_id": listing.get("listing_id"),
                "url": listing.get("url"),
                "make": listing.get("make"),
                "model": listing.get("model"),
                "year": listing.get("year"),
                "price": listing.get("price"),
                "currency": "KES",
                "mileage": listing.get("mileage"),
                "engine_size": listing.get("engine_size"),
                "fuel_type": listing.get("fuel_type"),
                "transmission": listing.get("transmission"),
                "body_type": listing.get("body_type"),
                "location": listing.get("location"),
                "seller_name": listing.get("seller_name"),
                "seller_type": listing.get("seller_type"),
                "condition": listing.get("condition"),
                "active": True,
                "first_seen": datetime.now(timezone.utc).isoformat(),
                "last_seen": datetime.now(timezone.utc).isoformat(),
            }

            # Remove None values to avoid column mismatch errors
            data = {k: v for k, v in data.items() if v is not None}

            # Use upsert to handle duplicates
            result = (
                self.supabase
                .table("market_listings")
                .upsert(
                    data,
                    on_conflict="listing_id"
                )
                .execute()
            )

            logger.debug(f"Saved listing: {listing.get('listing_id')} from {source}")
            return True

        except Exception as e:
            logger.exception(f"Save listing failed for source {source}: {str(e)}")
            return False

    # ─── RUN SINGLE SOURCE ───────────────────────────────

    async def run_source(
        self,
        source: str,
        pages: int = 3,
        limit_per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Run a single scraper source.
        """
        # Validate source exists
        if source not in self.scrapers:
            logger.error(f"Unknown source: {source}. Available: {list(self.scrapers.keys())}")
            return {
                "status": "failed",
                "source": source,
                "error": f"Unknown source. Available: {list(self.scrapers.keys())}"
            }

        scraper = self.scrapers[source]
        
        logger.info(f"🔄 Running scraper: {source} | pages={pages}, limit={limit_per_page}")

        try:
            result = await scraper.run(pages, limit_per_page)
            
            listings = result.get("listings", [])
            logger.info(f"✅ {source} returned {len(listings)} listings")

            # Save listings to database
            saved = 0
            for listing in listings:
                ok = await self.save_listing(source, listing)
                if ok:
                    saved += 1

            logger.info(f"💾 {source}: {saved}/{len(listings)} listings saved")

            return {
                "source": source,
                "status": "success",
                "listings_found": len(listings),
                "listings_saved": saved,
                "result": result
            }

        except Exception as e:
            logger.exception(f"❌ {source} scraper crashed: {str(e)}")
            return {
                "status": "failed",
                "source": source,
                "error": f"Scraper crashed: {str(e)}"
            }

    # ─── RUN ALL SOURCES ──────────────────────────────────

    async def run_all(
        self,
        pages: int = 3,
        limit_per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Run all configured scrapers.
        """
        logger.info(f"🔄 Running all scrapers | pages={pages}, limit={limit_per_page}")

        output = {}
        total_found = 0
        total_saved = 0

        for source in self.scrapers:
            result = await self.run_source(source, pages, limit_per_page)
            output[source] = result
            total_found += result.get("listings_found", 0)
            total_saved += result.get("listings_saved", 0)

        logger.info(f"✅ All scrapers completed | total_found={total_found}, total_saved={total_saved}")

        return {
            "total_found": total_found,
            "total_saved": total_saved,
            "sources": output
        }

    # ─── RUN ───────────────────────────────────────────────

    async def run(
        self,
        source: str = "all",
        pages: int = 3,
        limit_per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Run scraper for a specific source or all sources.
        
        Args:
            source: Source name or "all"
            pages: Number of pages to scrape
            limit_per_page: Items per page
            
        Returns:
            Dict with scraping results
        """
        if source == "all":
            return await self.run_all(pages, limit_per_page)

        return await self.run_source(source, pages, limit_per_page)
