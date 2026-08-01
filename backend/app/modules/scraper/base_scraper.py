# app/modules/scraper/base_scraper.py
# ================================================================
# Auto-D Kenya - Base Scraper
# ================================================================
# Common scraper functionality for Jiji, Cheki, Autochek, BeepBeep
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
    Base class inherited by all vehicle scrapers.
    """

    def __init__(
        self,
        source_name: str,
        base_url: str
    ):

        self.source_name = source_name
        self.base_url = base_url

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "Chrome/120 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9"
        }



    async def run(
        self,
        pages: int = 3,
        limit_per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Standard scraper execution wrapper.
        """

        start = time.time()

        try:

            result = await self.scrape(
                pages=pages,
                limit_per_page=limit_per_page
            )


            # Allow scraper to return either:
            # list[]
            # or {"listings":[]}

            if isinstance(result, list):

                listings = result

            else:

                listings = result.get(
                    "listings",
                    []
                )



            duration = round(
                time.time() - start,
                2
            )


            return {

                "source":
                    self.source_name,

                "status":
                    "success",

                "listings":
                    listings,


                "stats": {

                    "total_scraped":
                        len(listings),

                    "successful":
                        len(listings),

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
                            time.time() - start,
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
        Fetch HTML page.
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
                f"Failed fetching {url}: {e}"
            )

            return None



    def _parse_price(
        self,
        value: str
    ):

        if not value:
            return None


        try:

            clean = (
                value
                .replace("KES", "")
                .replace(",", "")
                .strip()
            )

            return float(clean)


        except Exception:

            return None



    def _parse_year(
        self,
        value: str
    ):

        if not value:
            return None


        try:

            digits = "".join(
                c for c in value
                if c.isdigit()
            )


            year = int(
                digits[:4]
            )


            if 1900 <= year <= datetime.now().year + 1:
                return year


        except Exception:

            pass


        return None



    def _parse_mileage(
        self,
        value: str
    ):

        if not value:
            return None


        try:

            clean = (
                value
                .lower()
                .replace("km", "")
                .replace(",", "")
                .strip()
            )

            return int(float(clean))


        except Exception:

            return None



    def _parse_engine_size(
        self,
        value: str
    ):

        if not value:
            return None


        try:

            number = ""

            for char in value:

                if char.isdigit() or char == ".":

                    number += char


            if number:

                return float(number)


        except Exception:

            pass


        return None



    async def scrape(
        self,
        pages: int,
        limit_per_page: int
    ):

        """
        Must be implemented by child scraper.
        """

        raise NotImplementedError(
            "Scraper must implement scrape()"
        )
