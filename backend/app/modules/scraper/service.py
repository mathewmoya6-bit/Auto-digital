# app/modules/scraper/service.py
# ================================================================
# Auto-D Kenya - Scraper Service
# ================================================================

import logging
from datetime import datetime
from typing import Dict, Any, Optional

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



    async def get_source_id(
        self,
        source_name: str
    ):

        response = (
            self.supabase
            .table("market_sources")
            .select("id")
            .eq(
                "name",
                source_name
            )
            .single()
            .execute()
        )


        if not response.data:

            raise Exception(
                f"Source not found {source_name}"
            )


        return response.data["id"]




    async def start_scraper(
        self,
        source: str,
        pages: int = 3,
        limit_per_page: int = 20,
        user_id: Optional[str] = None
    ):

        """
        Create scraper job.
        """


        source_id = await self.get_source_id(
            source
        )


        now = datetime.utcnow().isoformat()



        response = (
            self.supabase
            .table("scraper_jobs")
            .insert({

                "source_id":
                    source_id,

                "status":
                    "pending",

                "started_at":
                    now,

                "pages_scraped":
                    0,

                "listings_found":
                    0,

                "listings_saved":
                    0,

                "listings_updated":
                    0,

                "error_count":
                    0

            })
            .execute()
        )


        if not response.data:

            raise Exception(
                "Failed creating scraper job"
            )



        job_id = response.data[0]["id"]



        self.jobs[job_id] = {

            "id":
                job_id,

            "source":
                source,

            "status":
                "pending"

        }



        return job_id




    async def run_scraper_background(
        self,
        job_id: int,
        source: str,
        pages: int = 3,
        limit_per_page: int = 20
    ):


        start_time = datetime.utcnow()



        try:


            self.supabase.table(
                "scraper_jobs"
            ).update({

                "status":
                    "running"

            }).eq(
                "id",
                job_id
            ).execute()



            result = await self.worker.run(
                source=source,
                pages=pages,
                limit_per_page=limit_per_page
            )



            duration = (
                datetime.utcnow()
                - start_time
            ).seconds



            self.supabase.table(
                "scraper_jobs"
            ).update({

                "status":
                    "completed",

                "completed_at":
                    datetime.utcnow()
                    .isoformat(),

                "pages_scraped":
                    pages,

                "listings_found":
                    result.get(
                        "listings_found",
                        result.get(
                            "total_found",
                            0
                        )
                    ),

                "listings_saved":
                    result.get(
                        "listings_saved",
                        result.get(
                            "total_saved",
                            0
                        )
                    ),

                "duration_seconds":
                    duration

            }).eq(
                "id",
                job_id
            ).execute()



            self.jobs[job_id].update({

                "status":
                    "completed",

                "result":
                    result

            })



            return result



        except Exception as e:


            logger.exception(
                "Scraper job failed"
            )



            self.supabase.table(
                "scraper_jobs"
            ).update({

                "status":
                    "failed",

                "error_count":
                    1

            }).eq(
                "id",
                job_id
            ).execute()



            self.jobs[job_id].update({

                "status":
                    "failed",

                "error":
                    str(e)

            })


            return {

                "status":
                    "failed",

                "error":
                    str(e)

            }




    async def get_job_status(
        self,
        job_id: int
    ):


        if job_id in self.jobs:

            return self.jobs[job_id]



        response = (
            self.supabase
            .table("scraper_jobs")
            .select("*")
            .eq(
                "id",
                job_id
            )
            .execute()
        )


        if response.data:

            return response.data[0]


        return {

            "error":
                "Job not found"

        }




    async def get_job_history(
        self,
        limit: int = 20,
        offset: int = 0
    ):


        response = (
            self.supabase
            .table("scraper_jobs")
            .select("*")
            .order(
                "started_at",
                desc=True
            )
            .range(
                offset,
                offset + limit - 1
            )
            .execute()
        )


        return {

            "jobs":
                response.data or [],

            "limit":
                limit,

            "offset":
                offset

        }



    async def get_sources(self):


        response = (
            self.supabase
            .table("market_sources")
            .select("*")
            .execute()
        )


        return {

            "sources":
                response.data or []

        }



    async def health_check(self):

        return {

            "status":
                "healthy",

            "worker":
                "active",

            "time":
                datetime.utcnow()
                .isoformat()

        }
