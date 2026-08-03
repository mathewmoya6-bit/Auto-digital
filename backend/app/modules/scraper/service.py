# app/modules/scraper/service.py

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.core.database import get_supabase
from app.modules.scraper.worker import ScraperWorker

logger = logging.getLogger(__name__)


# ─── SCRAPER SERVICE ──────────────────────────────────────

class ScraperService:
    """
    Thin wrapper around ScraperWorker for API endpoints.
    
    All execution logic, status management, and database operations
    are delegated to the worker. This service only handles:
    - Request/response formatting
    - Parameter validation
    - Logging
    
    The worker owns:
    - scraper_runs lifecycle
    - Source validation and caching
    - Execution with retries
    - Status tracking
    - Database operations
    """

    def __init__(self):
        self.worker = ScraperWorker()

    # ─── GET SOURCES ────────────────────────────────────────

    async def get_sources(self) -> Dict[str, Any]:
        """Get all available scraper sources."""
        try:
            sources = await self.worker.get_available_sources()
            
            return {
                "sources": sources,
                "count": len(sources),
                "available_scrapers": sources,  # Same list for now
            }

        except Exception as e:
            logger.exception("Unable to get sources")
            return {
                "sources": [],
                "count": 0,
                "available_scrapers": [],
            }

    # ─── DASHBOARD STATUS ──────────────────────────────────

    async def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive scraper status for dashboard.
        Delegates entirely to worker.
        """
        try:
            status_data = await self.worker.get_dashboard_status()
            
            # Format for API response
            return {
                "status": status_data.get("last_status", "idle"),
                "running": status_data.get("running_count", 0) > 0,
                "pending_jobs": status_data.get("pending_count", 0),
                "running_jobs": status_data.get("running_count", 0),
                "completed_jobs": status_data.get("completed_count", 0),
                "failed_jobs": status_data.get("failed_count", 0),
                "total_jobs": sum([
                    status_data.get("pending_count", 0),
                    status_data.get("running_count", 0),
                    status_data.get("completed_count", 0),
                    status_data.get("failed_count", 0),
                ]),
                "last_run": status_data.get("last_run", {}).get("started_at"),
                "last_run_status": status_data.get("last_run", {}).get("status"),
                "last_run_listings_found": status_data.get("last_run", {}).get("listings_found", 0),
                "last_run_listings_saved": status_data.get("last_run", {}).get("listings_saved", 0),
                "total_listings": status_data.get("total_listings", 0),
                "sources": status_data.get("sources", []),
                "sources_count": len(status_data.get("sources", [])),
                "available_scrapers": await self.worker.get_available_sources(),
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
                "last_run_listings_found": 0,
                "last_run_listings_saved": 0,
                "total_listings": 0,
                "sources": [],
                "sources_count": 0,
                "available_scrapers": [],
            }

    # ─── RUN SCRAPER ──────────────────────────────────────

    async def run_scraper(
        self,
        source: str = "all",
        pages: int = 3,
        limit_per_page: int = 20,
        parallel: bool = True,
        max_concurrent: int = 4,
    ) -> Dict[str, Any]:
        """
        Run scraper for a specific source or all sources.
        Delegates entirely to worker.
        """
        logger.info(
            "Starting scraper source=%s pages=%s limit=%s parallel=%s max_concurrent=%s",
            source,
            pages,
            limit_per_page,
            parallel,
            max_concurrent,
        )

        return await self.worker.run(
            source=source,
            pages=pages,
            limit_per_page=limit_per_page,
            parallel=parallel,
            max_concurrent=max_concurrent,
        )

    # ─── RUN STATUS ────────────────────────────────────────

    async def get_run_status(self, run_id: int) -> Dict[str, Any]:
        """
        Get status of a specific scraper run.
        Delegates to worker.
        """
        try:
            run = await self.worker.get_run(run_id)
            
            if not run:
                return {
                    "error": f"Run {run_id} not found",
                    "found": False
                }
            
            return {
                "found": True,
                **run
            }

        except Exception as e:
            logger.exception(f"Failed to get run {run_id} status")
            return {
                "error": f"Failed to get run status: {str(e)}",
                "found": False
            }

    # ─── RUN HISTORY ────────────────────────────────────────

    async def get_run_history(
        self,
        limit: int = 20,
        offset: int = 0,
        source: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get scraper run history with pagination and filters.
        Delegates to worker.
        """
        try:
            return await self.worker.get_run_history(
                limit=limit,
                offset=offset,
                source=source,
                status=status,
            )

        except Exception as e:
            logger.exception("Failed to get run history")
            return {
                "runs": [],
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
        Delegates to worker.
        """
        try:
            worker_health = await self.worker.health_check()
            
            return {
                "success": True,
                "data": {
                    "status": "healthy" if worker_health.get("healthy") else "degraded",
                    "database": worker_health.get("database_status", "unknown"),
                    "worker": "active" if worker_health.get("healthy") else "degraded",
                    "sources": worker_health.get("source_count", 0),
                    "runs": worker_health.get("run_count", 0),
                    "latest_run": worker_health.get("latest_run"),
                    "available_scrapers": await self.worker.get_available_sources(),
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
                    "runs": 0,
                    "latest_run": None,
                    "available_scrapers": [],
                    "error": str(e),
                    "time": datetime.now(timezone.utc).isoformat()
                }
            }

    # ─── RECOVER STUCK JOBS ────────────────────────────────

    async def recover_stuck_jobs(self, max_age_minutes: int = 60) -> Dict[str, Any]:
        """
        Recover stuck scraper runs.
        Delegates to worker.
        """
        return await self.worker.recover_stuck_jobs(max_age_minutes=max_age_minutes)
