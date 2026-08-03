# app/modules/scraper/jiji.py
# ================================================================
# Auto-D Kenya - Jiji Vehicle Scraper
# ================================================================

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
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

        self.search_url = "https://jiji.co.ke/cars"

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

            logger.info(f"Jiji: scraping page {page}")

            try:

                soup = await self._fetch_page(
                    self.search_url,
                    params={"page": page},
                )

                if soup is None:
                    logger.warning(f"Unable to fetch page {page}")
                    continue

                urls = self._extract_listing_urls(soup)

                logger.info(
                    f"Found {len(urls)} listing URLs on page {page}"
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
                    f"Failed scraping Jiji page {page}"
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
    # EXTRACT LISTING URLS
    # ============================================================

    def _extract_listing_urls(self, soup) -> List[str]:

        urls = []
        seen = set()

        for link in soup.find_all("a", href=True):

            href = link["href"]

            if (
                "/cars/" not in href
                and "/vehicle/" not in href
                and "/ad/" not in href
            ):
                continue

            url = urljoin(
                self.base_url,
                href,
            )

            if url in seen:
                continue

            seen.add(url)
            urls.append(url)

        return urls

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
                "listing_id": urlparse(url).path.rstrip("/").split("/")[-1],
                "title": title,
                "url": url,
                "price": self._parse_price(page_text),
                "currency": "KES",
                "make": None,
                "model": None,
                "year": self._parse_year(page_text),
                "mileage": self._parse_mileage(page_text),
                "engine_size": self._parse_engine_size(page_text),
                "fuel_type": None,
                "transmission": None,
                "body_type": None,
                "location": "Kenya",
                "seller_name": "Jiji",
                "seller_type": "Dealer",
                "condition": "Used",
            }

            return listing

        except Exception:
            logger.exception(
                f"Failed parsing Jiji listing: {url}"
            )
            return None
