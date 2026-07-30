# app/modules/scraper/autochek.py
# Auto-D Kenya - Autochek Scraper
# ================================================================
# TYPE: MODULE - Autochek specific scraper

import logging
from typing import List, Dict, Any

from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class AutochekScraper(BaseScraper):
    """Scraper for Autochek.co.ke."""
    
    def __init__(self):
        super().__init__(
            source_name="autochek",
            base_url="https://www.autochek.co.ke"
        )
        self.api_url = "https://api.autochek.co.ke/v1/listings"
    
    async def scrape(self, pages: int = 3, limit_per_page: int = 20) -> List[Dict[str, Any]]:
        """Scrape vehicle listings from Autochek."""
        all_listings = []
        
        for page in range(1, pages + 1):
            logger.info(f"Scraping Autochek page {page}")
            
            try:
                params = {
                    "page": page,
                    "limit": limit_per_page,
                    "status": "active",
                    "sort": "newest"
                }
                
                data = await self._fetch_json(self.api_url, params)
                if data and data.get("data"):
                    for item in data["data"]:
                        listing = {
                            "listing_id": str(item.get("id", "")),
                            "title": item.get("title", ""),
                            "price": item.get("price", 0),
                            "description": item.get("description", ""),
                            "mileage": item.get("mileage", 0),
                            "year": item.get("year", 0),
                            "make": item.get("make", {}).get("name", "") if item.get("make") else "",
                            "model": item.get("model", {}).get("name", "") if item.get("model") else "",
                            "variant": item.get("variant", {}).get("name", "") if item.get("variant") else "",
                            "location": item.get("location", {}).get("city", "") if item.get("location") else "",
                            "url": item.get("url", ""),
                            "image_url": item.get("images", [{}])[0].get("url", "") if item.get("images") else "",
                            "fuel_type": item.get("fuel_type", ""),
                            "transmission": item.get("transmission", ""),
                            "body_type": item.get("body_type", "")
                        }
                        all_listings.append(listing)
                
                await asyncio.sleep(random.uniform(0.5, 1))
                
            except Exception as e:
                logger.error(f"Error scraping Autochek page {page}: {str(e)}")
                break
        
        logger.info(f"Scraped {len(all_listings)} listings from Autochek")
        return all_listings
