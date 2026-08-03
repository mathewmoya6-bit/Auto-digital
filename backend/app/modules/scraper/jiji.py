# app/modules/scraper/jiji.py
# ================================================================
# Auto-D Kenya - Jiji Vehicle Scraper
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
        
        # Alternative URLs if the main one doesn't work
        self.fallback_urls = [
            "https://jiji.co.ke/vehicles",
            "https://jiji.co.ke/used-cars",
            "https://jiji.co.ke/cars-for-sale",
            "https://jiji.co.ke/automotive"
        ]

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
            logger.error("No working URL found for Jiji")
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
                "Jiji: scraping page %d using URL: %s",
                page,
                working_url
            )

            try:
                # Jiji uses different pagination formats
                soup = await self._fetch_page_with_pagination(working_url, page)

                if soup is None:
                    logger.warning(
                        "Unable to fetch Jiji page %d",
                        page,
                    )
                    continue

                # FIXED: Use the proper method instead of _extract_urls
                urls = self._extract_listing_urls(soup)

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
    # FIND WORKING URL
    # ============================================================

    async def _find_working_url(self) -> Optional[str]:
        """
        Find a working URL for Jiji listings.
        """
        urls_to_try = [self.search_url] + self.fallback_urls
        
        for url in urls_to_try:
            try:
                logger.info(f"Testing URL: {url}")
                soup = await self._fetch_page(url)
                if soup is not None:
                    # Check if we got actual content
                    body_text = soup.get_text(strip=True)
                    if len(body_text) > 100:  # Has real content
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
            "for sale", "used cars", "new cars", "automotive"
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
        Try different pagination formats for Jiji.
        """
        # Jiji specific pagination formats
        pagination_formats = [
            f"{base_url}?page={page}",
            f"{base_url}?p={page}",
            f"{base_url}?page_number={page}",
            f"{base_url}/page/{page}",
            f"{base_url}/{page}",
            f"{base_url}?start={page * 20}",
            f"{base_url}?offset={page * 20}",
        ]

        for url in pagination_formats:
            try:
                logger.debug(f"Trying pagination URL: {url}")
                soup = await self._fetch_page(url)
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
        Extract listing URLs from the Jiji page.
        FIXED: Replaces the missing _extract_urls method.
        """
        urls: Set[str] = set()

        # Jiji specific selectors
        selectors = [
            'a[href*="/cars/"]',
            'a[href*="/vehicle/"]',
            'a[href*="/ad/"]',
            'a[href*="/listing/"]',
            'a[href*="/automotive/"]',
            '.b-list-advert a',
            '.advert-list a',
            '.listing a',
            '.card a',
            '.item a',
            '.ad a',
            '.b-advert a',
            'a.advert-title',
            'a.advert-link',
            '.b-advert-title a',
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
            "/profile", "/account", "/dashboard",
            "/sell", "/post", "/create",
        ]
        
        if any(pattern in url.lower() for pattern in exclude_patterns):
            return False
            
        # Include listing URLs
        include_patterns = [
            "/cars/", "/vehicle/", "/ad/",
            "/listing/", "/automotive/", "/car/",
            "/vehicles/", "/used/", "/new/",
            "/sale/", "/buy/",
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
            soup = await self._fetch_page(url)

            if soup is None:
                return None

            # Extract title
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

        except Exception:
            logger.exception(
                "Failed parsing Jiji listing: %s",
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
            title = self._clean_text(h1.get_text())
            if title and len(title) > 2:
                return title

        # Try Jiji-specific title selectors
        title_selectors = [
            ".advert-title",
            ".listing-title",
            ".item-title",
            ".product-title",
            ".title",
            '[itemprop="name"]',
            '.b-advert-title',
        ]

        for selector in title_selectors:
            try:
                title_element = soup.select_one(selector)
                if title_element:
                    title = self._clean_text(title_element.get_text())
                    if title and len(title) > 2:
                        return title
            except Exception:
                continue

        # Try meta tags
        meta_title = soup.find("meta", {"property": "og:title"})
        if meta_title:
            content = meta_title.get("content")
            if content:
                title = self._clean_text(content)
                if title:
                    return title

        # Try title tag
        title_tag = soup.find("title")
        if title_tag:
            title = self._clean_text(title_tag.get_text())
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
        common_words = ["car", "used", "new", "vehicle", "listing", 
                       "cars", "vehicles", "ad", "automotive", "view"]
        if listing_id and len(listing_id) > 2 and listing_id.lower() not in common_words:
            # Check if it's numeric or alphanumeric
            if re.match(r'^[a-zA-Z0-9\-_]+$', listing_id):
                return listing_id

        # Try Jiji-specific ID patterns
        # Jiji often has IDs like "12345678" or "abc-123"
        id_patterns = [
            r'/cars/(\d+)',
            r'/ad/(\d+)',
            r'/listing/(\d+)',
            r'/(\d+)/',
        ]
        
        for pattern in id_patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

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
    ) -> Optional[float]:
        """
        Extract price from the page.
        """
        # Try specific price selectors (Jiji specific)
        price_selectors = [
            ".price",
            ".advert-price",
            ".listing-price",
            ".item-price",
            ".product-price",
            "[itemprop='price']",
            ".amount",
            ".sale-price",
            ".price-amount",
            "span.price",
            "div.price",
            ".cost",
            ".price-display",
            ".currency-value",
            ".b-advert-price",
            ".ad-price",
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

        # Try Jiji-specific price patterns
        price_patterns = [
            r'KSh\s*([\d,]+\.?\d*)',
            r'KES\s*([\d,]+\.?\d*)',
            r'Kenya Shillings\s*([\d,]+\.?\d*)',
            r'Price:\s*KSh\s*([\d,]+\.?\d*)',
            r'Price:\s*KES\s*([\d,]+\.?\d*)',
            r'Price:\s*([\d,]+\.?\d*)\s*KES',
            r'([\d,]+\.?\d*)\s*KSh',
            r'([\d,]+\.?\d*)\s*KES',
            r'KSh\.?\s*([\d,]+\.?\d*)',
            r'KES\.?\s*([\d,]+\.?\d*)',
        ]

        for pattern in price_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(',', '').replace(' ', '')
                try:
                    return float(price_str)
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
                            # Clean model (remove special characters)
                            model = ''.join(c for c in model if c.isalnum() or c.isspace())
                            if model and len(model) > 1:
                                # Check if model is not a common word
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

        # Try Jiji-specific detail sections
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
            ".advert-details",
            ".b-details",
            ".params",
            ".properties",
        ]

        # First try to find structured details
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

        # Extract year
        if details["year"] is None:
            year_match = re.search(r'(\d{4})', text)
            if year_match:
                year = int(year_match.group(1))
                if 1980 <= year <= datetime.now().year + 1:
                    details["year"] = year

        # Extract mileage
        if details["mileage"] is None:
            # Try various mileage patterns
            mileage_patterns = [
                r'(\d{1,3}(?:,\d{3})*)\s*km',
                r'(\d+)\s*kilometers',
                r'(\d+)\s*kms',
                r'km\s*(\d+)',
            ]
            for pattern in mileage_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        mileage_str = match.group(1).replace(',', '')
                        details["mileage"] = int(mileage_str)
                        break
                    except ValueError:
                        continue

        # Extract engine size
        if details["engine_size"] is None:
            engine_patterns = [
                r'(\d+\.?\d*)\s*l',
                r'(\d+\.?\d*)\s*cc',
                r'(\d+\.?\d*)\s*cylinder',
                r'engine\s*(\d+\.?\d*)',
            ]
            for pattern in engine_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        details["engine_size"] = float(match.group(1))
                        break
                    except ValueError:
                        continue

        # Extract fuel type
        if details["fuel_type"] is None:
            fuel_patterns = {
                "petrol": ["petrol", "gasoline", "gas"],
                "diesel": ["diesel"],
                "electric": ["electric", "ev"],
                "hybrid": ["hybrid"],
                "cng": ["cng", "lpg"],
            }
            for fuel, patterns in fuel_patterns.items():
                if any(p in text_lower for p in patterns):
                    details["fuel_type"] = fuel.capitalize()
                    break

        # Extract transmission
        if details["transmission"] is None:
            if "automatic" in text_lower or "auto" in text_lower:
                details["transmission"] = "Automatic"
            elif "manual" in text_lower:
                details["transmission"] = "Manual"
            elif "cvt" in text_lower:
                details["transmission"] = "CVT"
            elif "semi-automatic" in text_lower or "semi automatic" in text_lower:
                details["transmission"] = "Semi-Automatic"

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
        # Try specific location selectors (Jiji specific)
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
            ".advert-location",
            ".b-location",
        ]

        for selector in location_selectors:
            try:
                location_element = soup.select_one(selector)
                if location_element:
                    location = self._clean_text(location_element.get_text())
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
            r'Town:\s*([^,\.]+)',
            r'Region:\s*([^,\.]+)',
            r'From\s*([^,\.]+)',
        ]

        for pattern in location_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                location = self._clean_text(match.group(1))
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
        seller_name = "Jiji"
        seller_type = "Dealer"

        # Try to find seller name (Jiji specific)
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
            ".b-seller",
            ".b-user",
            ".user-name",
        ]

        for selector in seller_selectors:
            try:
                seller_element = soup.select_one(selector)
                if seller_element:
                    name = self._clean_text(seller_element.get_text())
                    if name and len(name) > 2:
                        seller_name = name
                        break
            except Exception:
                continue

        # Determine seller type
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

        # Check condition indicators
        if "brand new" in page_text_lower or "new car" in page_text_lower or "never used" in page_text_lower:
            return "New"
        elif "certified pre-owned" in page_text_lower or "certified used" in page_text_lower or "cpo" in page_text_lower:
            return "Certified Pre-Owned"
        elif "used car" in page_text_lower or "pre-owned" in page_text_lower or "second hand" in page_text_lower:
            return "Used"

        # Check meta data
        meta_condition = soup.find("meta", {"name": "condition"})
        if meta_condition:
            content = meta_condition.get("content", "").lower()
            if "new" in content:
                return "New"
            if "used" in content or "pre-owned" in content:
                return "Used"

        # Check for condition labels
        condition_selectors = [
            ".condition",
            ".vehicle-condition",
            "[itemprop='vehicleCondition']",
            ".status",
            ".condition-label",
        ]

        for selector in condition_selectors:
            try:
                condition_element = soup.select_one(selector)
                if condition_element:
                    condition = self._clean_text(condition_element.get_text()).lower()
                    if "new" in condition:
                        return "New"
                    if "used" in condition or "pre-owned" in condition:
                        return "Used"
                    if "cpo" in condition or "certified" in condition:
                        return "Certified Pre-Owned"
            except Exception:
                continue

        # Default to Used
        return "Used"

    # ============================================================
    # OVERRIDE: PARSE YEAR
    # ============================================================

    def _parse_year(
        self,
        text: str,
    ) -> Optional[int]:
        """
        Parse year from Jiji listing text.
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
        """
        return super()._parse_price(text)
