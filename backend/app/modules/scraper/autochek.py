# app/modules/scraper/autochek.py
# ================================================================
# Auto-D Kenya - Autochek Vehicle Scraper
# ================================================================
# TYPE: MODULE - Autochek.co.ke listing scraper
# ================================================================

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.modules.scraper.base import BaseScraper

logger = logging.getLogger(__name__)


class AutochekScraper(BaseScraper):
    """
    Autochek.co.ke vehicle listing scraper.
    
    Extracts:
    - Vehicle listings from search results
    - Detailed vehicle information from individual pages
    - Pricing, specifications, and seller details
    """

    def __init__(self):
        """Initialize Autochek scraper."""
        super().__init__()
        self.base_url = "https://www.autochek.co.ke"
        self.search_url = f"{self.base_url}/cars"

    # ============================================================
    # MAIN SCRAPE METHODS
    # ============================================================

    async def scrape(
        self,
        pages: int = 3,
        limit_per_page: int = 20,
    ) -> Dict[str, Any]:
        """
        Scrape Autochek vehicle listings.
        
        Args:
            pages: Number of pages to scrape
            limit_per_page: Listings per page
            
        Returns:
            Dict[str, Any]: Scraped listings and metadata
        """
        try:
            logger.info(f"Starting Autochek scrape: {pages} pages, {limit_per_page} per page")
            
            all_listings = []
            total_listings = 0
            failed_pages = 0
            
            for page_num in range(1, pages + 1):
                try:
                    logger.info(f"Scraping Autochek page {page_num}/{pages}")
                    
                    # Build URL with pagination
                    if page_num == 1:
                        url = self.search_url
                    else:
                        url = f"{self.search_url}?page={page_num}"
                    
                    # Fetch page
                    soup = await self._fetch_page(url)
                    
                    if soup is None:
                        logger.warning(f"Failed to fetch Autochek page {page_num}")
                        failed_pages += 1
                        continue
                    
                    # Parse listing URLs from page
                    listing_urls = self._extract_listing_urls(soup)
                    
                    if not listing_urls:
                        logger.warning(f"No listings found on Autochek page {page_num}")
                        failed_pages += 1
                        continue
                    
                    logger.info(f"Found {len(listing_urls)} listing URLs on page {page_num}")
                    
                    # Process each listing
                    for listing_url in listing_urls:
                        try:
                            listing = await self._parse_listing(listing_url)
                            if listing:
                                all_listings.append(listing)
                                total_listings += 1
                        except Exception as e:
                            logger.debug(f"Failed to parse listing {listing_url}: {e}")
                            continue
                    
                    # Respect rate limits
                    await self._rate_limit()
                    
                except Exception as e:
                    logger.error(f"Error scraping Autochek page {page_num}: {e}")
                    failed_pages += 1
                    continue
            
            logger.info(f"Autochek scrape complete: {total_listings} listings from {pages - failed_pages} pages")
            
            return {
                "listings": all_listings,
                "total_listings": total_listings,
                "pages_scraped": pages - failed_pages,
                "pages_failed": failed_pages,
                "source": "autochek",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as e:
            logger.exception(f"Autochek scrape failed: {e}")
            return {
                "listings": [],
                "total_listings": 0,
                "pages_scraped": 0,
                "pages_failed": pages,
                "source": "autochek",
                "error": str(e),
            }

    def _extract_listing_urls(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract listing URLs from search results page.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            List[str]: List of listing URLs
        """
        listing_urls = []
        
        selectors = [
            "a.listing-link",
            "a.vehicle-link",
            "a.car-link",
            "a.product-link",
            "a[href*='/cars/']",
            ".vehicle-card a",
            ".listing-card a",
            ".car-card a",
        ]
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    href = element.get("href")
                    if not href:
                        continue
                    
                    # Build full URL
                    if href.startswith("/"):
                        url = urljoin(self.base_url, href)
                    else:
                        url = href
                    
                    # Only include car listing URLs
                    if "/cars/" in url and url not in listing_urls:
                        listing_urls.append(url)
                        
            except Exception as e:
                logger.debug(f"Error extracting listing URLs with selector {selector}: {e}")
                continue
        
        # Limit to a reasonable number
        return listing_urls[:200]

    # ============================================================
    # PARSE INDIVIDUAL LISTING
    # ============================================================

    async def _parse_listing(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single Autochek vehicle listing.
        """
        try:
            soup = await self._fetch_page(url)
            
            if soup is None:
                return None
            
            title = self._extract_title(soup)
            if not title:
                return None
            
            make, model = self._extract_make_model(title)
            details = self._extract_vehicle_details(soup)
            
            listing = {
                "listing_id": self._extract_listing_id(url, soup),
                "title": title,
                "url": url,
                "price": self._extract_price(soup),
                "currency": "KES",
                "make": make,
                "model": model,
                "year": details.get("year"),
                "mileage": details.get("mileage"),
                "engine_size": details.get("engine_size"),
                "fuel_type": details.get("fuel_type"),
                "transmission": details.get("transmission"),
                "body_type": details.get("body_type"),
                "location": self._extract_location(soup),
                "seller_name": self._extract_seller_name(soup),
                "seller_type": self._extract_seller_type(soup),
                "condition": self._extract_condition(soup),
                "description": self._extract_description(soup),
                "images": self._extract_images(soup),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }
            
            return listing
            
        except Exception as e:
            logger.exception(f"Failed parsing listing {url}: {e}")
            return None

    # ============================================================
    # PRICE
    # ============================================================

    def _extract_price(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract vehicle price."""
        selectors = [
            ".price",
            ".vehicle-price",
            ".listing-price",
            "[itemprop='price']",
            ".amount",
            ".price-value",
            "span.price",
            "div.price",
        ]
        
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    price = self._parse_price(element.get_text(" ", strip=True))
                    if price:
                        return int(price)
            except Exception:
                continue
        
        return self._parse_price(soup.get_text(" ", strip=True))

    # ============================================================
    # DESCRIPTION
    # ============================================================

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract listing description."""
        selectors = [
            ".description",
            ".vehicle-description",
            ".listing-description",
            ".product-description",
            ".details",
            ".overview",
        ]
        
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    text = self._clean_text(element.get_text(" ", strip=True))
                    if len(text) > 20:
                        return text
            except Exception:
                continue
        
        meta = soup.find("meta", attrs={"name": "description"})
        if meta:
            return self._clean_text(meta.get("content", ""))
        
        return ""

    # ============================================================
    # IMAGES
    # ============================================================

    def _extract_images(self, soup: BeautifulSoup) -> List[str]:
        """Extract image URLs."""
        images = []
        
        selectors = [
            "img",
            ".gallery img",
            ".vehicle-gallery img",
            ".swiper img",
        ]
        
        for selector in selectors:
            try:
                for img in soup.select(selector):
                    src = img.get("src") or img.get("data-src") or img.get("data-lazy")
                    if not src:
                        continue
                    src = urljoin(self.base_url, src)
                    if src not in images:
                        images.append(src)
            except Exception:
                continue
        
        return images

    # ============================================================
    # SELLER
    # ============================================================

    def _extract_seller_name(self, soup: BeautifulSoup) -> str:
        """Extract seller name."""
        selectors = [
            ".dealer-name",
            ".seller-name",
            ".vendor-name",
            ".dealer",
        ]
        
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    text = self._clean_text(element.get_text(" ", strip=True))
                    if text:
                        return text
            except Exception:
                continue
        
        return "Autochek"

    def _extract_seller_type(self, soup: BeautifulSoup) -> str:
        """Extract seller type."""
        text = soup.get_text(" ", strip=True).lower()
        
        if "dealer" in text:
            return "Dealer"
        if "private seller" in text:
            return "Private"
        
        return "Dealer"

    # ============================================================
    # TITLE
    # ============================================================

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract vehicle title."""
        selectors = [
            "h1",
            ".vehicle-title",
            ".listing-title",
            ".product-title",
            ".car-title",
        ]
        
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    title = self._clean_text(element.get_text(" ", strip=True))
                    if title:
                        return title
            except Exception:
                continue
        
        meta = soup.find("meta", property="og:title")
        if meta:
            return self._clean_text(meta.get("content", ""))
        
        if soup.title:
            return self._clean_text(soup.title.get_text())
        
        return ""

    # ============================================================
    # MAKE / MODEL
    # ============================================================

    def _extract_make_model(self, title: str) -> tuple[str, str]:
        """Extract make and model from title."""
        if not title:
            return "", ""
        
        makes = [
            "Toyota", "Nissan", "Mazda", "Subaru", "Honda",
            "Suzuki", "Mitsubishi", "Mercedes", "Mercedes-Benz",
            "BMW", "Audi", "Volkswagen", "Lexus", "Hyundai",
            "Kia", "Ford", "Isuzu", "Peugeot", "Land Rover",
            "Range Rover", "Jeep", "Volvo"
        ]
        
        words = title.split()
        
        for i, word in enumerate(words):
            for make in makes:
                if word.lower() == make.split()[0].lower():
                    model = ""
                    if i + 1 < len(words):
                        model = words[i + 1]
                    return make, model
        
        return "", ""

    # ============================================================
    # LOCATION
    # ============================================================

    def _extract_location(self, soup: BeautifulSoup) -> str:
        """Extract vehicle location."""
        selectors = [
            ".location",
            ".vehicle-location",
            ".dealer-location",
            ".address",
            ".city",
        ]
        
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    location = self._clean_text(element.get_text(" ", strip=True))
                    if location:
                        return location
            except Exception:
                continue
        
        text = soup.get_text(" ", strip=True)
        cities = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Thika", "Machakos", "Kiambu"]
        
        for city in cities:
            if city.lower() in text.lower():
                return city
        
        return "Kenya"

    # ============================================================
    # CONDITION
    # ============================================================

    def _extract_condition(self, soup: BeautifulSoup) -> str:
        """Extract vehicle condition."""
        text = soup.get_text(" ", strip=True).lower()
        
        if "brand new" in text:
            return "New"
        if "used" in text or "pre-owned" in text:
            return "Used"
        
        return "Used"

    # ============================================================
    # LISTING ID
    # ============================================================

    def _extract_listing_id(self, url: str, soup: BeautifulSoup) -> str:
        """Extract listing ID from URL or soup."""
        path = urlparse(url).path
        slug = path.rstrip("/").split("/")[-1]
        
        if slug and len(slug) > 4:
            return slug
        
        meta = soup.find("meta", attrs={"name": "listing-id"})
        if meta:
            value = meta.get("content")
            if value:
                return value
        
        return str(abs(hash(url)))

    # ============================================================
    # VEHICLE DETAILS
    # ============================================================

    def _extract_vehicle_details(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract vehicle details from the page.
        
        Returns:
            Dict with year, mileage, engine_size, fuel_type, transmission, body_type
        """
        details = {
            "year": None,
            "mileage": None,
            "engine_size": None,
            "fuel_type": None,
            "transmission": None,
            "body_type": None,
        }
        
        # Try to find spec items
        spec_selectors = [
            ".spec-item",
            ".detail-item",
            ".feature-item",
            ".specification-item",
            "li.spec",
        ]
        
        for selector in spec_selectors:
            try:
                items = soup.select(selector)
                for item in items:
                    text = self._clean_text(item.get_text(" ", strip=True))
                    if not text:
                        continue
                    
                    text_lower = text.lower()
                    
                    # Year
                    if "year" in text_lower or "reg" in text_lower:
                        year_match = re.search(r"\b(19|20)\d{2}\b", text)
                        if year_match:
                            details["year"] = int(year_match.group())
                    
                    # Mileage
                    if "km" in text_lower or "mileage" in text_lower:
                        mileage_match = re.search(r"(\d+[,.]?\d*)\s*(?:km|kms|km)", text_lower)
                        if mileage_match:
                            details["mileage"] = int(re.sub(r"[^\d]", "", mileage_match.group(1)))
                    
                    # Engine size
                    if "cc" in text_lower or "engine" in text_lower:
                        engine_match = re.search(r"(\d+[,.]?\d*)\s*(?:cc|litre)", text_lower)
                        if engine_match:
                            details["engine_size"] = int(re.sub(r"[^\d]", "", engine_match.group(1)))
                    
                    # Fuel type
                    if "fuel" in text_lower:
                        if "petrol" in text_lower or "gasoline" in text_lower:
                            details["fuel_type"] = "Petrol"
                        elif "diesel" in text_lower:
                            details["fuel_type"] = "Diesel"
                        elif "electric" in text_lower:
                            details["fuel_type"] = "Electric"
                        elif "hybrid" in text_lower:
                            details["fuel_type"] = "Hybrid"
                    
                    # Transmission
                    if "transmission" in text_lower or "gear" in text_lower:
                        if "manual" in text_lower:
                            details["transmission"] = "Manual"
                        elif "automatic" in text_lower or "auto" in text_lower:
                            details["transmission"] = "Automatic"
                        elif "cvt" in text_lower:
                            details["transmission"] = "CVT"
                    
                    # Body type
                    body_types = ["suv", "sedan", "hatchback", "pickup", "van", "truck", "coupe", "convertible", "wagon"]
                    for body in body_types:
                        if body in text_lower:
                            details["body_type"] = body.title()
                            break
            except Exception:
                continue
        
        return details

    # ============================================================
    # OVERRIDES
    # ============================================================

    def _parse_price(self, text: str) -> Optional[int]:
        """Override price parsing."""
        return super()._parse_price(text)

    def _parse_year(self, text: str) -> Optional[int]:
        """Override year parsing."""
        return super()._parse_year(text)

    def _parse_mileage(self, text: str) -> Optional[int]:
        """Override mileage parsing."""
        return super()._parse_mileage(text)

    def _parse_engine_size(self, text: str) -> Optional[float]:
        """Override engine size parsing."""
        return super()._parse_engine_size(text)
