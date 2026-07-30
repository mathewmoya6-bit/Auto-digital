# app/modules/scraper/worker.py
# ================================================================
# Auto-D Kenya - Scraper Worker
# ================================================================

import asyncio
import logging
import random
from datetime import datetime
from typing import Any, Dict, List

from app.scrapers.base_scraper import BaseScraper
from app.scrapers.jiji import JijiScraper
from app.scrapers.cheki import ChekiScraper
from app.scrapers.autochek import AutochekScraper
from app.scrapers.beepbeep import BeepBeepScraper

logger = logging.getLogger(__name__)


class ScraperWorker:
    """Scraper worker for running scraping jobs."""

    def __init__(self):
        self.scrapers = {
            "jiji": JijiScraper(),
            "cheki": ChekiScraper(),
            "autochek": AutochekScraper(),
            "beepbeep": BeepBeepScraper(),
        }
        self.results = {}

    def get_sources(self) -> List[str]:
        return list(self.scrapers.keys())

    async def run_source(
        self,
        source: str,
        pages: int = 3,
        limit_per_page: int = 20,
    ) -> Dict[str, Any]:

        if source not in self.scrapers:
            return {
                "source": source,
                "status": "failed",
                "error": f"Source '{source}' not found",
            }

        scraper = self.scrapers[source]

        logger.info(f"Running scraper: {source}")

        try:
            result = await scraper.run(
                pages=pages,
                limit_per_page=limit_per_page,
            )

            self.results[source] = {
                "last_run": datetime.utcnow().isoformat(),
                "result": result,
            }

            return {
                "source": source,
                "status": "success",
                "listings_found": result.get("stats", {}).get("total_scraped", 0),
                "listings_saved": result.get("stats", {}).get("successful", 0),
                "duration": result.get("stats", {}).get("duration_seconds", 0),
                "result": result,
            }

        except Exception as e:
            logger.exception(f"Scraper {source} failed")

            return {
                "source": source,
                "status": "failed",
                "error": str(e),
            }

    async def run_all(
        self,
        pages: int = 3,
        limit_per_page: int = 20,
        delay: int = 2,
    ) -> Dict[str, Any]:

        results = {}
        total_found = 0
        total_saved = 0

        sources = list(self.scrapers.keys())

        for index, source in enumerate(sources):
            result = await self.run_source(
                source,
                pages,
                limit_per_page,
            )

            results[source] = result

            if result["status"] == "success":
                total_found += result.get("listings_found", 0)
                total_saved += result.get("listings_saved", 0)

            if index < len(sources) - 1:
                await asyncio.sleep(delay + random.uniform(0.5, 1.5))

        return {
            "total_found": total_found,
            "total_saved": total_saved,
            "sources": results,
            "completed_at": datetime.utcnow().isoformat(),
        }

    async def run(
        self,
        source: str = "all",
        pages: int = 3,
        limit_per_page: int = 20,
        delay: int = 2,
    ) -> Dict[str, Any]:

        if source == "all":
            return await self.run_all(
                pages,
                limit_per_page,
                delay,
            )

        return await self.run_source(
            source,
            pages,
            limit_per_page,
        )
