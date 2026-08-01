# app/modules/scraper/cheki.py
# ================================================================
# Auto-D Kenya - Cheki Vehicle Scraper
# ================================================================

import asyncio
import logging
import random
from datetime import datetime
from urllib.parse import urljoin
from typing import Dict, Any

from app.modules.scraper.base_scraper import BaseScraper


logger = logging.getLogger(__name__)


class ChekiScraper(BaseScraper):

    def __init__(self):

        super().__init__(
            source_name="cheki",
            base_url="https://cheki.co.ke"
        )

        self.search_url = (
            "https://cheki.co.ke/cars"
        )



    async def scrape(
        self,
        pages=3,
        limit_per_page=20
    ) -> Dict[str, Any]:

        listings = []


        for page in range(1, pages + 1):

            try:

                soup = await self._fetch_page(
                    self.search_url,
                    {
                        "page": page
                    }
                )


                if not soup:
                    continue



                links = []


                for a in soup.find_all("a"):

                    href = a.get("href")


                    if href:

                        url = urljoin(
                            self.base_url,
                            href
                        )


                        if "/car/" in url:
                            links.append(url)



                for url in links[:limit_per_page]:

                    item = await self._parse_listing(
                        url
                    )


                    if item:

                        listings.append(item)



                    await asyncio.sleep(
                        random.uniform(
                            0.5,
                            1.5
                        )
                    )



            except Exception as e:

                logger.error(
                    f"Cheki error: {e}"
                )



        return {

            "listings": listings,

            "stats": {

                "total_scraped":
                    len(listings),

                "successful":
                    len(listings),

                "failed": 0

            },

            "completed_at":
                datetime.utcnow()
                .isoformat()

        }




    async def _parse_listing(
        self,
        url
    ):

        try:

            soup = await self._fetch_page(
                url
            )


            if not soup:
                return {}



            title = ""

            h1 = soup.find("h1")

            if h1:

                title = h1.get_text(
                    strip=True
                )



            text = soup.get_text(
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
                        text
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
                    "",


                "seller_type":
                    "Dealer",


                "condition":
                    "Used"

            }



        except Exception as e:

            logger.error(
                f"Cheki parse error {e}"
            )

            return {}
