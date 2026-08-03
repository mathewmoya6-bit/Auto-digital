# app/modules/scraper/service.py

import logging
from datetime import datetime
from typing import Optional

from app.core.database import get_supabase
from app.modules.scraper.worker import ScraperWorker

logger = logging.getLogger(__name__)


class ScraperService:
    """
    Handles scraper jobs and execution.
    """

    def __init__(self):
        self.supabase = get_supabase()
        self.worker = ScraperWorker()
        self.jobs = {}

    # ============================================================
    # SOURCES
    # ============================================================

    async def get_source_id(self, source_name: str):

        response = (
            self.supabase
            .table("market_sources")
            .select("id")
            .eq("name", source_name)
            .single()
            .execute()
        )

        if not response.data:
            raise Exception(f"Unknown scraper source: {source_name}")

        return response.data["id"]

    async def get_sources(self):

        response = (
            self.supabase
            .table("market_sources")
            .select("*")
            .execute()
        )

        return {
            "sources": response.data or []
        }

    # ============================================================
    # DASHBOARD STATUS
    # ============================================================

    async def get_status(self):
        """
        Dashboard scraper status.
        """

        try:

            latest = (
                self.supabase
                .table("scraper_jobs")
                .select("*")
                .order("started_at", desc=True)
                .limit(1)
                .execute()
            )

            last_job = latest.data[0] if latest.data else {}

            total_listings = 0

            try:
                listings = (
                    self.supabase
                    .table("market_listings")
                    .select("id", count="exact")
                    .limit(1)
                    .execute()
                )

                total_listings = listings.count or 0

            except Exception:
                pass

            sources = await self.get_sources()

            return {
                "status": last_job.get("status", "idle"),
                "running": last_job.get("status") == "running",
                "last_run": last_job.get("started_at"),
                "total_listings": total_listings,
                "sources": sources["sources"]
            }

        except Exception as e:

            logger.exception("Unable to get scraper status")

            return {
                "status": "idle",
                "running": False,
                "last_run": None,
                "total_listings": 0,
                "sources": [],
                "error": str(e)
            }

    # ============================================================
    # CREATE JOB
    # ============================================================

    async def start_scraper(
        self,
        source: str,
        pages: int = 3,
        limit_per_page: int = 20,
        user_id: Optional[str] = None,
    ):

        source_id = await self.get_source_id(source)

        response = (
            self.supabase
            .table("scraper_jobs")
            .insert({
                "source_id": source_id,
                "status": "pending",
                "started_at": datetime.utcnow().isoformat(),
                "pages_scraped": 0,
                "listings_found": 0,
                "listings_saved": 0,
                "listings_updated": 0,
                "error_count": 0
            })
            .execute()
        )

        if not response.data:
            raise Exception("Unable to create scraper job")

        job = response.data[0]

        self.jobs[job["id"]] = job

        return job["id"]

    # ============================================================
    # RUN SCRAPER
    # ============================================================

    async def run_scraper_background(
        self,
        job_id: int,
        source: str,
        pages: int = 3,
        limit_per_page: int = 20,
    ):

        start = datetime.utcnow()

        try:

            (
                self.supabase
                .table("scraper_jobs")
                .update({
                    "status": "running"
                })
                .eq("id", job_id)
                .execute()
            )

            result = await self.worker.run(
                source=source,
                pages=pages,
                limit_per_page=limit_per_page,
            )

            duration = int(
                (datetime.utcnow() - start).total_seconds()
            )

            (
                self.supabase
                .table("scraper_jobs")
                .update({
                    "status": "completed",
                    "completed_at": datetime.utcnow().isoformat(),
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
                })
                .eq("id", job_id)
                .execute()
            )

            self.jobs[job_id] = {
                "status": "completed",
                "result": result,
            }

            return result

        except Exception as e:

            logger.exception("Scraper failed")

            (
                self.supabase
                .table("scraper_jobs")
                .update({
                    "status": "failed",
                    "error_count": 1,
                })
                .eq("id", job_id)
                .execute()
            )

            self.jobs[job_id] = {
                "status": "failed",
                "error": str(e),
            }

            return {
                "status": "failed",
                "error": str(e),
            }

    # ============================================================
    # JOB STATUS
    # ============================================================

    async def get_job_status(self, job_id: int):

        if job_id in self.jobs:
            return self.jobs[job_id]

        response = (
            self.supabase
            .table("scraper_jobs")
            .select("*")
            .eq("id", job_id)
            .single()
            .execute()
        )

        return response.data or {
            "error": "Job not found"
        }

    # ============================================================
    # JOB HISTORY
    # ============================================================

    async def get_job_history(
        self,
        limit: int = 20,
        offset: int = 0,
    ):

        response = (
            self.supabase
            .table("scraper_jobs")
            .select("*")
            .order("started_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return {
            "jobs": response.data or [],
            "limit": limit,
            "offset": offset,
        }

    # ============================================================
    # HEALTH
    # ============================================================

    async def health_check(self):

        try:

            self.supabase.table(
                "market_sources"
            ).select("id").limit(1).execute()

            return {
                "status": "healthy",
                "database": "connected",
                "worker": "active",
                "time": datetime.utcnow().isoformat(),
            }

        except Exception as e:

            return {
                "status": "unhealthy",
                "database": "disconnected",
                "worker": "inactive",
                "error": str(e),
                "time": datetime.utcnow().isoformat(),
            }
