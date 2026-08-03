# app/modules/scraper/cheki.py
# ================================================================
# Auto-D Kenya - Cheki Vehicle Scraper
# ================================================================

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.modules.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class ChekiScraper(BaseScraper):
    """
    Scraper for Cheki Kenya vehicle listings.
    """

    def __init__(self):
        super().__init__(
            source_name="cheki",
            base_url="https://cheki.co.ke"
        )

        self.search_url = "https://cheki.co.ke/cars"

    # ============================================================
    # MAIN SCRAPER
    # ============================================================

    async def scrape(
        self,
        pages: int = 3,
        limit_per_page: int = 20,
    ) -> Dict[str, Any]:

        listings = []

        for page in range(1, pages + 1):

            logger.info(
                "Cheki: scraping page %d",
                page,
            )

            try:

                soup = await self._fetch_page(
                    self.search_url,
                    params={"page": page},
                )

                if soup is None:
                    logger.warning(
                        "Unable to fetch Cheki page %d",
                        page,
                    )
                    continue

                urls = self._extract_urls(
                    soup,
                    ["/car/"],
                )

                logger.info(
                    "Found %d listings on Cheki page %d",
                    len(urls),
                    page,
                )

                for url in urls[:limit_per_page]:

                    listing = await self._parse_listing(url)

                    if listing and listing.get("listing_id"):
                        listings.append(listing)

                    await asyncio.sleep(
                        random.uniform(0.3, 0.8)
                    )

                await asyncio.sleep(
                    random.uniform(1, 2)
                )

            except Exception:
                logger.exception(
                    "Cheki page %d failed",
                    page,
                )

        return {
            "status": "success",
            "source": self.source_name,
            "listings": listings,
            "listings_found": len(listings),
            "listings_saved": 0,
            "completed_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    # ============================================================
    # PARSE VEHICLE
    # ============================================================

    async def _parse_listing(
        self,
        url: str,
    ) -> Optional[Dict[str, Any]]:

        try:

            soup = await self._fetch_page(url)

            if soup is None:
                return None

            # Extract title
            h1 = soup.find("h1")
            title = (
                self._clean_text(h1.get_text())
                if h1
                else ""
            )

            # Get page text for parsing
            page_text = soup.get_text(
                " ",
                strip=True,
            )

            # Extract listing ID safely
            listing_id = (
                urlparse(url)
                .path
                .rstrip("/")
                .split("/")[-1]
            )

            if not listing_id:
                return None

            return self._build_listing(
                listing_id=listing_id,
                title=title,
                url=url,
                price=self._parse_price(page_text),
                year=self._parse_year(page_text),
                mileage=self._parse_mileage(page_text),
                engine_size=self._parse_engine_size(page_text),
                seller_name="Cheki",
            )

        except Exception:
            logger.exception(
                "Failed parsing Cheki listing: %s",
                url,
            )
            return None
