# app/modules/scraper/service.py

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import HTTPException

from app.core.database import get_supabase
from app.modules.scraper.worker import ScraperWorker

logger = logging.getLogger(__name__)


# ─── CONSTANTS ──────────────────────────────────────────────

VALID_SOURCES = {
    "jiji",
    "cheki",
    "autochek",
    "beepbeep",
}

SOURCE_NAMES = {
    "jiji": "Jiji",
    "cheki": "Cheki",
    "autochek": "Autochek",
    "beepbeep": "BeepBeep",
}


# ─── SCRAPER SERVICE ──────────────────────────────────────

class ScraperService:
    """
    Handles scraper jobs and execution.
    """

    def __init__(self):
        self.supabase = get_supabase()
        self.worker = ScraperWorker()
        self.jobs: Dict[int, Dict[str, Any]] = {}

    # ─── SOURCES ────────────────────────────────────────────

    async def get_source_id(self, source_name: str) -> int:
        """
        Get source ID by name.
        
        Raises:
            ValueError: If source not found or invalid
        """
        # Validate source name
        if source_name not in VALID_SOURCES:
            available = ", ".join(sorted(VALID_SOURCES))
            raise ValueError(
                f"Invalid source '{source_name}'. Available sources: {available}"
            )

        logger.info(f"Looking up scraper source '{source_name}'")

        try:
            response = (
                self.supabase
                .table("market_sources")
                .select("id, name")
                .eq("name", source_name)
                .limit(1)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                # Check if table has any sources at all
                all_sources = (
                    self.supabase
                    .table("market_sources")
                    .select("name")
                    .execute()
                )
                
                if all_sources.data:
                    available = ", ".join([s["name"] for s in all_sources.data])
                    raise ValueError(
                        f"Source '{source_name}' not found. Available sources in DB: {available}"
                    )
                else:
                    raise ValueError(
                        f"Source '{source_name}' not found. The 'market_sources' table is empty. "
                        f"Please seed it with: INSERT INTO market_sources (name) VALUES "
                        f"('jiji'), ('cheki'), ('autochek'), ('beepbeep');"
                    )

            source_id = response.data[0]["id"]
            logger.info(f"Found source_id={source_id} for '{source_name}'")
            return source_id

        except ValueError:
            raise
        except Exception as e:
            logger.exception(f"Database error looking up source '{source_name}'")
            raise ValueError(f"Database error looking up source '{source_name}': {str(e)}")

    # ─── FIXED: GET SOURCES ─────────────────────────────────

    async def get_sources(self) -> Dict[str, Any]:
        """Get all available scraper sources."""
        try:
            response = (
                self.supabase
                .table("market_sources")
                .select("*")
                .order("name")
                .execute()
            )

            sources = response.data or []
            
            # Return flat dictionary matching router expectations
            return {
                "sources": sources,
                "count": len(sources),
            }

        except Exception as e:
            logger.exception("Unable to get sources")
            return {
                "sources": [],
                "count": 0,
            }

    # ─── FIXED: DASHBOARD STATUS ───────────────────────────

    async def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive scraper status for dashboard.
        """
        try:
            # Get job counts
            status_counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0}
            
            try:
                for status in status_counts.keys():
                    count_response = (
                        self.supabase
                        .table("scraper_jobs")
                        .select("id", count="exact")
                        .eq("status", status)
                        .execute()
                    )
                    status_counts[status] = count_response.count or 0
            except Exception:
                pass

            # Get latest job
            latest = (
                self.supabase
                .table("scraper_jobs")
                .select("*")
                .order("started_at", desc=True)
                .limit(1)
                .execute()
            )
            last_job = latest.data[0] if latest.data else {}

            # Get total listings
            total_listings = 0
            try:
                listings = (
                    self.supabase
                    .table("market_listings")
                    .select("id", count="exact")
                    .execute()
                )
                total_listings = listings.count or 0
            except Exception:
                pass

            # Get sources
            sources_result = await self.get_sources()
            sources = sources_result.get("sources", [])

            # Return flat dictionary matching router expectations
            return {
                "status": last_job.get("status", "idle"),
                "running": status_counts["running"] > 0,
                "pending_jobs": status_counts["pending"],
                "running_jobs": status_counts["running"],
                "completed_jobs": status_counts["completed"],
                "failed_jobs": status_counts["failed"],
                "total_jobs": sum(status_counts.values()),
                "last_run": last_job.get("started_at"),
                "last_run_status": last_job.get("status"),
                "total_listings": total_listings,
                "sources": sources,
                "sources_count": len(sources)
            }

        except Exception as e:
            logger.exception("Unable to get scraper status")
            return {
                "status": "idle",
                "running": False,
                "pending_jobs": 0,
                "running_jobs": 0,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "total_jobs": 0,
                "last_run": None,
                "last_run_status": None,
                "total_listings": 0,
                "sources": [],
                "sources_count": 0
            }

    # ─── CREATE JOB ─────────────────────────────────────────

    async def start_scraper(
        self,
        source: str,
        pages: int = 3,
        limit_per_page: int = 20,
        user_id: Optional[str] = None,
    ) -> int:
        """
        Create a new scraper job.
        
        Returns:
            int: Job ID
            
        Raises:
            ValueError: If source is invalid or not found
        """
        try:
            source_id = await self.get_source_id(source)
            
            now = datetime.now(timezone.utc).isoformat()
            
            response = (
                self.supabase
                .table("scraper_jobs")
                .insert({
                    "source_id": source_id,
                    "status": "pending",
                    "started_at": now,
                    "pages_scraped": 0,
                    "listings_found": 0,
                    "listings_saved": 0,
                    "listings_updated": 0,
                    "error_count": 0,
                })
                .execute()
            )

            if not response.data:
                raise Exception("Unable to create scraper job")

            job = response.data[0]

            # Store job metadata with source info in memory
            self.jobs[job["id"]] = {
                "id": job["id"],
                "source": source,
                "status": "pending",
                "pages": pages,
                "limit_per_page": limit_per_page,
                "created_at": now
            }

            logger.info(f"Created scraper job {job['id']} for source '{source}'")
            return job["id"]

        except ValueError:
            raise
        except Exception as e:
            logger.exception(f"Failed to create scraper job for '{source}'")
            raise Exception(f"Failed to create scraper job: {str(e)}")

    # ─── RUN SCRAPER ────────────────────────────────────────

    async def run_scraper_background(
        self,
        job_id: int,
        source: str,
        pages: int = 3,
        limit_per_page: int = 20,
    ) -> Dict[str, Any]:
        """
        Run scraper in background.
        """
        start = datetime.now(timezone.utc)
        logger.info(f"Starting scraper job {job_id} for source '{source}'")

        try:
            # Update to running
            self.supabase.table("scraper_jobs").update({
                "status": "running"
            }).eq("id", job_id).execute()

            # Run the scraper
            result = await self.worker.run(
                source=source,
                pages=pages,
                limit_per_page=limit_per_page,
            )

            duration = int(
                (datetime.now(timezone.utc) - start).total_seconds()
            )

            # Update with success
            self.supabase.table("scraper_jobs").update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "pages_scraped": pages,
                "listings_found": result.get(
                    "listings_found",
                    result.get("total_found", 0),
                ),
                "listings_saved": result.get(
                    "listings_saved",
                    result.get("total_saved", 0),
                ),
                "duration_seconds": duration,
            }).eq("id", job_id).execute()

            # Update in-memory cache
            self.jobs[job_id] = {
                "id": job_id,
                "source": source,
                "status": "completed",
                "pages": pages,
                "limit_per_page": limit_per_page,
                "created_at": start.isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "result": result
            }

            logger.info(f"Scraper job {job_id} completed successfully")
            return {
                "success": True,
                "status": "completed",
                "job_id": job_id,
                "source": source,
                "result": result
            }

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"Scraper job {job_id} failed: {error_msg}")

            # Update with failure
            self.supabase.table("scraper_jobs").update({
                "status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "error_count": 1,
                "duration_seconds": int((datetime.now(timezone.utc) - start).total_seconds()),
            }).eq("id", job_id).execute()

            # Update in-memory cache
            self.jobs[job_id] = {
                "id": job_id,
                "source": source,
                "status": "failed",
                "pages": pages,
                "limit_per_page": limit_per_page,
                "created_at": start.isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "error": error_msg
            }

            return {
                "success": False,
                "status": "failed",
                "job_id": job_id,
                "source": source,
                "error": error_msg
            }

    # ─── FIXED: JOB STATUS ──────────────────────────────────

    async def get_job_status(self, job_id: int) -> Dict[str, Any]:
        """
        Get status of a specific job.
        """
        try:
            # Check in-memory cache first
            if job_id in self.jobs:
                return self.jobs[job_id]

            # Query database
            response = (
                self.supabase
                .table("scraper_jobs")
                .select("*")
                .eq("id", job_id)
                .execute()
            )

            if not response.data:
                return {
                    "error": f"Job {job_id} not found"
                }

            return response.data[0]

        except Exception as e:
            logger.exception(f"Failed to get job {job_id} status")
            return {
                "error": f"Failed to get job status: {str(e)}"
            }

    # ─── FIXED: JOB HISTORY ────────────────────────────────

    async def get_job_history(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Get job history with pagination.
        """
        try:
            response = (
                self.supabase
                .table("scraper_jobs")
                .select("*")
                .order("started_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )

            # Get total count
            count_response = (
                self.supabase
                .table("scraper_jobs")
                .select("id", count="exact")
                .execute()
            )

            total = count_response.count or 0

            # Return flat dictionary matching router expectations
            return {
                "jobs": response.data or [],
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total
            }

        except Exception as e:
            logger.exception("Failed to get job history")
            return {
                "jobs": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "has_more": False,
                "error": str(e)
            }

    # ─── HEALTH CHECK ──────────────────────────────────────

    async def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive health check.
        """
        try:
            # Check database connection
            db_response = (
                self.supabase
                .table("market_sources")
                .select("id")
                .limit(1)
                .execute()
            )
            db_connected = True

            # Get source count
            sources_response = (
                self.supabase
                .table("market_sources")
                .select("id", count="exact")
                .execute()
            )
            source_count = sources_response.count or 0

            # Get job count
            jobs_response = (
                self.supabase
                .table("scraper_jobs")
                .select("id", count="exact")
                .execute()
            )
            job_count = jobs_response.count or 0

            # Get latest job
            latest = (
                self.supabase
                .table("scraper_jobs")
                .select("status, started_at")
                .order("started_at", desc=True)
                .limit(1)
                .execute()
            )
            latest_job = latest.data[0] if latest.data else None

            return {
                "success": True,
                "data": {
                    "status": "healthy" if db_connected else "unhealthy",
                    "database": "connected" if db_connected else "disconnected",
                    "worker": "active",
                    "sources": source_count,
                    "jobs": job_count,
                    "latest_job": latest_job,
                    "time": datetime.now(timezone.utc).isoformat()
                }
            }

        except Exception as e:
            logger.exception("Health check failed")
            return {
                "success": False,
                "data": {
                    "status": "unhealthy",
                    "database": "disconnected",
                    "worker": "inactive",
                    "sources": 0,
                    "jobs": 0,
                    "latest_job": None,
                    "error": str(e),
                    "time": datetime.now(timezone.utc).isoformat()
                }
            }
