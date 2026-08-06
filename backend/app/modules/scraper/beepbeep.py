# app/modules/scraper/beepbeep.py
# ================================================================
# Auto-D Kenya - BeepBeep Scraper
# ================================================================

import asyncio
import logging
import random
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.modules.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class BeepBeepScraper(BaseScraper):
    """
    Scraper for BeepBeep Kenya vehicle listings.
    BeepBeep is a car marketplace in Kenya (https://beepbeep.co.ke)
    """

    def __init__(self):
        super().__init__(
            source_name="beepbeep",
            base_url="https://beepbeep.co.ke"
        )

        # Main search URL for car listings
        self.search_url = "https://beepbeep.co.ke/cars"
        
        # Alternative URLs if the main one doesn't work
        self.fallback_urls = [
            "https://beepbeep.co.ke/vehicles",
            "https://beepbeep.co.ke/used-cars",
            "https://beepbeep.co.ke/listings",
            "https://beepbeep.co.ke/cars-for-sale"
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
        
        # Find a working URL first
        working_url = await self._find_working_url()
        if not working_url:
            logger.error("No working URL found for BeepBeep")
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
                "BeepBeep: scraping page %d using URL: %s",
                page,
                working_url
            )

            try:
                # Try different page parameter formats
                soup = await self._fetch_page_with_pagination(working_url, page)

                if soup is None:
                    logger.warning(
                        "Failed to load BeepBeep page %d",
                        page,
                    )
                    continue

                # Extract listing URLs
                urls = self._extract_listing_urls(soup)
                
                # Deduplicate URLs
                unique_urls = list(dict.fromkeys(urls))

                logger.info(
                    "Found %d unique vehicle links on BeepBeep page %d",
                    len(unique_urls),
                    page,
                )

                # Process each listing
                for url in unique_urls[:limit_per_page]:

                    listing = await self._parse_listing(url)

                    if listing and listing.get("listing_id"):
                        listings.append(listing)
                        logger.debug(f"Successfully scraped listing: {listing.get('title')}")

                    # Random delay to be polite
                    await asyncio.sleep(random.uniform(0.3, 0.8))

                # Delay between pages
                await asyncio.sleep(random.uniform(1, 2))

            except Exception as e:
                logger.exception(
                    "BeepBeep page %d failed: %s",
                    page,
                    str(e)
                )

        return {
            "status": "success",
            "source": self.source_name,
            "listings": listings,
            "listings_found": len(listings),
            "listings_saved": 0,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    # ============================================================
    # FIND WORKING URL
    # ============================================================

    async def _find_working_url(self) -> Optional[str]:
        """
        Find a working URL for BeepBeep listings.
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
        # Common pagination formats
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
        Extract listing URLs from the BeepBeep page.
        """
        urls: Set[str] = set()

        # BeepBeep specific selectors
        selectors = [
            'a[href*="/car/"]',
            'a[href*="/vehicle/"]',
            'a[href*="/listing/"]',
            'a[href*="/cars/"]',
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
        ]

        for selector in selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    href = element.get("href")
                    if href:
                        url = urljoin(self.base_url, href)
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
            "whatsapp.com", "/blog", "/news",
            "/category", "/tag", "/author",
        ]
        
        if any(pattern in url.lower() for pattern in exclude_patterns):
            return False
            
        # Include listing URLs
        include_patterns = [
            "/car/", "/vehicle/", "/listing/", 
            "/cars/", "/vehicles/", "/used/"
        ]
        
        return any(pattern in url.lower() for pattern in include_patterns)

    # ============================================================
    # PARSE LISTING
    # ============================================================

    async def _parse_listing(
        self,
        url: str,
    ) -> Optional[Dict[str, Any]]:

        try:
            soup = await self.fetch_soup(url)

            if soup is None:
                return None

            # Extract title
            title = self._extract_title(soup)

            if not title:
                logger.warning(f"No title found for listing: {url}")
                return None

            # Get page text
            page_text = soup.get_text(" ", strip=True)

            # Extract make and model
            make, model = self._extract_make_model(title)

            # Extract listing ID
            listing_id = self._extract_listing_id(url, soup)

            # Extract price
            price = self._extract_price(soup, page_text)

            # Extract vehicle details
            details = self._extract_vehicle_details(soup, page_text)

            # Extract location
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

        except Exception as e:
            logger.exception(
                "Failed parsing BeepBeep listing: %s - %s",
                url,
                str(e)
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
        title_tag = soup.find("h1")
        if title_tag:
            title = self.clean_text(title_tag.get_text())
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
            for separator in ["|", "-", "–", "—"]:
                if separator in title:
                    title = title.split(separator)[0].strip()
                    break
            if title:
                return title

        return ""

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

        # Common makes in Kenya (organized by length for better matching)
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
        
        # Try to find make in title
        for make in makes:
            if make.lower() in title_lower:
                # Extract model (text after make)
                parts = title.split()
                for i, part in enumerate(parts):
                    if part.lower() == make.lower() or part.lower() in make.lower():
                        # Get next part as model
                        if i + 1 < len(parts):
                            model = parts[i + 1]
                            # Clean model
                            model = ''.join(c for c in model if c.isalnum() or c.isspace())
                            if model and len(model) > 1:
                                # Check if model is not a common word
                                common_words = ["for", "with", "in", "at", "from", "on", "the"]
                                if model.lower() not in common_words:
                                    return make, model
                        return make, ""

        return "", ""

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
        common_words = ["car", "used", "new", "vehicle", "listing", "cars", "vehicles"]
        if listing_id and len(listing_id) > 2 and listing_id.lower() not in common_words:
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

        # Generate from URL hash
        return str(abs(hash(url)))[:10]

    # ============================================================
    # EXTRACT PRICE
    # ============================================================

    def _extract_price(
        self,
        soup: BeautifulSoup,
        page_text: str
    ) -> Optional[float]:
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
        ]

        for selector in price_selectors:
            try:
                price_element = soup.select_one(selector)
                if price_element:
                    price_text = price_element.get_text(strip=True)
                    price = self.parse_price(price_text)
                    if price:
                        return price
            except Exception:
                continue

        # Try to find price in page text
        price_patterns = [
            r'KSh\s*([\d,]+\.?\d*)',
            r'KES\s*([\d,]+\.?\d*)',
            r'Kenya Shillings\s*([\d,]+\.?\d*)',
            r'Price:\s*KSh\s*([\d,]+\.?\d*)',
            r'Price:\s*KES\s*([\d,]+\.?\d*)',
            r'Price:\s*([\d,]+\.?\d*)\s*KES',
            r'([\d,]+\.?\d*)\s*KSh',
            r'([\d,]+\.?\d*)\s*KES',
        ]

        for pattern in price_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(',', '')
                try:
                    return float(price_str)
                except ValueError:
                    continue

        return None

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
        detail_sections = soup.find_all(["div", "ul", "table", "dl"],
            class_=lambda x: x and any(word in x.lower() for word in 
                ["details", "specs", "specifications", "features", "info", "attributes"])
        )

        for section in detail_sections:
            section_text = section.get_text(" ", strip=True)
            
            # Extract year
            year_match = re.search(r'(\d{4})', section_text)
            if year_match and details["year"] is None:
                year = int(year_match.group(1))
                if 1980 <= year <= datetime.now().year:
                    details["year"] = year

            # Extract mileage
            if details["mileage"] is None:
                details["mileage"] = self.parse_mileage(section_text)

            # Extract engine size
            if details["engine_size"] is None:
                details["engine_size"] = self.parse_engine_size(section_text)

            # Extract fuel type
            if details["fuel_type"] is None:
                fuel_patterns = ["petrol", "diesel", "electric", "hybrid", "cng", "lpg"]
                for fuel in fuel_patterns:
                    if fuel in section_text.lower():
                        details["fuel_type"] = fuel.capitalize()
                        break

            # Extract transmission
            if details["transmission"] is None:
                if "automatic" in section_text.lower() or "auto" in section_text.lower():
                    details["transmission"] = "Automatic"
                elif "manual" in section_text.lower():
                    details["transmission"] = "Manual"

            # Extract body type
            if details["body_type"] is None:
                body_types = ["sedan", "suv", "hatchback", "coupe", 
                             "convertible", "truck", "van", "wagon", 
                             "pickup", "mpv", "sports", "luxury"]
                for body in body_types:
                    if body in section_text.lower():
                        details["body_type"] = body.capitalize()
                        break

        # If details not found in sections, try entire page text
        if details["year"] is None:
            details["year"] = self.parse_year(page_text)
        if details["mileage"] is None:
            details["mileage"] = self.parse_mileage(page_text)
        if details["engine_size"] is None:
            details["engine_size"] = self.parse_engine_size(page_text)

        return details

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
        ]

        for selector in location_selectors:
            try:
                location_element = soup.select_one(selector)
                if location_element:
                    location = self.clean_text(location_element.get_text())
                    if location and len(location) > 2:
                        # Check if it looks like a location
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
        ]

        for pattern in location_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                location = self.clean_text(match.group(1))
                if location and len(location) > 2:
                    return location

        # Default to Kenya
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
        seller_name = "BeepBeep"
        seller_type = "Dealer"

        # Try to find seller name
        seller_selectors = [
            ".seller-name",
            ".dealer-name",
            ".seller",
            ".dealer",
            ".vendor",
            "[itemprop='seller']",
            ".seller-info",
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

        # Determine seller type
        if "dealer" in page_text.lower() or "dealership" in page_text.lower():
            seller_type = "Dealer"
        elif "private seller" in page_text.lower() or "individual" in page_text.lower():
            seller_type = "Private"
        elif "company" in page_text.lower() or "ltd" in page_text.lower():
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
        # Check condition indicators
        condition_indicators = {
            "new": ["brand new", "new car", "new model", "never used", "0 km"],
            "used": ["used car", "pre-owned", "second hand", "used vehicle"],
            "cpo": ["certified pre-owned", "certified used", "cpo"],
        }

        page_text_lower = page_text.lower()

        for condition, indicators in condition_indicators.items():
            for indicator in indicators:
                if indicator in page_text_lower:
                    if condition == "new":
                        return "New"
                    elif condition == "used":
                        return "Used"
                    elif condition == "cpo":
                        return "Certified Pre-Owned"

        # Check meta data
        meta_condition = soup.find("meta", {"name": "condition"})
        if meta_condition:
            content = meta_condition.get("content", "").lower()
            if "new" in content:
                return "New"
            if "used" in content or "pre-owned" in content:
                return "Used"

        # Default to Used
        return "Used"
