# backend/app/modules/scraper/worker.py 
import logging from typing import Dict, Any
from app.scrapers.jiji import JijiScraper 
from app.scrapers.cheki import ChekiScraper 
from app.scrapers.autochek import AutochekScraper
from app.scrapers.beepbeep import BeepBeepScraper
logger = logging.getLogger(__name__) 
class ScraperWorker: def __init__(self): self.scrapers = 
  { "jiji": JijiScraper(), 
   "cheki": ChekiScraper(),
   "autochek": AutochekScraper(),
   "beepbeep": BeepBeepScraper(), 
  } async def run(self, source: str, query: str) -> Dict[str, Any]: scraper = self.scrapers.get(source) if not scraper: return { "success": False, "error": f"Unknown source: {source}" } try: results = await scraper.search(query) return { "success": True, "source": source, "results": results, } except Exception as e: logger.exception(f"Scraper failed: {source}") return { "success": False, "source": source, "error": str(e), }
