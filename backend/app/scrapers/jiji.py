# app/scrapers/jiji.py
# Auto-D Kenya - Jiji Scraper
# ================================================================
# TYPE: SCRAPER - Jiji.co.ke vehicle listings scraper

import asyncio
import random
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from datetime import datetime

from bs4 import BeautifulSoup

from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class JijiScraper(BaseScraper):
    """
    Scraper for Jiji.co.ke vehicle listings.
    
    Jiji is one of the largest marketplaces in Kenya.
    This scraper extracts vehicle listings with details like:
    - Make, Model, Year, Mileage
    - Price, Location
    - Images and descriptions
    """
    
    def __init__(self):
        super().__init__(
            source_name="jiji",
            base_url="https://jiji.co.ke"
        )
        self.search_url = "https://jiji.co.ke/cars"
        self.listing_selectors = {
            "title": "h1[data-testid='ad-title']",
            "price": "span[data-testid='ad-price']",
            "description": "div[data-testid='ad-description']",
            "location": "a[data-testid='ad-location']",
            "image": "img[data-testid='ad-image']"
        }
    
    async def scrape(self, pages: int = 3, limit_per_page: int = 20) -> List[Dict[str, Any]]:
        """
        Scrape vehicle listings from Jiji.
        
        Args:
            pages: Number of pages to scrape (default: 3)
            limit_per_page: Number of listings per page (default: 20)
            
        Returns:
            List of vehicle listings with normalized data
        """
        all_listings = []
        
        for page in range(1, pages + 1):
            logger.info(f"📄 Scraping Jiji page {page}")
            
            try:
                params = {"page": page, "limit": limit_per_page}
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
                logger.error(f"Error scraping Jiji page {page}: {str(e)}")
                break
        
        logger.info(f"✅ Scraped {len(all_listings)} total listings from Jiji")
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
        links = soup.select("a[data-testid='ad-link']")
        
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
            
            # Extract details from attribute sections
            details = self._extract_details(soup)
            
            # Extract image
            image_elem = soup.select_one(self.listing_selectors["image"])
            image_url = image_elem.get("src") if image_elem else None
            
            # Generate source ID
            source_id = urlparse(url).path.strip("/").split("/")[-1]
            if not source_id:
                source_id = f"jiji_{int(datetime.utcnow().timestamp())}"
            
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
                "location": details.get("location", ""),
                "url": url,
                "image_url": image_url,
                "fuel_type": self._parse_fuel_type(details.get("fuel type", "")),
                "transmission": self._parse_transmission(details.get("transmission", "")),
                "body_type": self._parse_body_type(details.get("body type", "")),
                "engine_size": self._parse_engine_size(details.get("engine", "")),
                "description": self._extract_description(soup),
                "seller": details.get("seller", ""),
                "scraped_at": datetime.utcnow().isoformat()
            }
            
            return listing
            
        except Exception as e:
            logger.error(f"Error parsing listing {url}: {str(e)}")
            return None
    
    def _extract_details(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extract vehicle details from attribute sections.
        
        Args:
            soup: BeautifulSoup object of the listing page
            
        Returns:
            Dict of attribute key-value pairs
        """
        details = {}
        
        # Try different selectors for attributes
        attr_sections = soup.select("div[data-testid='ad-attributes'] div")
        attr_sections.extend(soup.select(".attributes .attribute"))
        attr_sections.extend(soup.select(".specifications .spec"))
        
        for section in attr_sections:
            label_elem = section.select_one("span[data-testid='attribute-label']")
            value_elem = section.select_one("span[data-testid='attribute-value']")
            
            if not label_elem or not value_elem:
                # Try alternative selectors
                label_elem = section.select_one(".attr-label")
                value_elem = section.select_one(".attr-value")
            
            if label_elem and value_elem:
                key = label_elem.get_text(strip=True).lower()
                value = value_elem.get_text(strip=True)
                details[key] = value
        
        # Extract location
        location_elem = soup.select_one("a[data-testid='ad-location']")
        if location_elem:
            details["location"] = location_elem.get_text(strip=True)
        
        return details
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract description from listing page.
        
        Args:
            soup: BeautifulSoup object of the listing page
            
        Returns:
            Description text or None
        """
        desc_elem = soup.select_one("div[data-testid='ad-description']")
        if desc_elem:
            return desc_elem.get_text(strip=True)
        
        desc_elem = soup.select_one(".description .text")
        if desc_elem:
            return desc_elem.get_text(strip=True)
        
        return None
