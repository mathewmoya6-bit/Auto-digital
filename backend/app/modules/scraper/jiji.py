# app/modules/scraper/jiji.py
# ================================================================
# Auto-D Kenya - Jiji Vehicle Scraper
# ================================================================

import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Any, List
from urllib.parse import urljoin, urlparse

from app.modules.scraper.base_scraper import BaseScraper


logger = logging.getLogger(__name__)


class JijiScraper(BaseScraper):
    """
    Scraper for Jiji Kenya vehicle listings.
    """


    def __init__(self):

        super().__init__(
            source_name="jiji",
            base_url="https://jiji.co.ke"
        )

        self.search_url = (
            "https://jiji.co.ke/cars"
        )



    async def scrape(
        self,
        pages: int = 3,
        limit_per_page: int = 20
    ) -> Dict[str, Any]:

        listings = []


        for page in range(1, pages + 1):

            logger.info(
                f"Jiji scraping page {page}"
            )


            try:

                soup = await self._fetch_page(
                    self.search_url,
                    {
                        "page": page
                    }
                )


                if not soup:

                    logger.warning(
                        "Empty Jiji response"
                    )

                    continue



                logger.info(
                    f"Jiji HTML size: {len(str(soup))}"
                )



                urls = self._extract_listing_urls(
                    soup
                )


                logger.info(
                    f"Jiji URLs found: {len(urls)}"
                )



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

                logger.exception(
                    f"Jiji page {page} failed"
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



    def _extract_listing_urls(
        self,
        soup
    ) -> List[str]:

        urls = []


        for link in soup.find_all(
            "a",
            href=True
        ):

            href = link.get(
                "href"
            )


            if not href:

                continue



            if (
                "/cars/" in href
                or "/vehicle/" in href
                or "/ad/" in href
            ):


                url = urljoin(
                    self.base_url,
                    href
                )


                if url not in urls:

                    urls.append(
                        url
                    )



        return urls




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

            title_tag = soup.find(
                "h1"
            )


            if title_tag:

                title = title_tag.get_text(
                    strip=True
                )



            page_text = soup.get_text(
                " ",
                strip=True
            )



            listing_id = (
                urlparse(url)
                .path
                .rstrip("/")
                .split("/")
                [-1]
            )



            return {

                "listing_id":

                    listing_id,


                "url":

                    url,


                "title":

                    title,


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

                    self._parse_year(
                        page_text
                    ),


                "mileage":

                    self._parse_mileage(
                        page_text
                    ),


                "engine_size":

                    self._parse_engine_size(
                        page_text
                    ),


                "fuel_type":

                    "",


                "transmission":

                    "",


                "body_type":

                    "",


                "location":

                    "Kenya",


                "seller_name":

                    "Jiji",


                "seller_type":

                    "Dealer",


                "condition":

                    "Used"

            }



        except Exception as e:

            logger.error(
                f"Jiji parse error: {e}"
            )

            return {}
