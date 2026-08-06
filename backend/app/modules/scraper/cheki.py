# app/modules/scraper/cheki.py
# ================================================================
# Auto-D Kenya - Cheki Vehicle Scraper
# ================================================================

import asyncio
import logging
import random
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set
from urllib.parse import urlparse

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
        
        # Alternative URLs if the main one doesn't work
        self.fallback_urls = [
            "https://cheki.co.ke/used-cars",
            "https://cheki.co.ke/vehicles",
            "https://cheki.co.ke/listings",
            "https://cheki.co.ke/cars-for-sale"
        ]

    # ============================================================
    # RUN METHOD REMOVED - Inherited from BaseScraper
    # ============================================================

    # ============================================================
    # MAIN SCRAPER
    # ============================================================

    async def scrape(
        self,
        pages: int = 3,
        limit_per_page: int = 20,
    ) -> Dict[str, Any]:

        listings = []
        
        try:
            # Find a working URL first
            working_url = await self._find_working_url()
            if not working_url:
                logger.error("No working URL found for Cheki")
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
                    "Cheki: scraping page %d using URL: %s",
                    page,
                    working_url
                )

                try:
                    # Try different pagination formats
                    soup = await self._fetch_page_with_pagination(working_url, page)

                    if soup is None:
                        logger.warning(
                            "Unable to fetch Cheki page %d",
                            page,
                        )
                        continue

                    # Extract URLs
                    urls = self._extract_listing_urls(soup)

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
            
        finally:
            # Clean up HTTP client
            await self.close()

    # ============================================================
    # FIND WORKING URL
    # ============================================================

    async def _find_working_url(self) -> Optional[str]:
        """
        Find a working URL for Cheki listings.
        """
        urls_to_try = [self.search_url] + self.fallback_urls
        
        for url in urls_to_try:
            try:
                logger.info(f"Testing URL: {url}")
                soup = await self.fetch_soup(url)
                if soup is not None:
                    # Check if we got actual content
                    body_text = soup.get_text(strip=True)
                    if len(body_text) > 100:  # Has real content
                        # Check if it contains car listings
                        if self._has_listings(soup):
                            logger.info(f"Found working URL: {url}")
                            return url
            except Exception as e:
                logger.warning(f"URL {url} failed: {str(e)}")
                continue
        
        return None

    def _has_listings(self, soup: BeautifulSoup) -> bool:
        """
        Check if the page contains car listings.
        """
        # Look for common listing indicators
        indicators = [
            "car", "vehicle", "listing", "inventory",
            "for sale", "used cars", "new cars"
        ]
        
        text = soup.get_text(strip=True).lower()
        return any(indicator in text for indicator in indicators)

    # ============================================================
    # FETCH PAGE WITH PAGINATION
    # ============================================================

    async def _fetch_page_with_pagination(
        self,
        base_url: str,
        page: int
    ) -> Optional[BeautifulSoup]:
        """
        Try different pagination formats.
        """
        # Common pagination formats for Cheki
        pagination_formats = [
            f"{base_url}?page={page}",
            f"{base_url}?p={page}",
            f"{base_url}?page_number={page}",
            f"{base_url}?offset={page * 20}",
            f"{base_url}/page/{page}",
            f"{base_url}/{page}",
            f"{base_url}?start={page * 20}",
        ]

        for url in pagination_formats:
            try:
                logger.debug(f"Trying pagination URL: {url}")
                soup = await self.fetch_soup(url)
                if soup is not None:
                    # Check if we got actual content with listings
                    if self._has_listings(soup):
                        return soup
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
        Extract listing URLs from the Cheki page.
        """
        urls: Set[str] = set()

        # Cheki specific selectors
        selectors = [
            'a[href*="/car/"]',
            'a[href*="/vehicle/"]',
            'a[href*="/listing/"]',
            'a[href*="/cars/"]',
            'a[href*="/used/"]',
            '.car-card a',
            '.vehicle-card a',
            '.listing-card a',
            '.inventory-item a',
            '.car-item a',
            '.vehicle-item a',
            'a.listing-link',
            'a.vehicle-link',
            '.card a[href*="/car"]',
            '.card a[href*="/vehicle"]',
            '.ad a',
            '.listing a',
        ]

        for selector in selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    href = element.get("href")
                    if href:
                        url = self.absolute_url(href)  # Use BaseScraper method
                        if self._is_valid_listing_url(url):
                            urls.add(url)
            except Exception:
                continue

        # Fallback: look for any link with car-related keywords
        if not urls:
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href:
                    url = self.absolute_url(href)
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
            "whatsapp.com", "/blog", "/news",
            "/category", "/tag", "/author",
            "/profile", "/account", "/dashboard",
        ]
        
        if any(pattern in url.lower() for pattern in exclude_patterns):
            return False
            
        # Include listing URLs
        include_patterns = [
            "/car/", "/vehicle/", "/listing/",
            "/cars/", "/vehicles/", "/used/",
            "/new/", "/ad/", "/view/",
        ]
        
        return any(pattern in url.lower() for pattern in include_patterns)

    # ============================================================
    # PARSE VEHICLE
    # ============================================================

    async def _parse_listing(
        self,
        url: str,
    ) -> Optional[Dict[str, Any]]:

        try:
            soup = await self.fetch_soup(url)  # FIXED: use fetch_soup

            if soup is None:
                return None

            # Extract title using BaseScraper method
            title = self._extract_title(soup)

            if not title:
                logger.warning(f"No title found for listing: {url}")
                return None

            # Get page text for parsing
            page_text = soup.get_text(" ", strip=True)

            # Extract listing ID
            listing_id = self._extract_listing_id(url, soup)

            if not listing_id:
                return None

            # Extract make and model
            make, model = self._extract_make_model(title)

            # Extract price - FIXED: returns int
            price = self._extract_price(soup, page_text)

            # Extract vehicle details using BaseScraper methods
            details = self._extract_vehicle_details(soup, page_text)

            # Extract location using BaseScraper method
            location = self._extract_location(soup, page_text)

            # Extract seller info
            seller_name, seller_type = self._extract_seller_info(soup, page_text)

            # Extract condition
            condition = self._extract_condition(soup, page_text)

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
                "seller_name": seller_name,
                "seller_type": seller_type,
                "condition": condition,
            }

        except Exception:
            logger.exception(
                "Failed parsing Cheki listing: %s",
                url,
            )
            return None

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
        h1 = soup.find("h1")
        if h1:
            title = self.clean_text(h1.get_text())  # FIXED: use clean_text
            if title and len(title) > 2:
                return title

        # Try meta tags
        meta_title = soup.find("meta", {"property": "og:title"})
        if meta_title:
            content = meta_title.get("content")
            if content:
                title = self.clean_text(content)
                if title:
                    return title

        # Try title tag
        title_tag = soup.find("title")
        if title_tag:
            title = self.clean_text(title_tag.get_text())
            # Remove site name and separators
            for separator in ["|", "-", "–", "—", "::"]:
                if separator in title:
                    title = title.split(separator)[0].strip()
                    break
            if title:
                return title

        return ""

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
        
        # Check if it's a valid ID (not a common word)
        common_words = ["car", "used", "new", "vehicle", "listing", "cars", "vehicles", "view"]
        if listing_id and len(listing_id) > 2 and listing_id.lower() not in common_words:
            # Check if it's numeric or alphanumeric
            if re.match(r'^[a-zA-Z0-9\-_]+$', listing_id):
                return listing_id

        # Try to get from meta
        meta_id = soup.find("meta", {"name": "listing-id"})
        if meta_id:
            content = meta_id.get("content")
            if content:
                return content

        meta_id = soup.find("meta", {"property": "listing:id"})
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

        # Try to get from data attribute
        data_id = soup.find(attrs={"data-listing-id": True})
        if data_id:
            return data_id.get("data-listing-id")

        # Generate from URL hash
        return str(abs(hash(url)))[:10]

    # ============================================================
    # EXTRACT PRICE
    # ============================================================

    def _extract_price(
        self,
        soup: BeautifulSoup,
        page_text: str
    ) -> Optional[int]:  # FIXED: returns int, not float
        """
        Extract price from the page.
        """
        # Try specific price selectors
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
            ".cost",
            ".price-display",
            ".currency-value",
            ".listing-price",
            ".ad-price",
        ]

        for selector in price_selectors:
            try:
                price_element = soup.select_one(selector)
                if price_element:
                    price_text = price_element.get_text(strip=True)
                    price = self.parse_price(price_text)  # FIXED: use parse_price
                    if price:
                        return int(price)
            except Exception:
                continue

        # Try to find price in page text with Cheki-specific patterns
        price_patterns = [
            r'KSh\s*([\d,]+\.?\d*)',
            r'KES\s*([\d,]+\.?\d*)',
            r'Kenya Shillings\s*([\d,]+\.?\d*)',
            r'Price:\s*KSh\s*([\d,]+\.?\d*)',
            r'Price:\s*KES\s*([\d,]+\.?\d*)',
            r'Price:\s*([\d,]+\.?\d*)\s*KES',
            r'([\d,]+\.?\d*)\s*KSh',
            r'([\d,]+\.?\d*)\s*KES',
            r'KSh\s*([\d,]+\.?\d*)\s*/=',
            r'([\d,]+\.?\d*)\s*/=',
            r'KSh\.?\s*([\d,]+\.?\d*)',
        ]

        for pattern in price_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(',', '').replace(' ', '')
                try:
                    return int(float(price_str))  # FIXED: return int
                except ValueError:
                    continue

        return None

    # ============================================================
    # EXTRACT MAKE AND MODEL
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
            "Land Rover", "Range Rover", "Mercedes-Benz", "Mercedes",
            "Toyota", "Nissan", "Honda", "Subaru", "Mazda",
            "BMW", "Audi", "Volkswagen", "Ford", "Mitsubishi",
            "Isuzu", "Suzuki", "Hyundai", "Kia", "Lexus", "Volvo",
            "Peugeot", "Citroen", "Renault", "Fiat", "Jeep",
            "Chevrolet", "Dodge", "Chrysler", "Porsche", "Jaguar",
            "Bentley", "Ferrari", "Lamborghini", "Maserati",
            "Aston Martin", "Rolls Royce", "Mini", "Smart", "Tesla",
            "Daihatsu", "Mahindra", "Tata", "Proton"
        ]

        title_lower = title.lower()
        
        for make in makes:
            if make.lower() in title_lower:
                parts = title.split()
                for i, part in enumerate(parts):
                    if part.lower() == make.lower() or part.lower() in make.lower():
                        if i + 1 < len(parts):
                            model = parts[i + 1]
                            model = ''.join(c for c in model if c.isalnum() or c.isspace())
                            if model and len(model) > 1:
                                common_words = ["for", "with", "in", "at", "from", "on", "the"]
                                if model.lower() not in common_words:
                                    return make, model
                        return make, ""

        return "", ""

    # ============================================================
    # EXTRACT VEHICLE DETAILS
    # ============================================================

    def _extract_vehicle_details(
        self,
        soup: BeautifulSoup,
        page_text: str
    ) -> Dict[str, Any]:
        """
        Extract all vehicle details from the page.
        """
        details = {
            "year": None,
            "mileage": None,
            "engine_size": None,
            "fuel_type": None,
            "transmission": None,
            "body_type": None,
        }

        # Try to find detail sections
        detail_selectors = [
            ".details",
            ".specs",
            ".specifications",
            ".features",
            ".info",
            ".attributes",
            ".vehicle-details",
            ".car-details",
            ".listing-details",
        ]

        for selector in detail_selectors:
            try:
                detail_section = soup.select_one(selector)
                if detail_section:
                    section_text = detail_section.get_text(" ", strip=True)
                    self._extract_details_from_text(section_text, details)
            except Exception:
                continue

        # If not found in specific sections, parse from entire page
        if all(v is None for v in details.values()):
            self._extract_details_from_text(page_text, details)

        return details

    def _extract_details_from_text(self, text: str, details: Dict) -> None:
        """
        Extract details from text and update the details dict.
        """
        text_lower = text.lower()

        # Extract year - FIXED: use parse_year
        if details["year"] is None:
            details["year"] = self.parse_year(text)

        # Extract mileage - FIXED: use parse_mileage
        if details["mileage"] is None:
            details["mileage"] = self.parse_mileage(text)

        # Extract engine size - FIXED: use parse_engine_size
        if details["engine_size"] is None:
            engine = self.parse_engine_size(text)
            if engine:
                details["engine_size"] = engine

        # Extract fuel type
        if details["fuel_type"] is None:
            fuel_patterns = ["petrol", "diesel", "electric", "hybrid", "cng", "lpg"]
            for fuel in fuel_patterns:
                if fuel in text_lower:
                    details["fuel_type"] = fuel.capitalize()
                    break

        # Extract transmission
        if details["transmission"] is None:
            if "automatic" in text_lower or "auto" in text_lower:
                details["transmission"] = "Automatic"
            elif "manual" in text_lower:
                details["transmission"] = "Manual"

        # Extract body type
        if details["body_type"] is None:
            body_types = ["sedan", "suv", "hatchback", "coupe", 
                         "convertible", "truck", "van", "wagon", 
                         "pickup", "mpv", "sports", "luxury"]
            for body in body_types:
                if body in text_lower:
                    details["body_type"] = body.capitalize()
                    break

    # ============================================================
    # EXTRACT LOCATION
    # ============================================================

    def _extract_location(
        self,
        soup: BeautifulSoup,
        page_text: str
    ) -> str:
        """
        Extract location from the page.
        """
        # Try specific location selectors
        location_selectors = [
            ".location",
            ".vehicle-location",
            "[itemprop='location']",
            ".address",
            ".seller-location",
            ".city",
            ".area",
            ".region",
            ".place",
            ".location-info",
            ".town",
        ]

        for selector in location_selectors:
            try:
                location_element = soup.select_one(selector)
                if location_element:
                    location = self.clean_text(location_element.get_text())  # FIXED: use clean_text
                    if location and len(location) > 2:
                        kenyan_cities = ["nairobi", "mombasa", "kisumu", "nakuru", 
                                       "eldoret", "thika", "malindi", "kitale", 
                                       "garissa", "meru", "nyeri", "nanyuki"]
                        if any(city in location.lower() for city in kenyan_cities):
                            return location
            except Exception:
                continue

        # Try to find location in page text
        location_patterns = [
            r'Location:\s*([^,\.]+)',
            r'Located in:\s*([^,\.]+)',
            r'City:\s*([^,\.]+)',
            r'Area:\s*([^,\.]+)',
            r'Town:\s*([^,\.]+)',
            r'Region:\s*([^,\.]+)',
        ]

        for pattern in location_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                location = self.clean_text(match.group(1))
                if location and len(location) > 2:
                    return location

        return "Kenya"

    # ============================================================
    # EXTRACT SELLER INFO
    # ============================================================

    def _extract_seller_info(
        self,
        soup: BeautifulSoup,
        page_text: str
    ) -> tuple:
        """
        Extract seller name and type.
        """
        seller_name = "Cheki"
        seller_type = "Dealer"

        seller_selectors = [
            ".seller-name",
            ".dealer-name",
            ".seller",
            ".dealer",
            ".vendor",
            "[itemprop='seller']",
            ".seller-info",
            ".advertiser",
            ".owner",
        ]

        for selector in seller_selectors:
            try:
                seller_element = soup.select_one(selector)
                if seller_element:
                    name = self.clean_text(seller_element.get_text())
                    if name and len(name) > 2:
                        seller_name = name
                        break
            except Exception:
                continue

        page_text_lower = page_text.lower()
        if "dealer" in page_text_lower or "dealership" in page_text_lower or "company" in page_text_lower:
            seller_type = "Dealer"
        elif "private seller" in page_text_lower or "individual" in page_text_lower or "owner" in page_text_lower:
            seller_type = "Private"
        elif "ltd" in page_text_lower or "limited" in page_text_lower:
            seller_type = "Dealer"

        return seller_name, seller_type

    # ============================================================
    # EXTRACT CONDITION
    # ============================================================

    def _extract_condition(
        self,
        soup: BeautifulSoup,
        page_text: str
    ) -> str:
        """
        Extract vehicle condition.
        """
        page_text_lower = page_text.lower()

        if "brand new" in page_text_lower or "new car" in page_text_lower or "never used" in page_text_lower:
            return "New"
        elif "certified pre-owned" in page_text_lower or "certified used" in page_text_lower or "cpo" in page_text_lower:
            return "Certified Pre-Owned"
        elif "used car" in page_text_lower or "pre-owned" in page_text_lower or "second hand" in page_text_lower:
            return "Used"

        meta_condition = soup.find("meta", {"name": "condition"})
        if meta_condition:
            content = meta_condition.get("content", "").lower()
            if "new" in content:
                return "New"
            if "used" in content or "pre-owned" in content:
                return "Used"

        condition_selectors = [
            ".condition",
            ".vehicle-condition",
            "[itemprop='vehicleCondition']",
            ".status",
        ]

        for selector in condition_selectors:
            try:
                condition_element = soup.select_one(selector)
                if condition_element:
                    condition = self.clean_text(condition_element.get_text()).lower()
                    if "new" in condition:
                        return "New"
                    if "used" in condition or "pre-owned" in condition:
                        return "Used"
                    if "cpo" in condition or "certified" in condition:
                        return "Certified Pre-Owned"
            except Exception:
                continue

        return "Used"
