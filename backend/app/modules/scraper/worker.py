# app/modules/scraper/worker.py
# ================================================================
# Auto-D Kenya - Scraper Worker
# ================================================================

import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Any, List

from app.core.database import get_supabase

from app.modules.scraper.jiji import JijiScraper
from app.modules.scraper.cheki import ChekiScraper
from app.modules.scraper.autochek import AutochekScraper
from app.modules.scraper.beepbeep import BeepBeepScraper


logger = logging.getLogger(__name__)


class ScraperWorker:
    """
    Runs scraper jobs and saves vehicle listings.
    """


    def __init__(self):

        self.supabase = get_supabase()

        self.scrapers = {

            "jiji":
                JijiScraper(),

            "cheki":
                ChekiScraper(),

            "autochek":
                AutochekScraper(),

            "beepbeep":
                BeepBeepScraper()
        }


        self.results = {}

        self.source_cache = {}



    def get_sources(self) -> List[str]:

        return list(
            self.scrapers.keys()
        )



    async def get_source_id(
        self,
        source_name: str
    ):

        if source_name in self.source_cache:

            return self.source_cache[source_name]


        response = (
            self.supabase
            .table("market_sources")
            .select("id")
            .eq("name", source_name)
            .single()
            .execute()
        )


        if not response.data:

            raise Exception(
                f"Source not found: {source_name}"
            )


        source_id = response.data["id"]


        self.source_cache[source_name] = source_id


        return source_id



    async def get_make_id(
        self,
        make_name
    ):

        if not make_name:

            return None


        response = (
            self.supabase
            .table("vehicle_makes")
            .select("id")
            .ilike(
                "name",
                make_name
            )
            .limit(1)
            .execute()
        )


        if response.data:

            return response.data[0]["id"]


        return None



    async def get_model_id(
        self,
        model_name,
        make_id
    ):

        if not model_name or not make_id:

            return None


        response = (
            self.supabase
            .table("vehicle_models")
            .select("id")
            .ilike(
                "name",
                model_name
            )
            .eq(
                "make_id",
                make_id
            )
            .limit(1)
            .execute()
        )


        if response.data:

            return response.data[0]["id"]


        return None



    async def save_listing(
        self,
        source,
        listing
    ) -> bool:


        try:

            source_id = await self.get_source_id(
                source
            )


            make_id = await self.get_make_id(
                listing.get("make")
            )


            model_id = await self.get_model_id(
                listing.get("model"),
                make_id
            )


            if not make_id:

                logger.warning(
                    f"Make not found: {listing.get('make')}"
                )


            data = {

                "source_id":
                    source_id,


                "listing_id":
                    str(
                        listing.get(
                            "listing_id"
                        )
                    ),


                "url":
                    listing.get(
                        "url"
                    ),


                "make_id":
                    make_id,


                "model_id":
                    model_id,


                "year":
                    listing.get(
                        "year"
                    ),


                "price":
                    listing.get(
                        "price"
                    ),


                "currency":
                    listing.get(
                        "currency",
                        "KES"
                    ),


                "mileage":
                    listing.get(
                        "mileage"
                    ),


                "engine_size":
                    listing.get(
                        "engine_size"
                    ),


                "transmission":
                    listing.get(
                        "transmission"
                    ),


                "fuel_type":
                    listing.get(
                        "fuel_type"
                    ),


                "body_type":
                    listing.get(
                        "body_type"
                    ),


                "location":
                    listing.get(
                        "location"
                    ),


                "seller_name":
                    listing.get(
                        "seller_name"
                    ),


                "seller_type":
                    listing.get(
                        "seller_type"
                    ),


                "condition":
                    listing.get(
                        "condition",
                        "Used"
                    ),


                "first_seen":
                    datetime.utcnow()
                    .isoformat(),


                "last_seen":
                    datetime.utcnow()
                    .isoformat(),


                "active":
                    True

            }



            self.supabase.table(
                "market_listings"
            ).insert(
                data
            ).execute()



            return True



        except Exception as e:

            logger.error(
                f"Save listing failed: {e}"
            )

            return False




    async def run_source(
        self,
        source: str,
        pages: int = 3,
        limit_per_page: int = 20
    ):


        if source not in self.scrapers:

            return {

                "source":
                    source,

                "status":
                    "failed",

                "error":
                    "Unknown source"
            }



        try:

            scraper = self.scrapers[source]


            result = await scraper.run(
                pages=pages,
                limit_per_page=limit_per_page
            )


            listings = result.get(
                "listings",
                []
            )


            saved = 0


            for listing in listings:

                if await self.save_listing(
                    source,
                    listing
                ):

                    saved += 1



            response = {

                "source":
                    source,


                "status":
                    "success",


                "listings_found":
                    len(listings),


                "listings_saved":
                    saved,


                "completed_at":
                    datetime.utcnow()
                    .isoformat()

            }


            self.results[source] = response


            return response



        except Exception as e:


            logger.exception(
                f"{source} failed"
            )


            return {

                "source":
                    source,

                "status":
                    "failed",

                "error":
                    str(e)

            }




    async def run_all(
        self,
        pages=3,
        limit_per_page=20,
        delay=2
    ):


        results = {}

        total_found = 0

        total_saved = 0



        for source in self.scrapers:


            result = await self.run_source(
                source,
                pages,
                limit_per_page
            )


            results[source] = result



            total_found += result.get(
                "listings_found",
                0
            )


            total_saved += result.get(
                "listings_saved",
                0
            )



            await asyncio.sleep(
                delay + random.random()
            )



        return {

            "total_found":
                total_found,

            "total_saved":
                total_saved,

            "sources":
                results,

            "completed_at":
                datetime.utcnow()
                .isoformat()
        }



    async def run(
        self,
        source="all",
        pages=3,
        limit_per_page=20
    ):


        if source == "all":

            return await self.run_all(
                pages,
                limit_per_page
            )


        return await self.run_source(
            source,
            pages,
            limit_per_page
        )
