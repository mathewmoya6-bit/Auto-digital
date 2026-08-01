# app/modules/scraper/worker.py
# ================================================================
# Auto-D Kenya - Scraper Worker
# ================================================================

import asyncio
import logging
import random
from datetime import datetime
from typing import Any, Dict, List

from app.core.database import get_supabase

from app.scrapers.jiji import JijiScraper
from app.scrapers.cheki import ChekiScraper
from app.scrapers.autochek import AutochekScraper
from app.scrapers.beepbeep import BeepBeepScraper


logger = logging.getLogger(__name__)


class ScraperWorker:

    SOURCE_CACHE = {}

    def __init__(self):

        self.supabase = get_supabase()

        self.scrapers = {
            "jiji": JijiScraper(),
            "cheki": ChekiScraper(),
            "autochek": AutochekScraper(),
            "beepbeep": BeepBeepScraper(),
        }

        self.results = {}


    def get_sources(self) -> List[str]:
        return list(self.scrapers.keys())


    async def get_source_id(self, source_name: str):

        if source_name in self.SOURCE_CACHE:
            return self.SOURCE_CACHE[source_name]

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
                f"Source {source_name} not found"
            )

        source_id = response.data["id"]

        self.SOURCE_CACHE[source_name] = source_id

        return source_id



    async def get_make_id(self, make_name):

        if not make_name:
            return None

        result = (
            self.supabase
            .table("vehicle_makes")
            .select("id")
            .ilike("name", make_name)
            .limit(1)
            .execute()
        )

        if result.data:
            return result.data[0]["id"]

        return None



    async def get_model_id(self, model_name, make_id):

        if not model_name:
            return None

        result = (
            self.supabase
            .table("vehicle_models")
            .select("make_id,id")
            .ilike("name", model_name)
            .eq("make_id", make_id)
            .limit(1)
            .execute()
        )

        if result.data:
            return result.data[0]["id"]

        return None



    async def save_listing(
        self,
        source,
        listing
    ):

        try:

            source_id = await self.get_source_id(source)


            make_id = await self.get_make_id(
                listing.get("make")
            )


            model_id = await self.get_model_id(
                listing.get("model"),
                make_id
            )


            data = {

                "source_id": source_id,

                "listing_id":
                    str(listing.get("id")),

                "url":
                    listing.get("url"),


                "make_id":
                    make_id,

                "model_id":
                    model_id,


                "year":
                    listing.get("year"),


                "price":
                    listing.get("price"),

                "currency":
                    listing.get(
                        "currency",
                        "KES"
                    ),


                "mileage":
                    listing.get("mileage"),


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


                "active": True
            }


            result = (
                self.supabase
                .table("market_listings")
                .insert(data)
                .execute()
            )


            return True


        except Exception as e:

            logger.error(
                f"Saving listing failed: {e}"
            )

            return False



    async def run_source(
        self,
        source: str,
        pages: int = 3,
        limit_per_page: int = 20,
    ):


        if source not in self.scrapers:

            return {
                "source": source,
                "status": "failed",
                "error":
                "Source not found"
            }


        scraper = self.scrapers[source]


        try:

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

                success = await self.save_listing(
                    source,
                    listing
                )

                if success:
                    saved += 1



            self.results[source] = {

                "last_run":
                    datetime.utcnow()
                    .isoformat(),

                "saved":
                    saved
            }



            return {

                "source": source,

                "status": "success",

                "listings_found":
                    len(listings),

                "listings_saved":
                    saved,

                "result":
                    result
            }



        except Exception as e:

            logger.exception(
                f"{source} scraper failed"
            )


            return {

                "source": source,

                "status": "failed",

                "error":
                    str(e)
            }



    async def run(
        self,
        source="all",
        pages=3,
        limit_per_page=20,
        delay=2
    ):

        if source == "all":

            results = {}

            for src in self.scrapers:

                results[src] = await self.run_source(
                    src,
                    pages,
                    limit_per_page
                )

                await asyncio.sleep(
                    delay + random.random()
                )


            return results


        return await self.run_source(
            source,
            pages,
            limit_per_page
        )
