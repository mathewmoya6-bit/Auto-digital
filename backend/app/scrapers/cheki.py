# app/scrapers/cheki.py
# Auto-D Kenya - Cheki Scraper
# ================================================================
# TYPE: SCRAPER - Cheki.co.ke vehicle listings scraper

import asyncio
import random
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from datetime import datetime

from bs4 import BeautifulSoup

from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class ChekiScraper(BaseScraper):
    """
    Scraper for Cheki.co.ke vehicle listings.
    
    Cheki is a leading automotive marketplace in Kenya.
    This scraper extracts vehicle listings with details like:
    - Make, Model, Year, Mileage
    - Price, Location
    - Images and descriptions
    """
    
    def __init__(self):
        super().__init__(
            source_name="cheki",
            base_url="https://www.cheki.co.ke"
        )
        self.search_url = "https://www.cheki.co.ke/kenya/used-cars-for-sale"
        self.listing_selectors = {
            "title": "h1.listing-title",
            "price": "span.listing-price",
            "description": "div.listing-description",
            "location": "span[data-field='location']",
            "image": "img.listing-image"
        }
    
    async def scrape(self, pages: int = 3, limit_per_page: int = 20) -> List[Dict[str, Any]]:
        """
        Scrape vehicle listings from Cheki.
        
        Args:
            pages: Number of pages to scrape (default: 3)
            limit_per_page: Number of listings per page (default: 20)
            
        Returns:
            List of vehicle listings with normalized data
        """
        all_listings = []
        
        for page in range(1, pages + 1):
            logger.info(f"📄 Scraping Cheki page {page}")
            
            try:
                params = {"page": page} if page > 1 else {}
                soup = await self._fetch_page(self.search_url, params)
                
                if not soup:
                    logger.warning(f"No HTML returned for page {page}")
                    break
                
                # Find listing URLs
                urls = self._extract_listing_urls(soup)
                
                if not urls:
                    logger.warning(f"No listings found on page {page}")
                    break
                
                logger.info(f"Found {len(urls)} listing URLs on page {page}")
                
                # Parse each listing
                for url in urls:
                    try:
                        listing = await self._parse_listing(url)
                        if listing:
                            all_listings.append(listing)
                            self.stats["successful"] += 1
                    except Exception as e:
                        logger.error(f"Error parsing listing {url}: {str(e)}")
                        self.stats["failed"] += 1
                    
                    # Delay between requests to avoid rate limiting
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Delay between pages
                await asyncio.sleep(random.uniform(1.5, 3))
                
            except Exception as e:
                logger.error(f"Error scraping Cheki page {page}: {str(e)}")
                break
        
        logger.info(f"✅ Scraped {len(all_listings)} total listings from Cheki")
        return all_listings
    
    def _extract_listing_urls(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract listing URLs from search results page.
        
        Args:
            soup: BeautifulSoup object of the search results page
            
        Returns:
            List of listing URLs
        """
        urls = []
        links = soup.select("a.listing-link")
        
        for link in links:
            href = link.get("href")
            if href:
                full_url = urljoin(self.base_url, href)
                if full_url not in urls:
                    urls.append(full_url)
        
        return urls
    
    async def _parse_listing(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single listing page.
        
        Args:
            url: Listing URL
            
        Returns:
            Dict with listing data or None if parsing fails
        """
        try:
            soup = await self._fetch_page(url)
            if not soup:
                return None
            
            # Extract title
            title_elem = soup.select_one(self.listing_selectors["title"])
            title = title_elem.get_text(strip=True) if title_elem else None
            
            # Extract price
            price_elem = soup.select_one(self.listing_selectors["price"])
            price_text = price_elem.get_text(strip=True) if price_elem else None
            price = self._parse_price(price_text) if price_text else None
            
            # Extract details from listing details
            details = self._extract_details(soup)
            
            # Extract image
            image_elem = soup.select_one(self.listing_selectors["image"])
            image_url = image_elem.get("src") if image_elem else None
            
            # Generate source ID
            source_id = urlparse(url).path.strip("/").split("/")[-1]
            if not source_id:
                source_id = f"cheki_{int(datetime.utcnow().timestamp())}"
            
            # Build listing data
            listing = {
                "listing_id": source_id,
                "source_id": source_id,
                "title": title,
                "price": price,
                "currency": "KES",
                "mileage": self._parse_mileage(details.get("mileage", "")),
                "year": self._parse_year(details.get("year", "")),
                "make": details.get("make", ""),
                "model": details.get("model", ""),
                "variant": details.get("trim", "") or details.get("variant", ""),
                "trim": details.get("trim", ""),
                "location": details
