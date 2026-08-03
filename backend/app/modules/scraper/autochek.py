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
            base_url="https://autochek.africa/ke"
        )

        # FIXED: Correct URL structure for Autochek
        # The correct URL for car listings in Kenya is:
        # https://autochek.africa/ke/used-cars
        # or https://autochek.africa/ke/new-cars
        self.search_url = "https://autochek.africa/ke/used-cars"
        
        # Also try these if the above doesn't work
        self.fallback_urls = [
            "https://autochek.africa/ke/cars-for-sale",
            "https://autochek.africa/ke/new-cars",
            "https://autochek.africa/ke/inventory",
            "https://autochek.africa/ke/vehicles"
        ]

    # ============================================================
    # RUN METHOD (Called by worker)
    # ============================================================

    async def run(
        self,
        pages: int = 3,
        limit_per_page: int = 20,
    ) -> Dict[str, Any]:
        """
        Run the scraper - entry point for worker.
        """
        return await self.scrape(pages, limit_per_page)

    # ============================================================
    # MAIN SCRAPER
    # ============================================================

    async def scrape(
        self,
        pages: int = 3,
        limit_per_page: int = 20,
    ) -> Dict[str, Any]:

        listings = []
        
        # Try to find working URL first
        working_url = await self._find_working_url()
        if not working_url:
            logger.error("No working URL found for Autochek")
            return {
                "status": "error",
                "source": self.source_name,
                "listings": [],
                "listings_found": 0,
                "listings_saved": 0,
                "error": "No working URL found",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

        for page in range(1, pages + 1):

            logger.info(
                "Autochek: scraping page %d using URL: %s",
                page,
                working_url
            )

            try:
                # FIXED: Use working URL with page parameter
                soup = await self._fetch_page(
                    working_url,
                    params={"page": page}
                )

                if soup is None:
                    logger.warning(
                        "Failed to load Autochek page %d",
                        page,
                    )
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
    # FIND WORKING URL
    # ============================================================

    async def _find_working_url(self) -> Optional[str]:
        """
        Find a working URL for Autochek listings.
        """
        urls_to_try = [self.search_url] + self.fallback_urls
        
        for url in urls_to_try:
            try:
                logger.info(f"Testing URL: {url}")
                # Try to fetch without page parameter first
                soup = await self._fetch_page(url)
                if soup is not None:
                    # Check if we got actual content
                    body_text = soup.get_text(strip=True)
                    if len(body_text) > 100:  # Has real content
                        logger.info(f"Found working URL: {url}")
                        return url
            except Exception as e:
                logger.warning(f"URL {url} failed: {str(e)}")
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

        # FIXED: Better selectors for Autochek
        # Autochek typically uses these patterns
        selectors = [
            'a[href*="/car/"]',
            'a[href*="/used/"]',
            'a[href*="/new/"]',
            'a[href*="/vehicle/"]',
            '.listing-card a',
            '.vehicle-card a',
            '.car-card a',
            '.inventory-item a',
        ]

        for selector in selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    href = element.get("href")
                    if href:
                        url = urljoin(self.base_url, href)
                        # Filter to only listing URLs
                        if self._is_valid_listing_url(url):
                            urls.add(url)
            except Exception:
                continue

        # Fallback: look for any link with car-related keywords
        if not urls:
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href:
                    url = urljoin(self.base_url, href)
                    if self._is_valid_listing_url(url):
                        urls.add(url)

        return list(urls)

    def _is_valid_listing_url(self, url: str) -> bool:
        """
        Check if URL is a valid listing URL.
        """
        # Exclude non-listing URLs
        exclude_patterns = [
            "/login", "/signup", "/register", 
            "/about", "/contact", "/help", 
            "/faq", "/privacy", "/terms",
            "facebook.com", "twitter.com", 
            "instagram.com", "youtube.com",
            "whatsapp.com", "/blog", "/news"
        ]
        
        if any(pattern in url.lower() for pattern in exclude_patterns):
            return False
            
        # Include listing URLs
        include_patterns = [
            "/car/", "/used/", "/new/", 
            "/vehicle/", "/listing/"
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
        details = {
            "year": None,
            "mileage": None,
            "engine_size": None,
            "fuel_type": None,
            "transmission": None,
            "body_type": None,
        }

        # Get page text
        page_text = soup.get_text(" ", strip=True)

        # Extract from page text using regex
        details["year"] = self._parse_year(page_text)
        details["mileage"] = self._parse_mileage(page_text)
        details["engine_size"] = self._parse_engine_size(page_text)

        # Look for specific detail sections
        detail_sections = soup.find_all(["div", "ul", "table"], 
            class_=lambda x: x and any(word in x.lower() for word in 
                ["details", "specs", "features", "info"])
        )

        for section in detail_sections:
            section_text = section.get_text(" ", strip=True)
            
            # Extract fuel type
            if "petrol" in section_text.lower():
                details["fuel_type"] = "Petrol"
            elif "diesel" in section_text.lower():
                details["fuel_type"] = "Diesel"
            elif "electric" in section_text.lower():
                details["fuel_type"] = "Electric"
            elif "hybrid" in section_text.lower():
                details["fuel_type"] = "Hybrid"
            
            # Extract transmission
            if "automatic" in section_text.lower():
                details["transmission"] = "Automatic"
            elif "manual" in section_text.lower():
                details["transmission"] = "Manual"
            
            # Extract body type
            body_types = ["sedan", "suv", "hatchback", "coupe", 
                         "convertible", "truck", "van", "wagon"]
            for body in body_types:
                if body in section_text.lower():
                    details["body_type"] = body.capitalize()
                    break

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
        # Try h1 first
        title_tag = soup.find("h1")
        if title_tag:
            title = self._clean_text(title_tag.get_text())
            if title:
                return title

        # Try meta tags
        meta_title = soup.find("meta", {"property": "og:title"})
        if meta_title:
            content = meta_title.get("content")
            if content:
                return self._clean_text(content)

        # Try title tag
        title_tag = soup.find("title")
        if title_tag:
            title = self._clean_text(title_tag.get_text())
            # Remove site name if present
            if "|" in title:
                title = title.split("|")[0].strip()
            return title

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

        # Common makes in Kenya (organized by length for better matching)
        makes = [
            "Land Rover", "Range Rover", "Mercedes-Benz", "Mercedes", 
            "Toyota", "Nissan", "Honda", "Subaru", "Mazda",
            "BMW", "Audi", "Volkswagen", "Ford", "Mitsubishi", 
            "Isuzu", "Suzuki", "Hyundai", "Kia", "Lexus", "Volvo",
            "Peugeot", "Citroen", "Renault", "Fiat", "Jeep",
            "Chevrolet", "Dodge", "Chrysler", "Porsche", "Jaguar",
            "Bentley", "Ferrari", "Lamborghini", "Maserati",
            "Aston Martin", "Rolls Royce", "Mini", "Smart", "Tesla"
        ]

        title_lower = title.lower()
        
        # Try to find make in title
        for make in makes:
            if make.lower() in title_lower:
                # Extract model (text after make)
                parts = title.split()
                for i, part in enumerate(parts):
                    if part.lower() == make.lower():
                        # Get next part as model
                        if i + 1 < len(parts):
                            model = parts[i + 1]
                            # Clean model (remove special characters)
                            model = ''.join(c for c in model if c.isalnum() or c.isspace())
                            if model and len(model) > 1:
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

            # Extract listing ID
            listing_id = self._extract_listing_id(url, soup)

            # Extract price
            price = self._parse_price(soup.get_text(" ", strip=True))
            
            # Try to get price from specific elements
            if price is None:
                price = self._extract_price_from_page(soup)

            # Extract location
            location = self._extract_location(soup)

            return {
                "listing_id": listing_id,
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
                "location": location,
                "seller_name": "Autochek",
                "seller_type": "Dealer",
                "condition": self._extract_condition(soup),
            }

        except Exception:
            logger.exception(
                "Failed parsing Autochek listing: %s",
                url,
            )
            return None

    # ============================================================
    # EXTRACT LISTING ID
    # ============================================================

    def _extract_listing_id(self, url: str, soup: BeautifulSoup) -> str:
        """
        Extract listing ID from URL or page.
        """
        # Try to get from URL
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        listing_id = path.split("/")[-1]
        
        # Check if it's a valid ID
        if listing_id and len(listing_id) > 2 and listing_id not in ["car", "used", "new", "vehicle"]:
            return listing_id

        # Try to get from meta
        meta_id = soup.find("meta", {"name": "listing-id"})
        if meta_id:
            content = meta_id.get("content")
            if content:
                return content

        # Try to get from hidden input
        hidden_id = soup.find("input", {"type": "hidden", "name": "listing_id"})
        if hidden_id:
            value = hidden_id.get("value")
            if value:
                return value

        # Generate from URL hash
        return str(abs(hash(url)))[:10]

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
            ".price-amount",
            "span.price",
            "div.price",
        ]

        for selector in price_selectors:
            try:
                price_element = soup.select_one(selector)
                if price_element:
                    price_text = price_element.get_text(strip=True)
                    price = self._parse_price(price_text)
                    if price:
                        return price
            except Exception:
                continue

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
            ".city",
            ".area",
            ".region",
        ]

        for selector in location_selectors:
            try:
                location_element = soup.select_one(selector)
                if location_element:
                    location = self._clean_text(location_element.get_text())
                    if location and len(location) > 2:
                        # Check if it looks like a location
                        if any(city in location.lower() for city in 
                            ["nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika", "malindi"]):
                            return location
            except Exception:
                continue

        # Default to Kenya
        return "Kenya"

    # ============================================================
    # EXTRACT CONDITION
    # ============================================================

    def _extract_condition(self, soup: BeautifulSoup) -> str:
        """
        Extract vehicle condition.
        """
        # Check page text for condition indicators
        page_text = soup.get_text(" ", strip=True).lower()
        
        if "brand new" in page_text or "new car" in page_text or "new model" in page_text:
            return "New"
        if "used car" in page_text or "pre-owned" in page_text or "second hand" in page_text:
            return "Used"
        if "certified pre-owned" in page_text or "cpo" in page_text:
            return "Certified Pre-Owned"

        # Check meta data
        meta_condition = soup.find("meta", {"name": "condition"})
        if meta_condition:
            content = meta_condition.get("content", "").lower()
            if "new" in content:
                return "New"
            if "used" in content or "pre-owned" in content:
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
