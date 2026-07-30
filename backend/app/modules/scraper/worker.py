# app/modules/scraper/worker.py
# Auto-D Kenya - Scraper Worker
# ================================================================
# TYPE: MODULE - Scraper background worker

import asyncio
import logging
import random
from typing import List, Dict, Any, Optional

from app.scrapers.base_scraper import BaseScraper
from app.scrapers.jiji_scraper import JijiScraper
from app.scrapers.cheki_scraper import ChekiScraper
from app.scrapers.autochek_scraper import AutochekScraper
from app.scrapers.beepbeep_scraper import BeepBeepScraper
from app.scrapers.pigiame_scraper import PigiameScraper

logger = logging.getLogger(__name__)


class ScraperWorker:
    """Scraper worker for running scraping jobs."""
    
    def __init__(self):
        self.scrapers = {
            "jiji": JijiScraper(),
            "cheki": ChekiScraper(),
            "autochek": AutochekScraper(),
            "beepbeep": BeepBeepScraper(),
            "pigiame": PigiameScraper()
        }
        self.results = {}
    
    def get_sources(self) -> List[str]:
        """Get available scraper sources."""
        return list(self.scrapers.keys())
    
    async def run_source(
        self,
        source: str,
        pages: int = 3,
        limit_per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Run a specific scraper source.
        
        Args:
            source: Source name
            pages: Number of pages to scrape
            limit_per_page: Items per page
            
        Returns:
            Dict with results
        """
        if source not in self.scrapers:
            return {
                "source": source,
                "status": "failed",
                "error": f"Source '{source}' not found"
            }
        
        scraper = self.scrapers[source]
        logger.info(f"Running scraper: {source}")
        
        try:
            result = await scraper.run(pages=pages, limit_per_page=limit_per_page)
            
            self.results[source] = {
                "last_run": datetime.utcnow().isoformat(),
                "result": result
            }
            
            return {
                "source": source,
                "status": "success",
                "listings_found": result.get("stats", {}).get("total_scraped", 0),
                "listings_saved": result.get("stats", {}).get("successful", 0),
                "duration": result.get("stats", {}).get("duration_seconds", 0),
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Scraper {source} failed: {str(e)}")
            return {
                "source": source,
                "status": "failed",
                "error": str(e)
            }
    
    async def run_all(
        self,
        pages: int = 3,
        limit_per_page: int = 20,
        delay: int = 2
    ) -> Dict[str, Any]:
        """
        Run all scrapers.
        
        Args:
            pages: Number of pages per scraper
            limit_per_page: Items per page
            delay: Delay between scrapers in seconds
            
        Returns:
            Dict with results
        """
        results = {}
        total_found = 0
        total_saved = 0
        
        for source in self.scrapers:
            result = await self.run_source(source, pages, limit_per_page)
            results[source] = result
            
            if result.get("status") == "success":
                total_found += result.get("listings_found", 0)
                total_saved += result.get("listings_saved", 0)
            
            # Delay between scrapers
            if source != list(self.scrapers.keys())[-1]:
                await asyncio.sleep(delay + random.uniform(0.5, 1.5))
        
        return {
            "total_found": total_found,
            "total_saved": total_saved,
            "sources": results,
            "completed_at": datetime.utcnow().isoformat()
        }
    
    async def run(
        self,
        source: str = "all",
        pages: int = 3,
        limit_per_page: int = 20,
        delay: int = 2
    ) -> Dict[str, Any]:
        """
        Run scraper for source(s).
        
        Args:
            source: 'all' or specific source name
            pages: Number of pages
            limit_per_page: Items per page
            delay: Delay between scrapers
            
        Returns:
            Dict with results
        """
        if source == "all":
            return await self.run_all(pages, limit_per_page, delay)
        else:
            return await self.run_source(source, pages, limit_per_page)
