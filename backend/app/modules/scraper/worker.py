# app/modules/scraper/worker.py
# ================================================================
# Auto-D Kenya - Scraper Worker
# ================================================================

import logging
from datetime import datetime
from typing import Dict, Any, List

from app.core.database import get_supabase

from app.modules.scraper.jiji import JijiScraper
from app.modules.scraper.cheki import ChekiScraper
from app.modules.scraper.autochek import AutochekScraper
from app.modules.scraper.beepbeep import BeepBeepScraper


logger = logging.getLogger(__name__)


class ScraperWorker:


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




    def get_sources(self) -> List[str]:

        return list(
            self.scrapers.keys()
        )




    async def save_listing(
        self,
        source: str,
        listing: Dict[str, Any]
    ):

        try:


            source_row = (
                self.supabase
                .table("market_sources")
                .select("id")
                .eq(
                    "name",
                    source
                )
                .single()
                .execute()
            )


            if not source_row.data:

                return False



            source_id = source_row.data["id"]



            data = {

                "source_id":
                    source_id,


                "listing_id":
                    listing.get(
                        "listing_id"
                    ),


                "url":
                    listing.get(
                        "url"
                    ),


                "year":
                    listing.get(
                        "year"
                    ),


                "price":
                    listing.get(
                        "price"
                    ),


                "currency":
                    "KES",


                "mileage":
                    listing.get(
                        "mileage"
                    ),


                "engine_size":
                    listing.get(
                        "engine_size"
                    ),


                "fuel_type":
                    listing.get(
                        "fuel_type"
                    ),


                "transmission":
                    listing.get(
                        "transmission"
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
                        "condition"
                    ),


                "active":
                    True,


                "first_seen":
                    datetime.utcnow()
                    .isoformat(),


                "last_seen":
                    datetime.utcnow()
                    .isoformat()

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

                "status":
                    "failed",

                "error":
                    "Unknown source"

            }



        scraper = self.scrapers[source]



        result = await scraper.run(
            pages,
            limit_per_page
        )



        listings = result.get(
            "listings",
            []
        )



        saved = 0



        for listing in listings:


            ok = await self.save_listing(
                source,
                listing
            )


            if ok:

                saved += 1



        return {

            "source":
                source,


            "status":
                "success",


            "listings_found":
                len(listings),


            "listings_saved":
                saved,


            "result":
                result

        }




    async def run_all(
        self,
        pages=3,
        limit_per_page=20
    ):


        output = {}

        total_found = 0

        total_saved = 0



        for source in self.scrapers:


            result = await self.run_source(
                source,
                pages,
                limit_per_page
            )


            output[source] = result


            total_found += result.get(
                "listings_found",
                0
            )


            total_saved += result.get(
                "listings_saved",
                0
            )



        return {

            "total_found":
                total_found,


            "total_saved":
                total_saved,


            "sources":
                output

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
