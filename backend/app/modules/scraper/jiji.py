# app/modules/scraper/jiji.py
# Auto-D Kenya - Jiji Scraper
# ================================================================
# TYPE: MODULE - Jiji specific scraper

import asyncio
import random
import logging
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import urljoin

from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class JijiScraper(BaseScraper):
    """Scraper for Jiji Kenya vehicle listings."""

    def __init__(self):
        super().__init__(
            source_name="jiji",
            base_url="https://jiji.co.ke"
        )

        self.search_url = "https://jiji.co.ke/cars"


    async def scrape(
        self,
        pages: int = 3,
        limit_per_page: int = 20
    ) -> Dict[str, Any]:

        listings = []

        for page in range(1, pages + 1):

            logger.info(
                f"Scraping Jiji page {page}"
            )

            try:

                params = {
                    "page": page,
                    "limit": limit_per_page
                }

                soup = await self._fetch_page(
                    self.search_url,
                    params
                )

                if not soup:
                    break


                urls = []

                links = soup.select(
                    "a[data-testid='ad-link']"
                )


                for link in links:

                    href = link.get("href")

                    if href:

                        url = urljoin(
                            self.base_url,
                            href
                        )

                        if url not in urls:
                            urls.append(url)


                logger.info(
                    f"Found {len(urls)} listings"
                )


                for url in urls[:limit_per_page]:

                    listing = await self._parse_listing(url)

                    if listing:
                        listings.append(listing)


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

                continue



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

            soup = await self._fetch_page(url)


            if not soup:
                return {}



            title_elem = soup.select_one(
                "h1[data-testid='ad-title']"
            )

            title = (
                title_elem
                .get_text(strip=True)
                if title_elem
                else ""
            )



            price_elem = soup.select_one(
                "span[data-testid='ad-price']"
            )


            price_text = (
                price_elem
                .get_text(strip=True)
                if price_elem
                else ""
            )


            price = self._parse_price(
                price_text
            )



            details = {}


            sections = soup.select(
                "div[data-testid='ad-attributes'] div"
            )


            for section in sections:

                label = section.select_one(
                    "span[data-testid='attribute-label']"
                )

                value = section.select_one(
                    "span[data-testid='attribute-value']"
                )


                if label and value:

                    key = label.get_text(
                        strip=True
                    ).lower()

                    details[key] = value.get_text(
                        strip=True
                    )



            image = soup.select_one(
                "img[data-testid='ad-image']"
            )


            image_url = (
                image.get("src")
                if image
                else None
            )



            listing_id = (
                url.rstrip("/")
                .split("/")
                [-1]
            )


            if not listing_id:

                listing_id = (
                    f"jiji-{int(datetime.utcnow().timestamp())}"
                )



            return {

                "listing_id":
                    listing_id,


                "title":
                    title,


                "price":
                    price,


                "currency":
                    "KES",


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


                "location":
                    details.get(
                        "location",
                        ""
                    ),


                "url":
                    url,


                "image_url":
                    image_url,


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


                "engine_size":
                    self._parse_engine_size(
                        details.get(
                            "engine",
                            ""
                        )
                    ),


                "seller_name":
                    "",


                "seller_type":
                    "Dealer",


                "condition":
                    "Used"

            }



        except Exception as e:

            logger.error(
                f"Parse listing failed {url}: {e}"
            )

            return {}
