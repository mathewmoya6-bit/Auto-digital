# app/modules/scraper/autochek.py
# ================================================================
# Auto-D Kenya - Autochek Vehicle Scraper
# ================================================================

import asyncio
import logging
import random
from datetime import datetime
from urllib.parse import urljoin
from typing import Dict, Any

from app.modules.scraper.base_scraper import BaseScraper


logger = logging.getLogger(__name__)


class AutochekScraper(BaseScraper):
    """
    Scraper for Autochek vehicle listings.
    """


    def __init__(self):

        super().__init__(
            source_name="autochek",
            base_url="https://autochek.africa"
        )

        self.search_url = (
            "https://autochek.africa/ke/cars"
        )



    async def scrape(
        self,
        pages: int = 3,
        limit_per_page: int = 20
    ) -> Dict[str, Any]:

        listings = []


        for page in range(1, pages + 1):

            logger.info(
                f"Autochek scraping page {page}"
            )


            try:

                soup = await self._fetch_page(
                    self.search_url,
                    {
                        "page": page
                    }
                )


                if not soup:

                    continue



                urls = []


                for link in soup.find_all("a"):

                    href = link.get(
                        "href"
                    )


                    if href:

                        url = urljoin(
                            self.base_url,
                            href
                        )


                        if (
                            "/cars/" in url
                            and url not in urls
                        ):

                            urls.append(url)



                for url in urls[:limit_per_page]:

                    listing = await self._parse_listing(
                        url
                    )


                    if listing:

                        listings.append(
                            listing
                        )


                    await asyncio.sleep(
                        random.uniform(
                            0.5,
                            1.5
                        )
                    )



                await asyncio.sleep(
                    random.uniform(
                        1,
                        2
                    )
                )



            except Exception as e:

                logger.error(
                    f"Autochek page error: {e}"
                )



        return {

            "listings":
                listings,


            "stats": {

                "total_scraped":
                    len(listings),

                "successful":
                    len(listings),

                "failed":
                    0

            },


            "completed_at":
                datetime.utcnow()
                .isoformat()

        }





    async def _parse_listing(
        self,
        url: str
    ) -> Dict[str, Any]:

        try:

            soup = await self._fetch_page(
                url
            )


            if not soup:

                return {}



            title = ""


            title_element = soup.find(
                "h1"
            )


            if title_element:

                title = title_element.get_text(
                    strip=True
                )



            page_text = soup.get_text(
                " ",
                strip=True
            )



            return {

                "listing_id":

                    url.rstrip("/")
                    .split("/")
                    [-1],



                "title":

                    title,



                "url":

                    url,



                "price":

                    self._parse_price(
                        page_text
                    ),



                "currency":

                    "KES",



                "make":

                    "",



                "model":

                    "",



                "year":

                    None,



                "mileage":

                    None,



                "engine_size":

                    None,



                "fuel_type":

                    "",



                "transmission":

                    "",



                "body_type":

                    "",



                "location":

                    "Kenya",



                "seller_name":

                    "Autochek",



                "seller_type":

                    "Dealer",



                "condition":

                    "Used"

            }



        except Exception as e:

            logger.error(
                f"Autochek parse failed: {e}"
            )

            return {}
