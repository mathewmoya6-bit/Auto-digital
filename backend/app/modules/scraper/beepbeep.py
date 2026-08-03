# app/modules/scraper/beepbeep.py
# ================================================================
# Auto-D Kenya - BeepBeep Vehicle Scraper
# ================================================================

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.modules.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class BeepBeepScraper(BaseScraper):
    """
    Scraper for BeepBeep Kenya vehicle listings.
    """

    def __init__(self):
        super().__init__(
            source_name="beepbeep",
            base_url="https://beepbeep.co.ke",
        )

        self.search_url = "https://beepbeep.co.ke/vehicles"

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
                "BeepBeep: scraping page %d",
                page,
            )

            try:

                soup = await self._fetch_page(
                    self.search_url,
                    params={"page": page},
                )

                if soup is None:
                    logger.warning(
                        "Unable to fetch BeepBeep page %d",
                        page,
                    )
                    continue

                urls = self._extract_listing_urls(soup)
                
                # Deduplicate URLs
                unique_urls = list(dict.fromkeys(urls))

                logger.info(
                    "Found %d unique listings on BeepBeep page %d",
                    len(unique_urls),
                    page,
                )

                for url in unique_urls[:limit_per_page]:

                    listing = await self._parse_listing(url)

                    # Skip invalid listings
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
                    "Failed scraping BeepBeep page %d",
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
    # EXTRACT LISTING URLS
    # ============================================================

    def _extract_listing_urls(
        self,
        soup: BeautifulSoup,
    ) -> List[str]:
        """
        Extract listing URLs from the BeepBeep page.
        """
        urls: Set[str] = set()

        for link in soup.find_all("a", href=True):

            href = link["href"]

            url = urljoin(
                self.base_url,
                href,
            )

            if (
                "/vehicle/" not in url
                and "/car/" not in url
            ):
                continue

            urls.add(url)

        return list(urls)

    # ============================================================
    # EXTRACT VEHICLE DETAILS
    # ============================================================

    def _extract_vehicle_details(
        self,
        text: str,
    ) -> Dict[str, Any]:
        """
        Extract all vehicle details from page text.
        """
        return {
            "year": self._parse_year(text),
            "mileage": self._parse_mileage(text),
            "engine_size": self._parse_engine_size(text),
        }

    # ============================================================
    # EXTRACT TITLE
    # ============================================================

    def _extract_title(
        self,
        soup: BeautifulSoup,
    ) -> str:
        """
        Extract vehicle title from the page.
        """
        h1 = soup.find("h1")
        if h1:
            return self._clean_text(h1.get_text())
        return ""

    # ============================================================
    # EXTRACT MAKE AND MODEL FROM TITLE
    # ============================================================

    def _extract_make_model(
        self,
        title: str,
    ) -> tuple:
        """
        Extract make and model from the title.
        """
        if not title:
            return "", ""

        # Common makes in Kenya
        makes = [
            "Toyota", "Nissan", "Honda", "Subaru", "Mazda",
            "Mercedes", "BMW", "Audi", "Volkswagen", "Ford",
            "Mitsubishi", "Isuzu", "Suzuki", "Hyundai", "Kia",
            "Land Rover", "Jaguar", "Porsche", "Lexus", "Volvo",
            "Peugeot", "Citroen", "Renault", "Fiat", "Jeep",
            "Range Rover", "Chevrolet", "Dodge", "Chrysler",
            "Bentley", "Ferrari", "Lamborghini", "Maserati",
            "Aston Martin", "Rolls Royce", "Mini", "Smart"
        ]

        title_lower = title.lower()
        title_words = title.split()

        for make in makes:
            if make.lower() in title_lower:
                for i, word in enumerate(title_words):
                    if word.lower() == make.lower():
                        if i + 1 < len(title_words):
                            return make, title_words[i + 1]
                        return make, ""

        return "", ""

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

            # Extract title
            title = self._extract_title(soup)

            # Get page text for parsing
            page_text = soup.get_text(
                " ",
                strip=True,
            )

            # Extract vehicle details
            details = self._extract_vehicle_details(page_text)

            # Extract make and model from title
            make, model = self._extract_make_model(title)

            # Extract listing ID safely
            listing_id = (
                urlparse(url)
                .path
                .rstrip("/")
                .split("/")[-1]
            )

            # Validate listing ID
            if not listing_id:
                return None

            return {
                "listing_id": listing_id,
                "title": title,
                "url": url,
                "price": self._parse_price(page_text),
                "currency": "KES",
                "make": make,
                "model": model,
                "year": details.get("year"),
                "mileage": details.get("mileage"),
                "engine_size": details.get("engine_size"),
                "fuel_type": "",
                "transmission": "",
                "body_type": "",
                "location": "Kenya",
                "seller_name": "BeepBeep",
                "seller_type": "Dealer",
                "condition": "Used",
            }

        except Exception:
            logger.exception(
                "Failed parsing BeepBeep listing: %s",
                url,
            )
            return None

    # ============================================================
    # OVERRIDE: PARSE YEAR
    # ============================================================

    def _parse_year(
        self,
        text: str,
    ) -> Optional[int]:
        """
        Parse year from BeepBeep listing text.
        Override base method if needed for BeepBeep-specific format.
        """
        return super()._parse_year(text)

    # ============================================================
    # OVERRIDE: PARSE MILEAGE
    # ============================================================

    def _parse_mileage(
        self,
        text: str,
    ) -> Optional[int]:
        """
        Parse mileage from BeepBeep listing text.
        Override base method if needed for BeepBeep-specific format.
        """
        return super()._parse_mileage(text)

    # ============================================================
    # OVERRIDE: PARSE ENGINE SIZE
    # ============================================================

    def _parse_engine_size(
        self,
        text: str,
    ) -> Optional[float]:
        """
        Parse engine size from BeepBeep listing text.
        Override base method if needed for BeepBeep-specific format.
        """
        return super()._parse_engine_size(text)

    # ============================================================
    # OVERRIDE: PARSE PRICE
    # ============================================================

    def _parse_price(
        self,
        text: str,
    ) -> Optional[float]:
        """
        Parse price from BeepBeep listing text.
        Override base method if needed for BeepBeep-specific format.
        """
        return super()._parse_price(text)
