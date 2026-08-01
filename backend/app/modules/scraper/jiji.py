# app/modules/scraper/jiji.py
# ================================================================
# Auto-D Kenya - Jiji Vehicle Scraper
# ================================================================

import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Any
from urllib.parse import urljoin

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

                    continue



                urls = []


                links = soup.select(
                    "a[data-testid='ad-link']"
                )


                for link in links:

                    href = link.get(
                        "href"
                    )


                    if href:

                        url = urljoin(
                            self.base_url,
                            href
                        )


                        if url not in urls:

                            urls.append(url)



                logger.info(
                    f"Found {len(urls)} Jiji links"
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

                logger.error(
                    f"Jiji page error: {e}"
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
        url: str
    ) -> Dict[str, Any]:

        try:

            soup = await self._fetch_page(
                url
            )


            if not soup:

                return {}



            title = ""

            title_element = soup.select_one(
                "h1[data-testid='ad-title']"
            )


            if title_element:

                title = title_element.get_text(
                    strip=True
                )



            price = None

            price_element = soup.select_one(
                "span[data-testid='ad-price']"
            )


            if price_element:

                price = self._parse_price(
                    price_element.get_text(
                        strip=True
                    )
                )



            details = {}


            attributes = soup.select(
                "div[data-testid='ad-attributes'] div"
            )


            for item in attributes:

                label = item.select_one(
                    "span[data-testid='attribute-label']"
                )

                value = item.select_one(
                    "span[data-testid='attribute-value']"
                )


                if label and value:

                    key = label.get_text(
                        strip=True
                    ).lower()


                    val = value.get_text(
                        strip=True
                    )


                    details[key] = val



            listing_id = (
                url.rstrip("/")
                .split("/")
                [-1]
            )


            image = soup.select_one(
                "img[data-testid='ad-image']"
            )


            image_url = None

            if image:

                image_url = image.get(
                    "src"
                )



            return {

                "listing_id":
                    listing_id,


                "title":
                    title,


                "url":
                    url,


                "price":
                    price,


                "currency":
                    "KES",


                "make":
                    details.get(
                        "make",
                        ""
                    ),


                "model":
                    details.get(
                        "model",
                        ""
                    ),


                "year":
                    self._parse_year(
                        details.get(
                            "year",
                            ""
                        )
                    ),


                "mileage":
                    self._parse_mileage(
                        details.get(
                            "mileage",
                            ""
                        )
                    ),


                "engine_size":
                    self._parse_engine_size(
                        details.get(
                            "engine",
                            ""
                        )
                    ),


                "fuel_type":
                    details.get(
                        "fuel type",
                        ""
                    ),


                "transmission":
                    details.get(
                        "transmission",
                        ""
                    ),


                "body_type":
                    details.get(
                        "body type",
                        ""
                    ),


                "location":
                    details.get(
                        "location",
                        ""
                    ),


                "seller_name":
                    "",


                "seller_type":
                    "Dealer",


                "condition":
                    "Used",


                "image_url":
                    image_url
            }



        except Exception as e:

            logger.error(
                f"Jiji parse error {url}: {e}"
            )

            return {}
