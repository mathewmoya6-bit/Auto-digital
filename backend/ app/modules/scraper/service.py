# app/modules/scraper/service.py
# Auto-D Kenya - Scraper Service
# ================================================================
# TYPE: MODULE - Scraper business logic

import logging
from typing import List, Dict, Any
from datetime import datetime

from app.core.database import get_supabase
from app.modules.scraper.worker import ScraperWorker

logger = logging.getLogger(__name__)


class ScraperService:
    """Scraper service for managing scraping operations."""
    
    def __init__(self):
        self.supabase = get_supabase()
        self.worker = ScraperWorker()
        self.status = {
            "is_running": False,
            "last_run": None,
            "sources": {}
        }
    
    async def run_scraper(self, source: str = "all") -> Dict[str, Any]:
        """Run the scraper."""
        if self.status["is_running"]:
            return {"message": "Scraper is already running"}
        
        self.status["is_running"] = True
        self.status["last_run"] = datetime.utcnow()
        
        try:
            if source == "all":
                result = await self.worker.run_all()
            else:
                result = await self.worker.run_source(source)
            
            self.status["sources"][source] = {
                "last_run": datetime.utcnow(),
                "result": result
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Scraper error: {str(e)}")
            raise
        finally:
            self.status["is_running"] = False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get scraper status."""
        return self.status
    
    def get_sources(self) -> List[str]:
        """Get available scraper sources."""
        return self.worker.get_sources()
