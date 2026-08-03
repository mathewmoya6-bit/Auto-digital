# app/modules/scraper/worker.py

import logging
from datetime import datetime
from typing import Any, Dict, List

from app.core.database import get_supabase
from app.modules.scraper.vehicle_lookup import VehicleLookup

from app.modules.scraper.jiji import JijiScraper
from app.modules.scraper.cheki import ChekiScraper
from app.modules.scraper.autochek import AutochekScraper
from app.modules.scraper.beepbeep import BeepBeepScraper

logger = logging.getLogger(__name__)


class ScraperWorker:
    """
    Executes marketplace scrapers and persists listings.
    """

    def __init__(self):
        self.supabase = get_supabase()
        self.lookup = VehicleLookup()

        self.scrapers = {
            "jiji": JijiScraper(),
            "cheki": ChekiScraper(),
            "autochek": AutochekScraper(),
            "beepbeep": BeepBeepScraper(),
        }

    # ============================================================
    # SOURCES
    # ============================================================

    def get_sources(self) -> List[str]:
        return list(self.scrapers.keys())

    # ============================================================
    # SAVE LISTING
    # ============================================================

    async def save_listing(
        self,
        source: str,
        listing: Dict[str, Any],
    ) -> bool:
        """
        Save or update a vehicle listing.
        """

        try:

            response = (
                self.supabase
                .table("market_sources")
                .select("id")
                .eq("name", source)
                .limit(1)
                .execute()
            )

            if not response.data:
                logger.error("Unknown source: %s", source)
                return False

            source_id = response.data[0]["id"]

            listing_id = listing.get("listing_id")

            if not listing_id:
                logger.warning("Listing missing listing_id")
                return False

            vehicle = await self.lookup.resolve(
                listing,
                create_missing=False,
            )

            now = datetime.utcnow().isoformat()

            data = {
                "source_id": source_id,
                "listing_id": listing_id,
                "title": listing.get("title"),
                "url": listing.get("url"),
                "price": listing.get("price"),
                "currency": listing.get("currency", "KES"),
                "year": listing.get("year"),

                "make": vehicle["make"],
                "model": vehicle["model"],
                "make_id": vehicle["make_id"],
                "model_id": vehicle["model_id"],

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

                "first_seen": now,
                "last_seen": now,
            }

            (
                self.supabase
                .table("market_listings")
                .upsert(
                    data,
                    on_conflict="source_id,listing_id",
                )
                .execute()
            )

            logger.info(
                "[%s] Saved listing %s",
                source,
                listing_id,
            )

            return True

        except Exception:
            logger.exception(
                "Failed saving listing %s",
                listing.get("listing_id"),
            )
            return False

    # ============================================================
    # RUN SINGLE SOURCE
    # ============================================================

    async def run_source(
        self,
        source: str,
        pages: int = 3,
        limit_per_page: int = 20,
    ) -> Dict[str, Any]:

        scraper = self.scrapers.get(source)

        if scraper is None:
            return {
                "status": "failed",
                "source": source,
                "error": "Unknown scraper",
            }

        logger.info("Running %s scraper", source)

        result = await scraper.run(
            pages=pages,
            limit_per_page=limit_per_page,
        )

        listings = result.get("listings", [])

        saved = 0

        for listing in listings:

            if await self.save_listing(
                source,
                listing,
            ):
                saved += 1

        return {
            "source": source,
            "status": "success",
            "listings_found": len(listings),
            "listings_saved": saved,
            "result": result,
        }

    # ============================================================
    # RUN ALL
    # ============================================================

    async def run_all(
        self,
        pages: int = 3,
        limit_per_page: int = 20,
    ) -> Dict[str, Any]:

        output = {}

        total_found = 0
        total_saved = 0

        for source in self.get_sources():

            try:

                result = await self.run_source(
                    source,
                    pages,
                    limit_per_page,
                )

                output[source] = result

                total_found += result.get(
                    "listings_found",
                    0,
                )

                total_saved += result.get(
                    "listings_saved",
                    0,
                )

            except Exception:

                logger.exception(
                    "%s scraper failed",
                    source,
                )

                output[source] = {
                    "status": "failed",
                    "error": "Scraper crashed",
                }

        return {
            "status": "success",
            "total_found": total_found,
            "total_saved": total_saved,
            "sources": output,
        }

    # ============================================================
    # ENTRY POINT
    # ============================================================

    async def run(
        self,
        source: str = "all",
        pages: int = 3,
        limit_per_page: int = 20,
    ) -> Dict[str, Any]:

        if source == "all":
            return await self.run_all(
                pages,
                limit_per_page,
            )

        return await self.run_source(
            source,
            pages,
            limit_per_page,
        )
