# app/modules/scraper/autochek.py
# ================================================================
# Auto-D Kenya - Autochek Scraper
# ================================================================

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

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

        # FIX: Updated URL - Autochek uses '/ke/cars-for-sale' or similar
        self.search_url = "https://autochek.africa/ke/cars-for-sale"
        # Alternative URLs to try if the above doesn't work:
        # self.search_url = "https://autochek.africa/ke/used-cars"
        # self.search_url = "https://autochek.africa/ke/new-cars"
        # self.search_url = "https://autochek.africa/ke/inventory"

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
                "Autochek: scraping page %d",
                page,
            )

            try:

                # FIX: Try different URL patterns if the main one fails
                soup = await self._fetch_page_with_fallback(page)
                
                if soup is None:
                    logger.warning(
                        "Failed to load Autochek page %d after trying all URL patterns",
                        page,
                    )
                    # Try the next page anyway
                    continue

                urls = self._extract_listing_urls(soup)
                
                # Deduplicate URLs
                unique_urls = list(dict.fromkeys(urls))

                logger.info(
                    "Found %d unique vehicle links on Autochek page %d",
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
                    "Autochek page %d failed",
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
    # FETCH PAGE WITH FALLBACK URLS
    # ============================================================

    async def _fetch_page_with_fallback(
        self,
        page: int,
    ) -> Optional[BeautifulSoup]:
        """
        Try multiple URL patterns if the main one fails.
        """
        # List of possible URL patterns
        url_patterns = [
            "https://autochek.africa/ke/cars-for-sale",
            "https://autochek.africa/ke/used-cars",
            "https://autochek.africa/ke/new-cars",
            "https://autochek.africa/ke/inventory",
            "https://autochek.africa/ke/vehicles",
            "https://autochek.africa/ke/cars",  # Original (might still work with different params)
        ]

        for base_url in url_patterns:
            try:
                # FIX: Some sites use page in path, others use query params
                # Try both formats
                for url_format in [
                    f"{base_url}?page={page}",
                    f"{base_url}/{page}",
                    f"{base_url}?p={page}",
                    f"{base_url}?page_number={page}",
                ]:
                    try:
                        logger.debug(f"Trying URL: {url_format}")
                        soup = await self._fetch_page(url_format)
                        if soup is not None:
                            # Check if we got actual content (not empty)
                            if soup.find("body") and len(soup.get_text(strip=True)) > 100:
                                logger.info(f"Successfully fetched: {url_format}")
                                return soup
                    except Exception:
                        continue
            except Exception:
                continue

        return None

    # ============================================================
    # EXTRACT LISTING URLS
    # ============================================================

    def _extract_listing_urls(
        self,
        soup: BeautifulSoup,
    ) -> List[str]:
        """
        Extract listing URLs from the Autochek page.
        """
        urls: Set[str] = set()

        # FIX: Look for listing links with multiple possible selectors
        # Common selectors for car listings
        selectors = [
            "a[href*='/car/']",
            "a[href*='/vehicle/']",
            "a[href*='/listing/']",
            "a[href*='/cars/']",
            "a[href*='/ke/car/']",
            "a[href*='/ke/vehicle/']",
            ".listing-card a",  # Class-based selectors
            ".vehicle-card a",
            ".car-card a",
        ]

        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                href = element.get("href")
                if href:
                    url = urljoin(self.base_url, href)
                    # FIX: Only add valid listing URLs
                    if self._is_valid_listing_url(url):
                        urls.add(url)

        # Fallback: if no URLs found with selectors, look for any link containing car identifiers
        if not urls:
            for link in soup.find_all("a", href=True):
                href = link["href"]
                url = urljoin(self.base_url, href)
                if self._is_valid_listing_url(url):
                    urls.add(url)

        return list(urls)

    def _is_valid_listing_url(self, url: str) -> bool:
        """
        Check if URL is a valid listing URL.
        """
        # FIX: Exclude non-listing URLs
        exclude_patterns = [
            "/login",
            "/signup",
            "/register",
            "/about",
            "/contact",
            "/help",
            "/faq",
            "/privacy",
            "/terms",
            "facebook.com",
            "twitter.com",
            "instagram.com",
            "youtube.com",
        ]
        
        if any(pattern in url.lower() for pattern in exclude_patterns):
            return False
            
        # Include listing URLs
        include_patterns = [
            "/car/",
            "/vehicle/",
            "/listing/",
            "/cars/",
        ]
        
        return any(pattern in url.lower() for pattern in include_patterns)

    # ============================================================
    # EXTRACT VEHICLE DETAILS
    # ============================================================

    def _extract_vehicle_details(
        self,
        soup: BeautifulSoup,
    ) -> Dict[str, Any]:
        """
        Extract all vehicle details from page.
        """
        # FIX: Search for specific elements on the page
        details = {
            "year": None,
            "mileage": None,
            "engine_size": None,
            "fuel_type": None,
            "transmission": None,
            "body_type": None,
        }

        # Look for detail sections
        detail_selectors = [
            ".vehicle-details",
            ".car-details",
            ".specs",
            ".features",
        ]

        for selector in detail_selectors:
            detail_section = soup.select_one(selector)
            if detail_section:
                text = detail_section.get_text(" ", strip=True)
                # Parse details from text
                details["year"] = self._parse_year(text)
                details["mileage"] = self._parse_mileage(text)
                details["engine_size"] = self._parse_engine_size(text)
                break

        # If no detail section found, parse from entire page
        if details["year"] is None:
            page_text = soup.get_text(" ", strip=True)
            details["year"] = self._parse_year(page_text)
            details["mileage"] = self._parse_mileage(page_text)
            details["engine_size"] = self._parse_engine_size(page_text)

        return details

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
        # FIX: Try multiple title selectors
        title_selectors = [
            "h1",
            ".vehicle-title",
            ".car-title",
            ".listing-title",
            "h1[itemprop='name']",
            ".product-title",
        ]

        for selector in title_selectors:
            title_tag = soup.select_one(selector)
            if title_tag:
                title = self._clean_text(title_tag.get_text())
                if title:
                    return title

        # Fallback: try meta tags
        meta_title = soup.find("meta", {"property": "og:title"})
        if meta_title:
            title = meta_title.get("content")
            if title:
                return self._clean_text(title)

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
                        # FIX: Return model if next word exists, otherwise return empty
                        if i + 1 < len(title_words):
                            # Skip common words that might follow the make
                            model = title_words[i + 1]
                            # Remove common suffixes
                            common_suffixes = ["for", "with", "in", "at", "from", "on"]
                            if model.lower() not in common_suffixes:
                                return make, model
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

            if not title:
                logger.warning(f"No title found for listing: {url}")
                return None

            # Get vehicle details
            details = self._extract_vehicle_details(soup)

            # Extract make and model from title
            make, model = self._extract_make_model(title)

            # Extract listing ID safely
            path = urlparse(url).path.rstrip("/")
            listing_id = path.split("/")[-1]
            
            # FIX: Better listing ID extraction
            if not listing_id or listing_id in ["car", "vehicle", "listing"]:
                # Try to get ID from URL parameters
                parsed_url = urlparse(url)
                if parsed_url.query:
                    import urllib.parse
                    params = urllib.parse.parse_qs(parsed_url.query)
                    if "id" in params:
                        listing_id = params["id"][0]
                    elif "listing_id" in params:
                        listing_id = params["listing_id"][0]

            # Validate listing ID
            if not listing_id or len(listing_id) < 3:
                # Fallback: use URL hash
                listing_id = str(hash(url))[:8]

            # Extract price with multiple methods
            price = self._extract_price_from_page(soup)
            if price is None:
                price = self._parse_price(soup.get_text(" ", strip=True))

            return {
                "listing_id": str(listing_id),
                "title": title,
                "url": url,
                "price": price,
                "currency": "KES",
                "make": make,
                "model": model,
                "year": details.get("year"),
                "mileage": details.get("mileage"),
                "engine_size": details.get("engine_size"),
                "fuel_type": details.get("fuel_type") or "",
                "transmission": details.get("transmission") or "",
                "body_type": details.get("body_type") or "",
                "location": self._extract_location(soup),
                "seller_name": "Autochek",
                "seller_type": "Dealer",
                "condition": self._extract_condition(soup, details),
            }

        except Exception:
            logger.exception(
                "Failed parsing Autochek listing: %s",
                url,
            )
            return None

    # ============================================================
    # EXTRACT PRICE FROM PAGE
    # ============================================================

    def _extract_price_from_page(self, soup: BeautifulSoup) -> Optional[float]:
        """
        Extract price from specific price elements on the page.
        """
        price_selectors = [
            ".price",
            ".vehicle-price",
            ".car-price",
            ".listing-price",
            "[itemprop='price']",
            ".product-price",
            ".amount",
            ".sale-price",
        ]

        for selector in price_selectors:
            price_element = soup.select_one(selector)
            if price_element:
                price_text = price_element.get_text(strip=True)
                price = self._parse_price(price_text)
                if price:
                    return price

        return None

    # ============================================================
    # EXTRACT LOCATION
    # ============================================================

    def _extract_location(self, soup: BeautifulSoup) -> str:
        """
        Extract location from the page.
        """
        location_selectors = [
            ".location",
            ".vehicle-location",
            "[itemprop='location']",
            ".address",
            ".seller-location",
        ]

        for selector in location_selectors:
            location_element = soup.select_one(selector)
            if location_element:
                location = self._clean_text(location_element.get_text())
                if location and len(location) > 2:
                    return location

        return "Kenya"

    # ============================================================
    # EXTRACT CONDITION
    # ============================================================

    def _extract_condition(self, soup: BeautifulSoup, details: Dict) -> str:
        """
        Extract vehicle condition.
        """
        # Check for condition indicators
        condition_selectors = [
            ".condition",
            ".vehicle-condition",
            "[itemprop='vehicleCondition']",
        ]

        for selector in condition_selectors:
            condition_element = soup.select_one(selector)
            if condition_element:
                condition = self._clean_text(condition_element.get_text()).lower()
                if "new" in condition:
                    return "New"
                if "used" in condition or "pre-owned" in condition:
                    return "Used"

        # Check page text
        page_text = soup.get_text(" ", strip=True).lower()
        if "brand new" in page_text or "new car" in page_text:
            return "New"
        if "used car" in page_text or "pre-owned" in page_text:
            return "Used"

        return "Used"

    # ============================================================
    # OVERRIDE: PARSE YEAR
    # ============================================================

    def _parse_year(
        self,
        text: str,
    ) -> Optional[int]:
        """
        Parse year from Autochek listing text.
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
        Parse mileage from Autochek listing text.
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
        Parse engine size from Autochek listing text.
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
        Parse price from Autochek listing text.
        """
        return super()._parse_price(text)
