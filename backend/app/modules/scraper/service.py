# app/modules/scraper/service.py
# Auto-D Kenya - Scraper Service
# ================================================================
# TYPE: MODULE - Scraper business logic

import logging
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
    
    # ─── SOURCE LOOKUP ──────────────────────────────────────────────
    
    async def get_source_id(self, source_name: str) -> Optional[int]:
        """
        Get source ID by source name.
        
        Args:
            source_name: Source name ('jiji', 'cheki', 'autochek')
            
        Returns:
            Optional[int]: Source ID or None if not found
        """
        try:
            response = (
                self.supabase
                .table("market_sources")
                .select("id")
                .eq("name", source_name.lower())
                .single()
                .execute()
            )
            
            if response.data:
                return response.data.get("id")
            return None
            
        except Exception as e:
            logger.error(f"Error getting source ID for {source_name}: {str(e)}")
            return None
    
    async def get_source_name(self, source_id: int) -> Optional[str]:
        """
        Get source name by source ID.
        
        Args:
            source_id: Source ID
            
        Returns:
            Optional[str]: Source name or None if not found
        """
        try:
            response = (
                self.supabase
                .table("market_sources")
                .select("name")
                .eq("id", source_id)
                .single()
                .execute()
            )
            
            if response.data:
                return response.data.get("name")
            return None
            
        except Exception as e:
            logger.error(f"Error getting source name for ID {source_id}: {str(e)}")
            return None
    
    # ─── START SCRAPER ──────────────────────────────────────────────
    
    async def start_scraper(
        self,
        source: str,
        pages: int = 3,
        limit_per_page: int = 20,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start a scraper job.
        
        Args:
            source: Source to scrape ('all', 'jiji', 'cheki', 'autochek')
            pages: Number of pages to scrape
            limit_per_page: Items per page
            user_id: User who started the job
            
        Returns:
            Dict[str, Any]: Job info with job_id
        """
        try:
            # Get source ID
            source_id = None
            if source.lower() != "all":
                source_id = await self.get_source_id(source)
                if source_id is None:
                    raise ValueError(f"Source '{source}' not found in market_sources table")
            
            # Create job record - let PostgreSQL generate the ID
            now = datetime.utcnow().isoformat()
            job_data = {
                "source_id": source_id,
                "status": "pending",
                "started_at": now,
                "pages_scraped": 0,
                "listings_found": 0,
                "listings_saved": 0,
                "listings_updated": 0,
                "duration_seconds": 0,
                "error_count": 0,
                "created_at": now,
                "updated_at": now
            }
            
            # Add user_id if provided
            if user_id:
                job_data["user_id"] = user_id
            
            # Insert job - returns the generated ID
            response = self.supabase.table("scraper_jobs").insert(job_data).execute()
            
            if not response.data:
                raise ValueError("Failed to create scraper job")
            
            job = response.data[0]
            job_id = job.get("id")
            
            # Store in memory
            self.jobs[str(job_id)] = {
                "id": job_id,
                "source": source,
                "source_id": source_id,
                "status": "pending",
                "started_at": now,
                "pages_scraped": 0,
                "listings_found": 0,
                "listings_saved": 0,
                "listings_updated": 0,
                "duration_seconds": 0,
                "error_count": 0
            }
            
            logger.info(f"📊 Created scraper job {job_id} for source: {source}")
            
            return {
                "job_id": job_id,
                "source": source,
                "status": "pending",
                "started_at": now
            }
            
        except Exception as e:
            logger.error(f"Error creating scraper job: {str(e)}")
            raise
    
    # ─── RUN SCRAPER BACKGROUND ──────────────────────────────────────
    
    async def run_scraper_background(
        self,
        job_id: int,
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
        start_time = datetime.utcnow()
        error_count = 0
        listings_found = 0
        listings_saved = 0
        listings_updated = 0
        pages_scraped = 0
        
        try:
            # Get source ID
            source_id = None
            if source.lower() != "all":
                source_id = await self.get_source_id(source)
            
            # Update job status to running
            self.jobs[str(job_id)]["status"] = "running"
            self.status["is_running"] = True
            self.status["current_job"] = job_id
            
            # Update database
            self.supabase.table("scraper_jobs").update({
                "status": "running",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", job_id).execute()
            
            logger.info(f"🔄 Starting scraper job {job_id} for source: {source}")
            
            # Run scraper
            result = await self.worker.run(
                source=source,
                pages=pages,
                limit_per_page=limit_per_page
            )
            
            # Extract results
            listings_found = result.get("total_found", 0)
            listings_saved = result.get("total_saved", 0)
            listings_updated = result.get("total_updated", 0)
            pages_scraped = result.get("pages_scraped", pages)
            error_count = result.get("errors", 0)
            
            # Calculate duration
            end_time = datetime.utcnow()
            duration_seconds = (end_time - start_time).total_seconds()
            
            # Update job with results
            self.jobs[str(job_id)].update({
                "status": "completed",
                "completed_at": end_time.isoformat(),
                "pages_scraped": pages_scraped,
                "listings_found": listings_found,
                "listings_saved": listings_saved,
                "listings_updated": listings_updated,
                "duration_seconds": duration_seconds,
                "error_count": error_count,
                "result": result
            })
            
            self.status["last_run"] = end_time.isoformat()
            self.status["is_running"] = False
            self.status["current_job"] = None
            
            # Update database
            self.supabase.table("scraper_jobs").update({
                "status": "completed",
                "completed_at": end_time.isoformat(),
                "pages_scraped": pages_scraped,
                "listings_found": listings_found,
                "listings_saved": listings_saved,
                "listings_updated": listings_updated,
                "duration_seconds": duration_seconds,
                "error_count": error_count,
                "updated_at": end_time.isoformat(),
                "result": result
            }).eq("id", job_id).execute()
            
            logger.info(f"✅ Scraper job {job_id} completed: {listings_saved} saved, {listings_updated} updated in {duration_seconds:.1f}s")
            
        except Exception as e:
            logger.error(f"❌ Scraper job {job_id} failed: {str(e)}")
            
            # Calculate duration even on failure
            end_time = datetime.utcnow()
            duration_seconds = (end_time - start_time).total_seconds()
            
            self.jobs[str(job_id)].update({
                "status": "failed",
                "error": str(e),
                "completed_at": end_time.isoformat(),
                "duration_seconds": duration_seconds,
                "error_count": error_count + 1,
                "pages_scraped": pages_scraped
            })
            self.status["is_running"] = False
            self.status["current_job"] = None
            
            self.supabase.table("scraper_jobs").update({
                "status": "failed",
                "error": str(e),
                "completed_at": end_time.isoformat(),
                "duration_seconds": duration_seconds,
                "error_count": error_count + 1,
                "pages_scraped": pages_scraped,
                "updated_at": end_time.isoformat()
            }).eq("id", job_id).execute()
    
    # ─── STATUS ──────────────────────────────────────────────────────
    
    async def get_status(self) -> ScraperStatusResponse:
        """Get current scraper status."""
        return ScraperStatusResponse(
            is_running=self.status["is_running"],
            last_run=self.status["last_run"],
            current_job=self.status["current_job"],
            jobs=len(self.jobs),
            sources=self.worker.get_sources()
        )
    
    async def get_job_status(self, job_id: int) -> Dict[str, Any]:
        """
        Get specific job status.
        
        Args:
            job_id: Job ID (int from database)
            
        Returns:
            Dict[str, Any]: Job status
        """
        # Check memory cache first
        if str(job_id) in self.jobs:
            return self.jobs[str(job_id)]
        
        # Try to get from database
        try:
            response = self.supabase.table("scraper_jobs").select("*").eq("id", job_id).execute()
            if response.data:
                job = response.data[0]
                # Add source name if source_id exists
                if job.get("source_id"):
                    source_name = await self.get_source_name(job["source_id"])
                    job["source_name"] = source_name
                return job
        except Exception as e:
            logger.error(f"Error getting job {job_id}: {str(e)}")
        
        return {"error": "Job not found"}
    
    async def get_sources(self) -> ScraperSourceResponse:
        """Get available scraper sources."""
        sources = self.worker.get_sources()
        
        # Get source status from database
        source_status = {}
        for source in sources:
            try:
                # Get source ID
                source_id = await self.get_source_id(source)
                
                if source_id:
                    # Count listings for this source
                    count_response = self.supabase.table("market_listings").select("count", count="exact").eq("source_id", source_id).execute()
                    
                    # Get last scrape
                    last_response = self.supabase.table("scraper_jobs").select("*").eq("source_id", source_id).order("started_at", desc=True).limit(1).execute()
                    
                    source_status[source] = {
                        "available": True,
                        "source_id": source_id,
                        "total_listings": count_response.count if count_response else 0,
                        "last_scrape": last_response.data[0]["started_at"] if last_response.data else None,
                        "last_status": last_response.data[0]["status"] if last_response.data else None,
                        "last_listings_found": last_response.data[0]["listings_found"] if last_response.data else 0,
                        "last_listings_saved": last_response.data[0]["listings_saved"] if last_response.data else 0
                    }
                else:
                    source_status[source] = {
                        "available": True,
                        "total_listings": 0,
                        "last_scrape": None,
                        "last_status": None
                    }
            except Exception as e:
                logger.error(f"Error getting status for source {source}: {str(e)}")
                source_status[source] = {
                    "available": True,
                    "total_listings": 0,
                    "last_scrape": None,
                    "last_status": None,
                    "error": str(e)
                }
        
        return ScraperSourceResponse(
            sources=sources,
            status=source_status,
            total_sources=len(sources)
        )
    
    # ─── HEALTH CHECK ──────────────────────────────────────────────
    
    async def health_check(self) -> Dict[str, Any]:
        """Check scraper health."""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "worker": "active",
            "jobs_pending": len([j for j in self.jobs.values() if j.get("status") == "pending"]),
            "jobs_running": len([j for j in self.jobs.values() if j.get("status") == "running"]),
            "total_jobs": len(self.jobs)
        }
    
    # ─── JOB HISTORY ─────────────────────────────────────────────────
    
    async def get_job_history(self, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        Get scraper job history.
        
        Args:
            limit: Number of jobs to return
            offset: Offset for pagination
            
        Returns:
            Dict[str, Any]: Job history with pagination
        """
        try:
            response = self.supabase.table("scraper_jobs").select("*").order("started_at", desc=True).range(offset, offset + limit - 1).execute()
            
            count_response = self.supabase.table("scraper_jobs").select("count", count="exact").execute()
            
            jobs = response.data if response else []
            
            # Add source names to each job
            for job in jobs:
                if job.get("source_id"):
                    source_name = await self.get_source_name(job["source_id"])
                    job["source_name"] = source_name
            
            return {
                "jobs": jobs,
                "total": count_response.count if count_response else 0,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            logger.error(f"Error getting job history: {str(e)}")
            return {"jobs": [], "total": 0, "limit": limit, "offset": offset}
    
    # ─── SCRAPER STATS ──────────────────────────────────────────────
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get scraper statistics.
        
        Returns:
            Dict[str, Any]: Statistics
        """
        try:
            # Get total listings
            listings_response = self.supabase.table("market_listings").select("count", count="exact").execute()
            total_listings = listings_response.count if listings_response else 0
            
            # Get active sources
            sources_response = self.supabase.table("market_sources").select("id, name, is_active").execute()
            sources = sources_response.data if sources_response else []
            active_sources = len([s for s in sources if s.get("is_active", True)])
            
            # Get recent jobs
            recent_response = self.supabase.table("scraper_jobs").select("*").order("started_at", desc=True).limit(5).execute()
            recent_jobs = recent_response.data if recent_response else []
            
            # Get source breakdown
            source_breakdown = {}
            for source in sources:
                if source.get("is_active", True):
                    count_response = self.supabase.table("market_listings").select("count", count="exact").eq("source_id", source["id"]).execute()
                    source_breakdown[source["name"]] = count_response.count if count_response else 0
            
            return {
                "total_listings": total_listings,
                "active_sources": active_sources,
                "total_sources": len(sources),
                "source_breakdown": source_breakdown,
                "recent_jobs": recent_jobs,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting scraper stats: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
