# app/modules/scraper/cheki.py
# ================================================================
# Auto-D Kenya - Cheki Vehicle Scraper
# ================================================================

import asyncio
import logging
import random
from datetime import datetime, timezone
from urllib.parse import urljoin
from typing import Dict, Any, Optional

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

            logger.info(f"Cheki: scraping page {page}")

            try:

                soup = await self._fetch_page(
                    self.search_url,
                    params={"page": page},
                )

                if soup is None:
                    logger.warning(f"Unable to fetch page {page}")
                    continue

                urls = []
                seen = set()

                for link in soup.find_all("a", href=True):

                    href = link["href"]

                    url = urljoin(
                        self.base_url,
                        href,
                    )

                    if "/car/" not in url:
                        continue

                    if url in seen:
                        continue

                    seen.add(url)
                    urls.append(url)

                logger.info(
                    f"Found {len(urls)} listings on page {page}"
                )

                for url in urls[:limit_per_page]:

                    listing = await self._parse_listing(url)

                    if listing:
                        listings.append(listing)

                    await asyncio.sleep(
                        random.uniform(0.5, 1.2)
                    )

                await asyncio.sleep(
                    random.uniform(1, 2)
                )

            except Exception:
                logger.exception(
                    f"Cheki page {page} failed"
                )

        return {
            "status": "success",
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

            title = ""

            h1 = soup.find("h1")

            if h1:
                title = self._clean_text(
                    h1.get_text()
                )

            page_text = soup.get_text(
                " ",
                strip=True,
            )

            listing = {
                "listing_id": url.rstrip("/").split("/")[-1],
                "title": title,
                "url": url,
                "price": self._parse_price(page_text),
                "currency": "KES",
                "make": None,
                "model": None,
                "year": None,
                "mileage": None,
                "engine_size": None,
                "fuel_type": None,
                "transmission": None,
                "body_type": None,
                "location": "Kenya",
                "seller_name": "Cheki",
                "seller_type": "Dealer",
                "condition": "Used",
            }

            return listing

        except Exception:
            logger.exception(
                f"Failed parsing Cheki listing: {url}"
            )
            return None
