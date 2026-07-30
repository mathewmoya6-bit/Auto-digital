# app/modules/scraper/service.py
# Auto-D Kenya - Scraper Service
# ================================================================
# TYPE: MODULE - Scraper business logic

import logging
import uuid
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.database import get_supabase
from app.modules.scraper.worker import ScraperWorker
from app.modules.scraper.schemas import ScraperStatusResponse, ScraperSourceResponse

logger = logging.getLogger(__name__)


class ScraperService:
    """Scraper service for managing scraping operations."""
    
    def __init__(self):
        self.supabase = get_supabase()
        self.worker = ScraperWorker()
        self.jobs = {}
        self.status = {
            "is_running": False,
            "last_run": None,
            "current_job": None,
            "sources": {}
        }
    
    async def start_scraper(
        self,
        source: str,
        pages: int = 3,
        limit_per_page: int = 20,
        user_id: Optional[str] = None
    ) -> str:
        """
        Start a scraper job.
        
        Args:
            source: Source to scrape ('all', 'jiji', 'cheki', 'autochek')
            pages: Number of pages to scrape
            limit_per_page: Items per page
            user_id: User who started the job
            
        Returns:
            str: Job ID
        """
        job_id = str(uuid.uuid4())
        
        # Create job record
        try:
            self.supabase.table("scraper_jobs").insert({
                "id": job_id,
                "source": source,
                "pages": pages,
                "limit_per_page": limit_per_page,
                "user_id": user_id,
                "status": "pending",
                "started_at": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Error creating job record: {str(e)}")
        
        # Store in memory
        self.jobs[job_id] = {
            "id": job_id,
            "source": source,
            "status": "pending",
            "started_at": datetime.utcnow().isoformat(),
            "listings_found": 0,
            "listings_saved": 0
        }
        
        return job_id
    
    async def run_scraper_background(
        self,
        job_id: str,
        source: str,
        pages: int = 3,
        limit_per_page: int = 20
    ) -> None:
        """
        Run scraper in background.
        
        Args:
            job_id: Job ID
            source: Source to scrape
            pages: Number of pages
            limit_per_page: Items per page
        """
        try:
            # Update job status
            self.jobs[job_id]["status"] = "running"
            self.status["is_running"] = True
            self.status["current_job"] = job_id
            
            # Update database
            self.supabase.table("scraper_jobs").update({
                "status": "running",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", job_id).execute()
            
            # Run scraper
            result = await self.worker.run(
                source=source,
                pages=pages,
                limit_per_page=limit_per_page
            )
            
            # Update job with results
            self.jobs[job_id]["status"] = "completed"
            self.jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
            self.jobs[job_id]["listings_found"] = result.get("total_found", 0)
            self.jobs[job_id]["listings_saved"] = result.get("total_saved", 0)
            self.jobs[job_id]["result"] = result
            
            self.status["last_run"] = datetime.utcnow().isoformat()
            self.status["is_running"] = False
            self.status["current_job"] = None
            
            # Update database
            self.supabase.table("scraper_jobs").update({
                "status": "completed",
                "listings_found": result.get("total_found", 0),
                "listings_saved": result.get("total_saved", 0),
                "completed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "result": result
            }).eq("id", job_id).execute()
            
            logger.info(f"Scraper job {job_id} completed: {result}")
            
        except Exception as e:
            logger.error(f"Scraper job {job_id} failed: {str(e)}")
            
            self.jobs[job_id]["status"] = "failed"
            self.jobs[job_id]["error"] = str(e)
            self.status["is_running"] = False
            self.status["current_job"] = None
            
            self.supabase.table("scraper_jobs").update({
                "status": "failed",
                "error": str(e),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", job_id).execute()
    
    async def get_status(self) -> ScraperStatusResponse:
        """Get current scraper status."""
        return ScraperStatusResponse(
            is_running=self.status["is_running"],
            last_run=self.status["last_run"],
            current_job=self.status["current_job"],
            jobs=len(self.jobs),
            sources=self.worker.get_sources()
        )
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get specific job status."""
        if job_id in self.jobs:
            return self.jobs[job_id]
        
        # Try to get from database
        try:
            response = self.supabase.table("scraper_jobs").select("*").eq("id", job_id).execute()
            if response.data:
                return response.data[0]
        except Exception:
            pass
        
        return {"error": "Job not found"}
    
    async def get_sources(self) -> ScraperSourceResponse:
        """Get available scraper sources."""
        sources = self.worker.get_sources()
        
        # Get source status from database
        source_status = {}
        for source in sources:
            try:
                count_response = self.supabase.table("market_listings").select("count", count="exact").eq("source", source).execute()
                last_response = self.supabase.table("scraper_jobs").select("*").eq("source", source).order("started_at", desc=True).limit(1).execute()
                
                source_status[source] = {
                    "available": True,
                    "total_listings": count_response.count if count_response else 0,
                    "last_scrape": last_response.data[0]["started_at"] if last_response.data else None,
                    "last_status": last_response.data[0]["status"] if last_response.data else None
                }
            except Exception:
                source_status[source] = {
                    "available": True,
                    "total_listings": 0,
                    "last_scrape": None,
                    "last_status": None
                }
        
        return ScraperSourceResponse(
            sources=sources,
            status=source_status,
            total_sources=len(sources)
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check scraper health."""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "worker": "active",
            "jobs_pending": len([j for j in self.jobs.values() if j.get("status") == "pending"]),
            "jobs_running": len([j for j in self.jobs.values() if j.get("status") == "running"])
        }
    
    async def get_job_history(self, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """Get scraper job history."""
        try:
            response = self.supabase.table("scraper_jobs").select("*").order("started_at", desc=True).range(offset, offset + limit - 1).execute()
            
            count_response = self.supabase.table("scraper_jobs").select("count", count="exact").execute()
            
            return {
                "jobs": response.data if response else [],
                "total": count_response.count if count_response else 0,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            logger.error(f"Error getting job history: {str(e)}")
            return {"jobs": [], "total": 0, "limit": limit, "offset": offset}
