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
            logger.error("No working URL found for Jiji")
            return {
                "status": "error",
                "source": self.source_name,
                "listings": [],
                "listings_found": 0,
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
                    continue

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
            "completed_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    # ============================================================
    # FIND WORKING URL
    # ============================================================

    async def _find_working_url(self) -> Optional[str]:
        """Find a working URL for Jiji listings."""
        urls_to_try = [self.search_url] + self.fallback_urls
        
        for url in urls_to_try:
            try:
                logger.info(f"Testing URL: {url}")
                soup = await self._fetch_page(url)
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
    # FETCH PAGE WITH PAGINATION
    # ============================================================

    async def _fetch_page_with_pagination(
        self,
        base_url: str,
        page: int
    ) -> Optional[BeautifulSoup]:
        """Try different pagination formats."""
        pagination_formats = [
            f"{base_url}?page={page}",
            f"{base_url}?p={page}",
            f"{base_url}?page_number={page}",
            f"{base_url}/page/{page}",
            f"{base_url}/{page}",
            f"{base_url}?start={page * 20}",
        ]

        for url in pagination_formats:
            try:
                soup = await self._fetch_page(url)
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

        selectors = [
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

        if not urls:
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href:
                    url = urljoin(self.base_url, href)
                    if self._is_valid_listing_url(url):
                        urls.add(url)

        return list(urls)

    def _is_valid_listing_url(self, url: str) -> bool:
        """Check if URL is a valid listing URL."""
        exclude_patterns = [
            "/login", "/signup", "/register",
            "/about", "/contact", "/help",
            "/faq", "/privacy", "/terms",
            "facebook.com", "twitter.com",
            "instagram.com", "youtube.com",
            "/blog", "/news", "/profile", "/account",
        ]
        
        if any(pattern in url.lower() for pattern in exclude_patterns):
            return False
            
        include_patterns = [
            "/cars/", "/vehicle/", "/ad/",
            "/listing/", "/automotive/", "/car/",
            "/vehicles/", "/used/", "/new/",
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

            seller_name, seller_type = self._extract_seller_info(soup, page_text)

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

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract vehicle title from the page."""
        h1 = soup.find("h1")
        if h1:
            title = self._clean_text(h1.get_text())
            if title and len(title) > 2:
                return title

        title_selectors = [
            ".advert-title", ".listing-title", ".item-title",
            ".product-title", ".title", '[itemprop="name"]',
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

        meta_title = soup.find("meta", {"property": "og:title"})
        if meta_title:
            content = meta_title.get("content")
            if content:
                title = self._clean_text(content)
                if title:
                    return title

        title_tag = soup.find("title")
        if title_tag:
            title = self._clean_text(title_tag.get_text())
            for separator in ["|", "-", "–", "—"]:
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
        """Extract listing ID from URL or page."""
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        listing_id = path.split("/")[-1]
        
        common_words = ["car", "used", "new", "vehicle", "listing", "cars", "vehicles", "ad"]
        if listing_id and len(listing_id) > 2 and listing_id.lower() not in common_words:
            if re.match(r'^[a-zA-Z0-9\-_]+$', listing_id):
                return listing_id

        id_patterns = [r'/cars/(\d+)', r'/ad/(\d+)', r'/listing/(\d+)', r'/(\d+)/']
        for pattern in id_patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        meta_id = soup.find("meta", {"name": "listing-id"})
        if meta_id:
            content = meta_id.get("content")
            if content:
                return content

        return str(abs(hash(url)))[:10]

    # ============================================================
    # EXTRACT PRICE
    # ============================================================

    def _extract_price(self, soup: BeautifulSoup, page_text: str) -> Optional[float]:
        """Extract price from the page."""
        price_selectors = [
            ".price", ".advert-price", ".listing-price",
            ".item-price", ".product-price", "[itemprop='price']",
            ".amount", ".sale-price", ".price-amount",
            "span.price", "div.price",
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
                    return float(price_str)
                except ValueError:
                    continue

        return None

    # ============================================================
    # EXTRACT MAKE AND MODEL
    # ============================================================

    def _extract_make_model(self, title: str) -> tuple:
        """Extract make and model from the title."""
        if not title:
            return "", ""

        makes = [
            "Toyota", "Nissan", "Honda", "Subaru", "Mazda",
            "Mercedes", "BMW", "Audi", "Volkswagen", "Ford",
            "Mitsubishi", "Isuzu", "Suzuki", "Hyundai", "Kia",
            "Land Rover", "Lexus", "Volvo", "Peugeot", "Citroen",
            "Renault", "Fiat", "Jeep", "Chevrolet", "Dodge",
            "Chrysler", "Porsche", "Jaguar", "Bentley", "Ferrari",
        ]

        title_lower = title.lower()
        
        for make in makes:
            if make.lower() in title_lower:
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

        detail_selectors = [
            ".details", ".specs", ".specifications",
            ".features", ".info", ".attributes",
            ".vehicle-details", ".car-details",
        ]

        for selector in detail_selectors:
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

        if details["year"] is None:
            year_match = re.search(r'(\d{4})', text)
            if year_match:
                year = int(year_match.group(1))
                if 1980 <= year <= datetime.now().year + 1:
                    details["year"] = year

        if details["mileage"] is None:
            mileage_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*km', text, re.IGNORECASE)
            if mileage_match:
                try:
                    details["mileage"] = int(mileage_match.group(1).replace(",", ""))
                except ValueError:
                    pass

        if details["engine_size"] is None:
            engine_match = re.search(r'(\d+\.?\d*)\s*l', text, re.IGNORECASE)
            if engine_match:
                try:
                    details["engine_size"] = float(engine_match.group(1))
                except ValueError:
                    pass

        if details["fuel_type"] is None:
            if "petrol" in text_lower:
                details["fuel_type"] = "Petrol"
            elif "diesel" in text_lower:
                details["fuel_type"] = "Diesel"
            elif "electric" in text_lower:
                details["fuel_type"] = "Electric"

        if details["transmission"] is None:
            if "automatic" in text_lower:
                details["transmission"] = "Automatic"
            elif "manual" in text_lower:
                details["transmission"] = "Manual"

    # ============================================================
    # EXTRACT LOCATION
    # ============================================================

    def _extract_location(self, soup: BeautifulSoup, page_text: str) -> str:
        """Extract location from the page."""
        location_selectors = [
            ".location", ".vehicle-location", "[itemprop='location']",
            ".address", ".seller-location", ".city", ".area",
        ]

        for selector in location_selectors:
            try:
                location_element = soup.select_one(selector)
                if location_element:
                    location = self._clean_text(location_element.get_text())
                    if location and len(location) > 2:
                        return location
            except Exception:
                continue

        location_patterns = [
            r'Location:\s*([^,\.]+)',
            r'Located in:\s*([^,\.]+)',
            r'City:\s*([^,\.]+)',
        ]

        for pattern in location_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                location = self._clean_text(match.group(1))
                if location and len(location) > 2:
                    return location

        return "Kenya"

    # ============================================================
    # EXTRACT SELLER INFO
    # ============================================================

    def _extract_seller_info(self, soup: BeautifulSoup, page_text: str) -> tuple:
        """Extract seller name and type."""
        seller_name = "Jiji"
        seller_type = "Dealer"

        seller_selectors = [
            ".seller-name", ".dealer-name", ".seller",
            ".dealer", ".vendor", "[itemprop='seller']",
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

        if "private seller" in page_text.lower():
            seller_type = "Private"

        return seller_name, seller_type

    # ============================================================
    # EXTRACT CONDITION
    # ============================================================

    def _extract_condition(self, soup: BeautifulSoup, page_text: str) -> str:
        """Extract vehicle condition."""
        page_text_lower = page_text.lower()

        if "brand new" in page_text_lower or "new car" in page_text_lower:
            return "New"
        elif "certified pre-owned" in page_text_lower:
            return "Certified Pre-Owned"
        elif "used car" in page_text_lower or "pre-owned" in page_text_lower:
            return "Used"

        return "Used"
