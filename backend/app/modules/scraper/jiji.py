# app/modules/scraper/jiji.py
# ================================================================
# Auto-D Kenya - Jiji Vehicle Scraper
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

            logger.info(
                "Jiji: scraping page %d",
                page,
            )

            try:

                soup = await self._fetch_page(
                    self.search_url,
                    params={"page": page},
                )

                if soup is None:
                    logger.warning(
                        "Unable to fetch Jiji page %d",
                        page,
                    )
                    continue

                urls = self._extract_urls(
                    soup,
                    [
                        "/cars/",
                        "/vehicle/",
                        "/ad/",
                    ],
                )

                logger.info(
                    "Found %d unique listings on Jiji page %d",
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
                    "Failed scraping Jiji page %d",
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

            # Parse price
            price = self._parse_price(page_text)

            # Parse vehicle details
            year = self._parse_year(page_text)
            mileage = self._parse_mileage(page_text)
            engine_size = self._parse_engine_size(page_text)

            # Jiji sometimes has different text patterns
            # Try to find more specific details
            details = self._extract_jiji_details(soup)

            # Combine with base details
            if details:
                year = details.get("year") or year
                mileage = details.get("mileage") or mileage
                engine_size = details.get("engine_size") or engine_size

            return self._build_listing(
                listing_id=listing_id,
                title=title,
                url=url,
                price=price,
                year=year,
                mileage=mileage,
                engine_size=engine_size,
                seller_name="Jiji",
                seller_type="Dealer",
            )

        except Exception:
            logger.exception(
                "Failed parsing Jiji listing: %s",
                url,
            )
            return None

    # ============================================================
    # EXTRACT JIJI-SPECIFIC DETAILS
    # ============================================================

    def _extract_jiji_details(
        self,
        soup: BeautifulSoup,
    ) -> Dict[str, Any]:
        """
        Extract Jiji-specific vehicle details from the listing page.
        Jiji often has structured data in specific HTML elements.
        """
        details = {
            "year": None,
            "mileage": None,
            "engine_size": None,
            "fuel_type": "",
            "transmission": "",
            "body_type": "",
        }

        try:
            # Look for detail rows in Jiji's listing format
            # Jiji often uses table-like structures or divs with specific classes
            detail_elements = soup.find_all(
                ["div", "li", "tr"],
                class_=lambda c: c and (
                    "detail" in c.lower() or 
                    "spec" in c.lower() or 
                    "attribute" in c.lower() or
                    "info" in c.lower()
                )
            )

            for elem in detail_elements:
                text = self._clean_text(elem.get_text())
                text_lower = text.lower()

                if "year" in text_lower:
                    # Try to extract year
                    import re
                    match = re.search(r'year\s*[:.]?\s*(\d{4})', text, re.IGNORECASE)
                    if match:
                        try:
                            details["year"] = int(match.group(1))
                        except ValueError:
                            pass

                if "mileage" in text_lower or "kilometer" in text_lower:
                    import re
                    match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*km', text, re.IGNORECASE)
                    if match:
                        try:
                            details["mileage"] = int(match.group(1).replace(",", ""))
                        except ValueError:
                            pass

                if "engine" in text_lower:
                    import re
                    match = re.search(r'(\d+\.?\d*)\s*l', text, re.IGNORECASE)
                    if match:
                        try:
                            details["engine_size"] = float(match.group(1))
                        except ValueError:
                            pass

                if "fuel" in text_lower:
                    if "petrol" in text_lower or "gasoline" in text_lower:
                        details["fuel_type"] = "Petrol"
                    elif "diesel" in text_lower:
                        details["fuel_type"] = "Diesel"
                    elif "electric" in text_lower:
                        details["fuel_type"] = "Electric"
                    elif "hybrid" in text_lower:
                        details["fuel_type"] = "Hybrid"

                if "transmission" in text_lower:
                    if "automatic" in text_lower:
                        details["transmission"] = "Automatic"
                    elif "manual" in text_lower:
                        details["transmission"] = "Manual"
                    elif "cvt" in text_lower:
                        details["transmission"] = "CVT"

                if "body" in text_lower or "type" in text_lower:
                    body_types = ["suv", "sedan", "hatchback", "pickup", "truck", 
                                  "coupe", "convertible", "van", "mpv", "wagon"]
                    for bt in body_types:
                        if bt in text_lower:
                            details["body_type"] = bt.capitalize()
                            break

        except Exception as e:
            logger.debug(f"Error extracting Jiji details: {e}")

        return details

    # ============================================================
    # OVERRIDE: PARSE YEAR
    # ============================================================

    def _parse_year(
        self,
        text: str,
    ) -> Optional[int]:
        """
        Parse year from Jiji listing text.
        Override base method if needed for Jiji-specific format.
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
        Parse mileage from Jiji listing text.
        Override base method if needed for Jiji-specific format.
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
        Parse engine size from Jiji listing text.
        Override base method if needed for Jiji-specific format.
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
        Parse price from Jiji listing text.
        Override base method if needed for Jiji-specific format.
        """
        return super()._parse_price(text)
