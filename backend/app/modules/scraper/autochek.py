# app/modules/scraper/autochek.py
# ================================================================
# Auto-D Kenya - Autochek Scraper
# ================================================================

import asyncio
import logging
import random
from datetime import datetime, timezone
from urllib.parse import urljoin
from typing import Dict, Any, Optional

from app.modules.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class AutochekScraper(BaseScraper):
    """
    Scraper for Autochek Kenya vehicle listings.
    """

    def __init__(self):
        super().__init__(
            source_name="autochek",
            base_url="https://autochek.africa"
        )

        self.search_url = "https://autochek.africa/ke/cars"

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

            logger.info(f"Autochek: scraping page {page}")

            try:

                soup = await self._fetch_page(
                    self.search_url,
                    params={"page": page},
                )

                if soup is None:
                    logger.warning(f"Failed to load page {page}")
                    continue

                urls = []
                seen = set()

                for link in soup.find_all("a", href=True):

                    href = link["href"]

                    url = urljoin(
                        self.base_url,
                        href,
                    )

                    if "/cars/" not in url:
                        continue

                    if url in seen:
                        continue

                    seen.add(url)
                    urls.append(url)

                logger.info(
                    f"Found {len(urls)} vehicle links on page {page}"
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
                    f"Autochek page {page} failed"
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
    # PARSE LISTING
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

            title_tag = soup.find("h1")

            if title_tag:
                title = self._clean_text(
                    title_tag.get_text()
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
                "seller_name": "Autochek",
                "seller_type": "Dealer",
                "condition": "Used",
            }

            return listing

        except Exception:
            logger.exception(
                f"Failed parsing Autochek listing: {url}"
            )
            return None
