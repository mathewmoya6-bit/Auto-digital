# app/modules/scraper/worker.py
# Auto-D Kenya - Scraper Worker
# ================================================================
# TYPE: MODULE - Scraper background worker

import logging
from typing import List, Dict, Any

from app.scrapers.base_scraper import BaseScraper
from app.scrapers.jiji_scraper import JijiScraper
from app.scrapers.cheki_scraper import ChekiScraper
from app.scrapers.autochek_scraper import AutochekScraper

logger = logging.getLogger(__name__)


class ScraperWorker:
    """Scraper worker for running scraping jobs."""
    
    def __init__(self):
        self.scrapers = {
            "jiji": JijiScraper(),
            "cheki": ChekiScraper(),
            "autochek": AutochekScraper()
        }
    
    def get_sources(self) -> List[str]:
        """Get available scraper sources."""
        return list(self.scrapers.keys())
    
    async def run_source(self, source: str) -> Dict[str, Any]:
        """Run a specific scraper source."""
        if source not in self.scrapers:
            return {"error": f"Source '{source}' not found"}
        
        scraper = self.scrapers[source]
        logger.info(f"Running scraper: {source}")
        
        try:
            result = await scraper.run()
            return {
                "source": source,
                "status": "success",
                "result": result
            }
        except Exception as e:
            logger.error(f"Scraper {source} failed: {str(e)}")
            return {
                "source": source,
                "status": "failed",
                "error": str(e)
            }
    
    async def run_all(self) -> Dict[str, Any]:
        """Run all scrapers."""
        results = {}
        for source in self.scrapers:
            results[source] = await self.run_source(source)
        return results
