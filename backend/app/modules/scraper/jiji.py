# app/modules/scraper/jiji.py
# ================================================================
# Auto-D Kenya - Jiji Vehicle Scraper
# ================================================================

import asyncio
import hashlib
import logging
import random
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.modules.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class JijiScraper(BaseScraper):
    """
    Scraper for Jiji Kenya vehicle listings.
    """

    # ─── CONFIGURATION ──────────────────────────────────────────────
    
    # Listing URL patterns (regex for validation)
    LISTING_PATTERNS = [
        r"/cars/[A-Za-z0-9\-_]+$",
        r"/vehicle/[A-Za-z0-9\-_]+$",
        r"/ad/[A-Za-z0-9\-_]+$",
        r"/listing/[A-Za-z0-9\-_]+$",
        r"/automotive/[A-Za-z0-9\-_]+$",
    ]
    
    # Exclude patterns (non-listing URLs)
    EXCLUDE_PATTERNS = [
        r"/login", r"/signup", r"/register",
        r"/about", r"/contact", r"/help",
        r"/faq", r"/privacy", r"/terms",
        r"/blog", r"/news", r"/profile", r"/account",
        r"/dashboard", r"/settings", r"/messages",
    ]
    
    # Price selectors
    PRICE_SELECTORS = [
        ".price", ".advert-price", ".listing-price",
        ".item-price", ".product-price", "[itemprop='price']",
        ".amount", ".sale-price", ".price-amount",
        "span.price", "div.price",
    ]
    
    # Title selectors
    TITLE_SELECTORS = [
        "h1", ".advert-title", ".listing-title", ".item-title",
        ".product-title", ".title", '[itemprop="name"]',
    ]
    
    # Listing URL selectors
    URL_SELECTORS = [
        'a[href*="/cars/"]',
        'a[href*="/vehicle/"]',
        'a[href*="/ad/"]',
        'a[href*="/listing/"]',
        '.b-list-advert a',
        '.advert-list a',
        '.listing a',
        '.card a',
        '.item a',
        '.ad a',
        'a.advert-title',
        'a.advert-link',
    ]
    
    # Detail section selectors
    DETAIL_SELECTORS = [
        ".details", ".specs", ".specifications",
        ".features", ".info", ".attributes",
        ".vehicle-details", ".car-details",
    ]
    
    # Location selectors
    LOCATION_SELECTORS = [
        ".location", ".vehicle-location", "[itemprop='location']",
        ".address", ".seller-location", ".city", ".area",
    ]
    
    # Seller selectors
    SELLER_SELECTORS = [
        ".seller-name", ".dealer-name", ".seller",
        ".dealer", ".vendor", "[itemprop='seller']",
    ]
    
    # Phone selectors
    PHONE_SELECTORS = [
        ".phone", ".seller-phone", ".contact-phone",
        ".phone-number", "[itemprop='telephone']",
    ]
    
    # Description selectors
    DESCRIPTION_SELECTORS = [
        ".description", ".advert-description", ".listing-description",
        ".item-description", ".product-description",
    ]

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
        
        # Pagination templates
        self.pagination_templates = [
            "?page={page}",
            "?p={page}",
            "?page_number={page}",
            "/page/{page}",
            "/{page}",
            "?start={page}",
            "?offset={page}",
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
        seen_ids = set()  # FIXED: Deduplication
        failed_pages = 0
        
        try:
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
                    soup = await self._fetch_page_with_pagination(working_url, page)

                    if soup is None:
                        logger.warning(
                            "Unable to fetch Jiji page %d",
                            page,
                        )
                        failed_pages += 1
                        continue

                    urls = self._extract_listing_urls(soup)

                    logger.info(
                        "Found %d unique listing URLs on Jiji page %d",
                        len(urls),
                        page,
                    )

                    parsed_count = 0
                    for url in urls[:limit_per_page]:

                        listing = await self._parse_listing(url)

                        if listing and listing.get("listing_id"):
                            listing_id = listing["listing_id"]
                            if listing_id not in seen_ids:
                                seen_ids.add(listing_id)
                                listings.append(listing)
                                parsed_count += 1

                        await asyncio.sleep(
                            random.uniform(0.3, 0.8)
                        )

                    logger.info(
                        "Jiji page %d: parsed %d new listings (total: %d)",
                        page,
                        parsed_count,
                        len(listings),
                    )

                    await asyncio.sleep(
                        random.uniform(1, 2)
                    )

                except Exception:
                    logger.exception(
                        "Failed scraping Jiji page %d",
                        page,
                    )
                    failed_pages += 1
                    continue

            return {
                "status": "success",
                "source": self.source_name,
                "listings": listings,
                "listings_found": len(listings),
                "pages_scraped": pages - failed_pages,
                "pages_failed": failed_pages,
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
        """Find a working URL for Jiji listings."""
        urls_to_try = [self.search_url] + self.fallback_urls
        
        for url in urls_to_try:
            try:
                logger.info(f"Testing URL: {url}")
                soup = await self.fetch_soup_with_retry(url)
                if soup is not None:
                    body_text = soup.get_text(strip=True)
                    if len(body_text) > 100:
                        if self._has_listings(soup):
                            logger.info(f"Found working URL: {url}")
                            return url
            except Exception as e:
                logger.warning(f"URL {url} failed: {str(e)}")
                continue
        
        return None

    def _has_listings(self, soup: BeautifulSoup) -> bool:
        """Check if the page contains car listings."""
        indicators = ["car", "vehicle", "listing", "inventory", "for sale", "used cars"]
        text = soup.get_text(strip=True).lower()
        return any(indicator in text for indicator in indicators)

    # ============================================================
    # FETCH PAGE WITH PAGINATION AND RETRY
    # ============================================================

    async def fetch_soup_with_retry(
        self,
        url: str,
        max_retries: int = 3,
    ) -> Optional[BeautifulSoup]:
        """
        Fetch page with retry logic.
        """
        for attempt in range(max_retries):
            try:
                soup = await self.fetch_soup(url)
                if soup is not None:
                    return soup
            except Exception as e:
                logger.debug(f"Fetch attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        return None

    async def _fetch_page_with_pagination(
        self,
        base_url: str,
        page: int
    ) -> Optional[BeautifulSoup]:
        """Try different pagination formats with retry."""
        for template in self.pagination_templates:
            # Handle different template types
            if template.startswith("?"):
                url = f"{base_url}{template.format(page=page)}"
            else:
                url = f"{base_url}{template.format(page=page)}"
            
            try:
                soup = await self.fetch_soup_with_retry(url)
                if soup is not None:
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
        """Extract listing URLs from the Jiji page."""
        urls: Set[str] = set()

        for selector in self.URL_SELECTORS:
            try:
                elements = soup.select(selector)
                for element in elements:
                    href = element.get("href")
                    if href:
                        url = self.absolute_url(href)
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
        """Check if URL is a valid listing URL using regex patterns."""
        # Check excludes first
        for pattern in self.EXCLUDE_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return False
            
        # Check includes
        for pattern in self.LISTING_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
                
        return False

    # ============================================================
    # PARSE LISTING
    # ============================================================

    async def _parse_listing(
        self,
        url: str,
    ) -> Optional[Dict[str, Any]]:

        try:
            soup = await self.fetch_soup_with_retry(url)

            if soup is None:
                return None

            title = self._extract_title(soup)

            if not title:
                logger.warning(f"No title found for listing: {url}")
                return None

            page_text = soup.get_text(" ", strip=True)

            listing_id = self._extract_listing_id(url, soup)

            if not listing_id:
                return None

            make, model = self._extract_make_model(title)

            price = self._extract_price(soup, page_text)

            details = self._extract_vehicle_details(soup, page_text)

            location = self._extract_location(soup, page_text)

            seller_name, seller_type, seller_phone = self._extract_seller_info(soup, page_text)

            condition = self._extract_condition(soup, page_text)

            description = self._extract_description(soup)

            images = self._extract_images(soup)

            # Extract additional fields
            color = self._extract_color(soup, page_text)
            drive_type = self._extract_drive_type(soup, page_text)
            variant = self._extract_variant(soup, page_text)
            engine_code = self._extract_engine_code(soup, page_text)
            vin = self._extract_vin(soup, page_text)

            return {
                "listing_id": listing_id,
                "title": title,
                "url": url,
                "price": price,
                "currency": "KES",
                
                "make": make,
                "model": model,
                "variant": variant,
                
                "year": details.get("year"),
                "mileage": details.get("mileage"),
                
                "engine_size": details.get("engine_size"),
                "engine_code": engine_code,
                "fuel_type": details.get("fuel_type") or "",
                "transmission": details.get("transmission") or "",
                "drive_type": drive_type,
                "body_type": details.get("body_type") or "",
                "color": color,
                
                "condition": condition,
                "description": description,
                
                "seller_name": seller_name,
                "seller_phone": seller_phone,
                "seller_type": seller_type,
                
                "location": location,
                "images": images,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
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

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract vehicle title from the page."""
        # Try h1 first
        h1 = soup.find("h1")
        if h1:
            title = self.clean_text(h1.get_text())
            if title and len(title) > 2:
                return title

        for selector in self.TITLE_SELECTORS:
            try:
                title_element = soup.select_one(selector)
                if title_element:
                    title = self.clean_text(title_element.get_text())
                    if title and len(title) > 2:
                        return title
            except Exception:
                continue

        meta_title = soup.find("meta", {"property": "og:title"})
        if meta_title:
            content = meta_title.get("content")
            if content:
                title = self.clean_text(content)
                if title:
                    return title

        title_tag = soup.find("title")
        if title_tag:
            title = self.clean_text(title_tag.get_text())
            for separator in ["|", "-", "–", "—"]:
                if separator in title:
                    title = title.split(separator)[0].strip()
                    break
            if title:
                return title

        return ""

    # ============================================================
    # EXTRACT LISTING ID (STABLE HASH)
    # ============================================================

    def _extract_listing_id(self, url: str, soup: BeautifulSoup) -> str:
        """Extract listing ID from URL or page with stable hash."""
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        listing_id = path.split("/")[-1]
        
        common_words = ["car", "used", "new", "vehicle", "listing", "cars", "vehicles", "ad"]
        if listing_id and len(listing_id) > 2 and listing_id.lower() not in common_words:
            if re.match(r'^[a-zA-Z0-9\-_]+$', listing_id):
                return listing_id

        # Try to find numeric ID in URL
        id_patterns = [r'/cars/(\d+)', r'/ad/(\d+)', r'/listing/(\d+)', r'/(\d+)/']
        for pattern in id_patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # Try meta tags
        meta_id = soup.find("meta", {"name": "listing-id"})
        if meta_id:
            content = meta_id.get("content")
            if content:
                return content

        # FIXED: Use stable hash (MD5) instead of Python hash
        return hashlib.md5(url.encode()).hexdigest()[:12]

    # ============================================================
    # EXTRACT PRICE
    # ============================================================

    def _extract_price(self, soup: BeautifulSoup, page_text: str) -> Optional[int]:
        """Extract price from the page."""
        for selector in self.PRICE_SELECTORS:
            try:
                price_element = soup.select_one(selector)
                if price_element:
                    price_text = price_element.get_text(strip=True)
                    price = self.parse_price(price_text)
                    if price:
                        return int(price)
            except Exception:
                continue

        # Try to find price in page text
        price_patterns = [
            r'KSh\s*([\d,]+\.?\d*)',
            r'KES\s*([\d,]+\.?\d*)',
            r'([\d,]+\.?\d*)\s*KSh',
            r'([\d,]+\.?\d*)\s*KES',
        ]

        for pattern in price_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(',', '').replace(' ', '')
                try:
                    return int(float(price_str))
                except ValueError:
                    continue

        return None

    # ============================================================
    # EXTRACT MAKE AND MODEL
    # ============================================================

    def _extract_make_model(self, title: str) -> tuple:
        """Extract make and model from the title using word boundaries."""
        if not title:
            return "", ""

        makes = [
            "Toyota", "Nissan", "Honda", "Subaru", "Mazda",
            "Mercedes", "BMW", "Audi", "Volkswagen", "Ford",
            "Mitsubishi", "Isuzu", "Suzuki", "Hyundai", "Kia",
            "Land Rover", "Lexus", "Volvo", "Peugeot", "Citroen",
            "Renault", "Fiat", "Jeep", "Chevrolet", "Dodge",
            "Chrysler", "Porsche", "Jaguar", "Bentley", "Ferrari",
            "Lamborghini", "Maserati", "Aston Martin", "Rolls Royce",
            "Mini", "Smart", "Tesla", "Daihatsu", "Mahindra", "Tata",
        ]
        
        for make in makes:
            # FIXED: Use word boundaries for exact matching
            if re.search(rf'\b{re.escape(make)}\b', title, re.I):
                parts = title.split()
                for i, part in enumerate(parts):
                    if part.lower() == make.lower():
                        if i + 1 < len(parts):
                            model = parts[i + 1]
                            model = ''.join(c for c in model if c.isalnum() or c.isspace())
                            if model and len(model) > 1:
                                return make, model
                        return make, ""

        return "", ""

    # ============================================================
    # EXTRACT VEHICLE DETAILS
    # ============================================================

    def _extract_vehicle_details(self, soup: BeautifulSoup, page_text: str) -> Dict[str, Any]:
        """Extract all vehicle details from the page."""
        details = {
            "year": None,
            "mileage": None,
            "engine_size": None,
            "fuel_type": None,
            "transmission": None,
            "body_type": None,
        }

        for selector in self.DETAIL_SELECTORS:
            try:
                detail_section = soup.select_one(selector)
                if detail_section:
                    section_text = detail_section.get_text(" ", strip=True)
                    self._extract_details_from_text(section_text, details)
            except Exception:
                continue

        if all(v is None for v in details.values()):
            self._extract_details_from_text(page_text, details)

        return details

    def _extract_details_from_text(self, text: str, details: Dict) -> None:
        """Extract details from text and update the details dict."""
        text_lower = text.lower()

        # Year - use BaseScraper method
        if details["year"] is None:
            details["year"] = self.parse_year(text)

        # Mileage - use BaseScraper method
        if details["mileage"] is None:
            details["mileage"] = self.parse_mileage(text)

        # Engine size - use BaseScraper method
        if details["engine_size"] is None:
            engine = self.parse_engine_size(text)
            if engine:
                details["engine_size"] = engine

        # Fuel type
        if details["fuel_type"] is None:
            if "petrol" in text_lower:
                details["fuel_type"] = "Petrol"
            elif "diesel" in text_lower:
                details["fuel_type"] = "Diesel"
            elif "electric" in text_lower:
                details["fuel_type"] = "Electric"
            elif "hybrid" in text_lower:
                details["fuel_type"] = "Hybrid"

        # Transmission
        if details["transmission"] is None:
            if "automatic" in text_lower or "auto" in text_lower:
                details["transmission"] = "Automatic"
            elif "manual" in text_lower:
                details["transmission"] = "Manual"

        # Body type
        if details["body_type"] is None:
            body_types = {
                "suv": "SUV",
                "sedan": "Sedan",
                "hatchback": "Hatchback",
                "station wagon": "Station Wagon",
                "wagon": "Station Wagon",
                "double cab": "Double Cab",
                "single cab": "Single Cab",
                "pickup": "Pickup",
                "van": "Van",
                "minibus": "Minibus",
                "bus": "Bus",
                "truck": "Truck",
                "tipper": "Tipper",
                "trailer": "Trailer",
                "coupe": "Coupe",
                "convertible": "Convertible",
                "crossover": "Crossover",
            }
            for key, value in body_types.items():
                if key in text_lower:
                    details["body_type"] = value
                    break

    # ============================================================
    # EXTRACT LOCATION
    # ============================================================

    def _extract_location(self, soup: BeautifulSoup, page_text: str) -> str:
        """Extract location from the page."""
        for selector in self.LOCATION_SELECTORS:
            try:
                location_element = soup.select_one(selector)
                if location_element:
                    location = self.clean_text(location_element.get_text())
                    if location and len(location) > 2:
                        return location
            except Exception:
                continue

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

        return "Kenya"

    # ============================================================
    # EXTRACT SELLER INFO
    # ============================================================

    def _extract_seller_info(self, soup: BeautifulSoup, page_text: str) -> tuple:
        """Extract seller name, type, and phone."""
        seller_name = "Jiji"
        seller_type = "Dealer"
        seller_phone = ""

        # Extract seller name
        for selector in self.SELLER_SELECTORS:
            try:
                seller_element = soup.select_one(selector)
                if seller_element:
                    name = self.clean_text(seller_element.get_text())
                    if name and len(name) > 2:
                        seller_name = name
                        break
            except Exception:
                continue

        # Extract seller phone
        for selector in self.PHONE_SELECTORS:
            try:
                phone_element = soup.select_one(selector)
                if phone_element:
                    phone = self.clean_text(phone_element.get_text())
                    if phone:
                        # Clean phone number
                        phone = re.sub(r'[^\d+]', '', phone)
                        if len(phone) >= 7:
                            seller_phone = phone
                            break
            except Exception:
                continue

        # Determine seller type
        page_text_lower = page_text.lower()
        if "private seller" in page_text_lower or "individual" in page_text_lower:
            seller_type = "Private"
        elif "dealer" in page_text_lower or "dealership" in page_text_lower:
            seller_type = "Dealer"

        return seller_name, seller_type, seller_phone

    # ============================================================
    # EXTRACT CONDITION
    # ============================================================

    def _extract_condition(self, soup: BeautifulSoup, page_text: str) -> str:
        """Extract vehicle condition."""
        page_text_lower = page_text.lower()

        if "brand new" in page_text_lower or "new car" in page_text_lower or "never used" in page_text_lower:
            return "New"
        elif "certified pre-owned" in page_text_lower or "cpo" in page_text_lower:
            return "Certified Pre-Owned"
        elif "used car" in page_text_lower or "pre-owned" in page_text_lower or "second hand" in page_text_lower:
            return "Used"

        return "Used"

    # ============================================================
    # EXTRACT DESCRIPTION
    # ============================================================

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract vehicle description."""
        for selector in self.DESCRIPTION_SELECTORS:
            try:
                desc_element = soup.select_one(selector)
                if desc_element:
                    description = self.clean_text(desc_element.get_text())
                    if description and len(description) > 20:
                        return description
            except Exception:
                continue

        meta_desc = soup.find("meta", {"name": "description"})
        if meta_desc:
            content = meta_desc.get("content")
            if content:
                return self.clean_text(content)

        return ""

    # ============================================================
    # EXTRACT IMAGES
    # ============================================================

    def _extract_images(self, soup: BeautifulSoup) -> List[str]:
        """Extract image URLs."""
        images = []
        
        img_selectors = [
            "img",
            ".gallery img",
            ".vehicle-gallery img",
            ".slider img",
            ".carousel img",
            ".advert-images img",
        ]
        
        for selector in img_selectors:
            try:
                for img in soup.select(selector):
                    src = img.get("src") or img.get("data-src") or img.get("data-lazy")
                    if not src:
                        continue
                    # Filter out small/icon images
                    if "icon" in src.lower() or "thumb" in src.lower():
                        continue
                    src = self.absolute_url(src)
                    if src and src not in images:
                        images.append(src)
            except Exception:
                continue
        
        # Limit to reasonable number
        return images[:20]

    # ============================================================
    # EXTRACT COLOR
    # ============================================================

    def _extract_color(self, soup: BeautifulSoup, page_text: str) -> str:
        """Extract vehicle color."""
        colors = ["White", "Black", "Silver", "Grey", "Gray", "Blue", 
                  "Red", "Green", "Yellow", "Orange", "Brown", "Gold",
                  "Purple", "Pink", "Maroon", "Navy", "Teal", "Cyan",
                  "Magenta", "Lime", "Olive", "Coral", "Ivory", "Beige"]
        
        page_text_lower = page_text.lower()
        for color in colors:
            if color.lower() in page_text_lower:
                return color
        
        # Try color selectors
        color_selectors = [".color", ".vehicle-color", ".car-color"]
        for selector in color_selectors:
            try:
                color_element = soup.select_one(selector)
                if color_element:
                    color = self.clean_text(color_element.get_text())
                    for c in colors:
                        if c.lower() in color.lower():
                            return c
            except Exception:
                continue
        
        return ""

    # ============================================================
    # EXTRACT DRIVE TYPE
    # ============================================================

    def _extract_drive_type(self, soup: BeautifulSoup, page_text: str) -> str:
        """Extract drive type (2WD, 4WD, AWD, FWD, RWD)."""
        drive_patterns = {
            "4WD": r'\b4wd\b',
            "AWD": r'\bawd\b',
            "FWD": r'\bfwd\b',
            "RWD": r'\brwd\b',
            "2WD": r'\b2wd\b',
            "4x4": r'\b4x4\b',
        }
        
        page_text_lower = page_text.lower()
        for drive, pattern in drive_patterns.items():
            if re.search(pattern, page_text_lower):
                return drive
        
        # Try drive selectors
        drive_selectors = [".drive-type", ".drivetrain"]
        for selector in drive_selectors:
            try:
                drive_element = soup.select_one(selector)
                if drive_element:
                    text = drive_element.get_text().lower()
                    for drive, pattern in drive_patterns.items():
                        if re.search(pattern, text):
                            return drive
            except Exception:
                continue
        
        return ""

    # ============================================================
    # EXTRACT VARIANT
    # ============================================================

    def _extract_variant(self, soup: BeautifulSoup, page_text: str) -> str:
        """Extract vehicle variant/trim level."""
        variant_selectors = [".variant", ".trim", ".model-variant"]
        for selector in variant_selectors:
            try:
                variant_element = soup.select_one(selector)
                if variant_element:
                    variant = self.clean_text(variant_element.get_text())
                    if variant and len(variant) > 1:
                        return variant
            except Exception:
                continue
        
        # Try to find in page text
        variant_patterns = [
            r'Variant:\s*([^,\.]+)',
            r'Trim:\s*([^,\.]+)',
            r'Model:\s*([^,\.]+)',
        ]
        for pattern in variant_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                variant = self.clean_text(match.group(1))
                if variant and len(variant) > 1:
                    return variant
        
        return ""

    # ============================================================
    # EXTRACT ENGINE CODE
    # ============================================================

    def _extract_engine_code(self, soup: BeautifulSoup, page_text: str) -> str:
        """Extract engine code (e.g., 1KD, 2TR, 1NZ, 2NZ)."""
        engine_code_patterns = [
            r'Engine Code:\s*([A-Z0-9\-]+)',
            r'Engine:\s*([A-Z0-9\-]+)',
            r'\b([A-Z0-9]{2,4})\b',  # Generic pattern for codes like 1KD, 2TR
        ]
        
        for pattern in engine_code_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                code = match.group(1).strip()
                if len(code) >= 3 and re.match(r'^[A-Z0-9]+$', code, re.I):
                    return code.upper()
        
        return ""

    # ============================================================
    # EXTRACT VIN
    # ============================================================

    def _extract_vin(self, soup: BeautifulSoup, page_text: str) -> str:
        """Extract VIN (Vehicle Identification Number)."""
        vin_patterns = [
            r'VIN:\s*([A-Z0-9]{17})',
            r'VIN\s*([A-Z0-9]{17})',
            r'\b([A-Z0-9]{17})\b',
        ]
        
        for pattern in vin_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                vin = match.group(1).strip()
                if len(vin) == 17:
                    return vin
        
        return ""
