# app/scrapers/base_scraper.py
# ================================================================
# Auto-D Kenya - Base Scraper
# ================================================================

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


class BaseScraper:
    """
    Base scraper class.
    All vehicle scrapers inherit from this.
    """


    def __init__(
        self,
        source_name: str,
        base_url: str
    ):

        self.source_name = source_name
        self.base_url = base_url

        self.headers = {
            "User-Agent":
            (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64)"
            )
        }



    async def run(
        self,
        pages: int = 3,
        limit_per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Standard scraper runner.
        """

        start_time = time.time()


        try:

            listings = await self.scrape(
                pages=pages,
                limit_per_page=limit_per_page
            )


            if not isinstance(
                listings,
                dict
            ):

                listings = {
                    "listings": listings
                }



            total = len(
                listings.get(
                    "listings",
                    []
                )
            )


            duration = round(
                time.time() - start_time,
                2
            )


            return {

                "source":
                    self.source_name,


                "status":
                    "success",


                "listings":
                    listings.get(
                        "listings",
                        []
                    ),


                "stats": {

                    "total_scraped":
                        total,

                    "successful":
                        total,

                    "failed":
                        0,

                    "duration_seconds":
                        duration

                },


                "completed_at":
                    datetime.utcnow()
                    .isoformat()

            }



        except Exception as e:


            logger.exception(
                f"{self.source_name} scraper failed"
            )


            return {

                "source":
                    self.source_name,


                "status":
                    "failed",


                "listings":
                    [],


                "stats": {

                    "total_scraped": 0,

                    "successful": 0,

                    "failed": 1,

                    "duration_seconds":
                        round(
                            time.time() - start_time,
                            2
                        )

                },


                "error":
                    str(e)

            }




    async def _fetch_page(
        self,
        url: str,
        params: Optional[dict] = None
    ):

        """
        Download HTML page.
        """

        try:

            async with httpx.AsyncClient(
                headers=self.headers,
                timeout=30,
                follow_redirects=True
            ) as client:


                response = await client.get(
                    url,
                    params=params
                )


                response.raise_for_status()


                return BeautifulSoup(
                    response.text,
                    "html.parser"
                )



        except Exception as e:

            logger.error(
                f"Fetch failed {url}: {e}"
            )

            return None




    def _parse_price(
        self,
        value: str
    ):

        if not value:
            return None

        try:

            numbers = (
                value
                .replace(",", "")
                .replace("KES", "")
                .strip()
            )

            return float(numbers)


        except:

            return None




    def _parse_year(
        self,
        value: str
    ):

        if not value:
            return None

        try:

            return int(
                "".join(
                    x for x in value
                    if x.isdigit()
                )[:4]
            )

        except:

            return None




    def _parse_mileage(
        self,
        value: str
    ):

        if not value:
            return None

        try:

            return int(
                value
                .replace(",", "")
                .replace("km", "")
                .strip()
            )

        except:

            return None




    def _parse_engine_size(
        self,
        value: str
    ):

        if not value:
            return None

        try:

            return float(
                "".join(
                    x for x in value
                    if x.isdigit()
                    or x == "."
                )
            )

        except:

            return None
