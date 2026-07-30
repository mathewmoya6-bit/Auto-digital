# app/modules/scraper/jiji.py
# Auto-D Kenya - Jiji Scraper
# ================================================================
# TYPE: MODULE - Jiji specific scraper

import asyncio
import random
import logging
from typing import List, Dict, Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class JijiScraper(BaseScraper):
    """Scraper for Jiji.co.ke."""
    
    def __init__(self):
        super().__init__(
            source_name="jiji",
            base_url="https://jiji.co.ke"
        )
        self.search_url = "https://jiji.co.ke/cars"
    
    async def scrape(self, pages: int = 3, limit_per_page: int = 20) -> List[Dict[str, Any]]:
        """Scrape vehicle listings from Jiji."""
        all_listings = []
        
        for page in range(1, pages + 1):
            logger.info(f"Scraping Jiji page {page}")
            
            try:
                params = {"page": page, "limit": limit_per_page}
                soup = await self._fetch_page(self.search_url, params)
                
                if not soup:
                    break
                
                # Find listing URLs
                urls = []
                links = soup.select("a[data-testid='ad-link']")
                for link in links:
                    href = link.get("href")
                    if href:
                        full_url = urljoin(self.base_url, href)
                        if full_url not in urls:
                            urls.append(full_url)
                
                # Parse each listing
                for url in urls:
                    listing = await self._parse_listing(url)
                    if listing:
                        all_listings.append(listing)
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                
                await asyncio.sleep(random.uniform(1, 2))
                
            except Exception as e:
                logger.error(f"Error scraping Jiji page {page}: {str(e)}")
                break
        
        logger.info(f"Scraped {len(all_listings)} listings from Jiji")
        return all_listings
    
    async def _parse_listing(self, url: str) -> Dict[str, Any]:
        """Parse a single listing page."""
        try:
            soup = await self._fetch_page(url)
            if not soup:
                return {}
            
            # Extract basic info
            title_elem = soup.select_one("h1[data-testid='ad-title']")
            title = title_elem.get_text(strip=True) if title_elem else None
            
            price_elem = soup.select_one("span[data-testid='ad-price']")
            price_text = price_elem.get_text(strip=True) if price_elem else None
            price = self._parse_price(price_text) if price_text else None
            
            # Extract details
            details = self._extract_vehicle_details(soup, {
                "make": "div:contains('Make') + div",
                "model": "div:contains('Model') + div",
                "year": "div:contains('Year') + div",
                "mileage": "div:contains('Mileage') + div",
                "location": "a[data-testid='ad-location']"
            })
            
            # Extract image
            image_elem = soup.select_one("img[data-testid='ad-image']")
            image_url = image_elem.get("src") if image_elem else None
            
            # Generate source ID
            source_id = urlparse(url).path.strip("/").split("/")[-1]
            
            return {
                "listing_id": source_id,
                "title": title,
                "price": price,
                "mileage": self._parse_mileage(details.get("mileage")),
                "year": self._parse_year(details.get("year")),
                "make": details.get("make"),
                "model": details.get("model"),
                "location": details.get("location"),
                "url": url,
                "image_url": image_url
            }
            
        except Exception as e:
            logger.error(f"Error parsing listing {url}: {str(e)}")
            return {}
