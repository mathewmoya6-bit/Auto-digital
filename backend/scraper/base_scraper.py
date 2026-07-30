# app/scrapers/base_scraper.py
# Auto-D Kenya - Base Scraper Service
# ================================================================
# TYPE: SERVICE - Base scraper class with common functionality

import asyncio
import json
import logging
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse, urljoin

import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.database import get_supabase

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Base scraper class with common functionality for all marketplace scrapers.
    
    This class provides:
    - HTTP session management with retry logic
    - HTML/JSON fetching with error handling
    - Price, mileage, year parsing utilities
    - Database saving functionality
    - Statistics tracking
    """
    
    def __init__(self, source_name: str, base_url: str):
        """
        Initialize the scraper.
        
        Args:
            source_name: Name of the source (e.g., "jiji", "cheki")
            base_url: Base URL of the marketplace
        """
        self.source_name = source_name
        self.base_url = base_url
        self.ua = UserAgent()
        self.session = None
        self.results = []
        self.stats = {
            "total_scraped": 0,
            "successful": 0,
            "failed": 0,
            "start_time": None,
            "end_time": None,
            "duplicates": 0
        }
        self.known_listing_ids = set()
        self.supabase = get_supabase()
    
    # ─── HTTP SESSION MANAGEMENT ──────────────────────────────────
    
    async def _get_session(self) -> httpx.AsyncClient:
        """
        Get or create HTTP session with retry logic.
        
        Returns:
            httpx.AsyncClient: HTTP client session
        """
        if self.session is None or self.session.is_closed:
            timeout = httpx.Timeout(settings.SCRAPE_TIMEOUT_SECONDS, connect=10.0)
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            self.session = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                follow_redirects=True,
                headers=self._get_headers()
            )
        return self.session
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers for HTTP requests.
        
        Returns:
            Dict[str, str]: Request headers
        """
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,sw;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        }
    
    # ─── FETCH METHODS WITH RETRY ─────────────────────────────────
    
    @retry(
        stop=stop_after_attempt(settings.SCRAPE_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout))
    )
    async def _fetch_page(self, url: str, params: Optional[Dict] = None) -> Optional[BeautifulSoup]:
        """
        Fetch a page and return BeautifulSoup object.
        
        Args:
            url: URL to fetch
            params: Optional query parameters
            
        Returns:
            Optional[BeautifulSoup]: Parsed HTML or None if failed
        """
        try:
            session = await self._get_session()
            response = await session.get(url, params=params)
            response.raise_for_status()
            
            # Check if response is HTML
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type:
                return BeautifulSoup(response.text, "html.parser")
            else:
                logger.warning(f"Non-HTML response from {url}: {content_type}")
                return None
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching {url}: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            raise
    
    @retry(
        stop=stop_after_attempt(settings.SCRAPE_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _fetch_json(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Fetch a JSON response.
        
        Args:
            url: URL to fetch
            params: Optional query parameters
            
        Returns:
            Optional[Dict]: JSON response or None if failed
        """
        try:
            session = await self._get_session()
            response = await session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching JSON from {url}: {str(e)}")
            raise
    
    # ─── PARSING UTILITIES ────────────────────────────────────────
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """
        Parse price from text.
        
        Args:
            price_text: Raw price text
            
        Returns:
            Optional[float]: Parsed price or None
        """
        if not price_text:
            return None
        
        # Remove currency symbols and commas
        cleaned = price_text.replace("KSh", "").replace("KES", "").replace("Ksh", "")
        cleaned = cleaned.replace("$", "").replace("€", "").replace("£", "")
        cleaned = cleaned.replace(",", "").replace(" ", "")
        
        # Extract numbers and decimal
        import re
        match = re.search(r'(\d+(?:\.\d+)?)', cleaned)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None
    
    def _parse_mileage(self, mileage_text: str) -> Optional[int]:
        """
        Parse mileage from text.
        
        Args:
            mileage_text: Raw mileage text
            
        Returns:
            Optional[int]: Parsed mileage or None
        """
        if not mileage_text:
            return None
        
        import re
        cleaned = mileage_text.replace("km", "").replace("KM", "").replace("kms", "")
        cleaned = cleaned.replace(",", "").replace(" ", "")
        match = re.search(r'(\d+)', cleaned)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None
    
    def _parse_year(self, year_text: str) -> Optional[int]:
        """
        Parse year from text.
        
        Args:
            year_text: Raw year text
            
        Returns:
            Optional[int]: Parsed year or None
        """
        if not year_text:
            return None
        
        import re
        match = re.search(r'(19|20)\d{2}', year_text)
        if match:
            try:
                return int(match.group(0))
            except ValueError:
                return None
        return None
    
    def _parse_engine_size(self, engine_text: str) -> Optional[int]:
        """
        Parse engine size from text.
        
        Args:
            engine_text: Raw engine text (e.g., "1500cc", "1.5L")
            
        Returns:
            Optional[int]: Engine size in cc or None
        """
        if not engine_text:
            return None
        
        import re
        # Remove spaces and convert to lowercase
        cleaned = engine_text.lower().replace(" ", "")
        
        # Try to match cc format
        match = re.search(r'(\d+)\s*cc', cleaned)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        
        # Try to match L format
        match = re.search(r'(\d+(?:\.\d+)?)\s*l', cleaned)
        if match:
            try:
                return int(float(match.group(1)) * 1000)
            except ValueError:
                pass
        
        # Try to match plain number
        match = re.search(r'(\d+)', cleaned)
        if match:
            try:
                num = int(match.group(1))
                # If number is small (e.g., 1.5), assume it's in litres
                if num < 10:
                    return int(num * 1000)
                return num
            except ValueError:
                pass
        
        return None
    
    def _parse_fuel_type(self, fuel_text: str) -> Optional[str]:
        """
        Parse fuel type from text.
        
        Args:
            fuel_text: Raw fuel text
            
        Returns:
            Optional[str]: Standardized fuel type
        """
        if not fuel_text:
            return None
        
        fuel_text = fuel_text.lower().strip()
        
        fuel_mappings = {
            "petrol": ["petrol", "gasoline", "super", "unleaded", "regular"],
            "diesel": ["diesel", "turbo diesel", "tdi"],
            "electric": ["electric", "ev", "electric vehicle", "battery"],
            "hybrid": ["hybrid", "hev", "plug-in hybrid", "phev"],
            "lpg": ["lpg", "autogas", "propane"],
            "cng": ["cng", "compressed natural gas"],
            "ethanol": ["ethanol", "flex fuel"]
        }
        
        for fuel_type, keywords in fuel_mappings.items():
            for keyword in keywords:
                if keyword in fuel_text:
                    return fuel_type
        
        return None
    
    def _parse_transmission(self, trans_text: str) -> Optional[str]:
        """
        Parse transmission type from text.
        
        Args:
            trans_text: Raw transmission text
            
        Returns:
            Optional[str]: Standardized transmission type
        """
        if not trans_text:
            return None
        
        trans_text = trans_text.lower().strip()
        
        if "automatic" in trans_text or "auto" in trans_text:
            return "Automatic"
        elif "manual" in trans_text or "stick" in trans_text:
            return "Manual"
        elif "cvt" in trans_text:
            return "CVT"
        elif "semi" in trans_text or "automated" in trans_text:
            return "Semi-Automatic"
        
        return None
    
    def _parse_body_type(self, body_text: str) -> Optional[str]:
        """
        Parse body type from text.
        
        Args:
            body_text: Raw body text
            
        Returns:
            Optional[str]: Standardized body type
        """
        if not body_text:
            return None
        
        body_text = body_text.lower().strip()
        
        body_mappings = {
            "suv": ["suv", "sport utility", "crossover", "4x4", "off-road"],
            "sedan": ["sedan", "saloon", "saloons"],
            "hatchback": ["hatchback", "hatch", "3-door", "5-door"],
            "pickup": ["pickup", "pick-up", "double cab", "single cab", "bakkie"],
            "van": ["van", "minivan", "people carrier", "mpv"],
            "truck": ["truck", "lorry", "heavy duty"],
            "bus": ["bus", "coach", "minibus", "matatu"],
            "coupe": ["coupe", "coupé", "sports car"],
            "convertible": ["convertible", "cabriolet", "roadster", "soft top"],
            "wagon": ["wagon", "estate", "station wagon", "shooting brake"]
        }
        
        for body_type, keywords in body_mappings.items():
            for keyword in keywords:
                if keyword in body_text:
                    return body_type
        
        return None
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison.
        
        Args:
            text: Raw text
            
        Returns:
            str: Normalized text
        """
        if not text:
            return ""
        return " ".join(text.strip().lower().split())
    
    # ─── DATABASE OPERATIONS ──────────────────────────────────────
    
    async def _save_to_database(self, listings: List[Dict[str, Any]]) -> int:
        """
        Save scraped listings to database.
        
        Args:
            listings: List of listing dictionaries
            
        Returns:
            int: Number of listings saved
        """
        if not listings:
            return 0
        
        try:
            saved_count = 0
            
            for listing in listings:
                # Generate source_id if not present
                if not listing.get("source_id"):
                    listing["source_id"] = f"{self.source_name}_{int(datetime.utcnow().timestamp())}_{listing.get('listing_id', '')}"
                
                # Check if listing already exists
                existing = self.supabase.table("market_listings").select("id").eq("source_id", listing.get("source_id")).execute()
                
                if existing.data:
                    # Update existing listing
                    self.supabase.table("market_listings").update({
                        "price": listing.get("price"),
                        "title": listing.get("title"),
                        "description": listing.get("description"),
                        "mileage": listing.get("mileage"),
                        "year": listing.get("year"),
                        "location": listing.get("location"),
                        "url": listing.get("url"),
                        "updated_at": datetime.utcnow().isoformat(),
                        "status": "active"
                    }).eq("id", existing.data[0]["id"]).execute()
                    self.stats["duplicates"] += 1
                else:
                    # Insert new listing
                    self.supabase.table("market_listings").insert({
                        "source": self.source_name,
                        "source_id": listing.get("source_id"),
                        "title": listing.get("title"),
                        "description": listing.get("description"),
                        "price": listing.get("price"),
                        "mileage": listing.get("mileage"),
                        "year": listing.get("year"),
                        "make": listing.get("make"),
                        "model": listing.get("model"),
                        "variant": listing.get("variant"),
                        "location": listing.get("location"),
                        "url": listing.get("url"),
                        "image_url": listing.get("image_url"),
                        "scraped_at": datetime.utcnow().isoformat(),
                        "created_at": datetime.utcnow().isoformat(),
                        "status": "active"
                    }).execute()
                    saved_count += 1
            
            logger.info(f"Saved {saved_count} new listings from {self.source_name} (updated {self.stats['duplicates']})")
            return saved_count
            
        except Exception as e:
            logger.error(f"Error saving to database: {str(e)}")
            return 0
    
    async def _update_market_prices(self, listings: List[Dict[str, Any]]) -> None:
        """
        Update market prices for valuation.
        
        Args:
            listings: List of listing dictionaries
        """
        if not listings:
            return
        
        try:
            # Group by make/model
            grouped = {}
            for listing in listings:
                make = listing.get("make", "").strip()
                model = listing.get("model", "").strip()
                if make and model:
                    key = f"{make}|{model}"
                    if key not in grouped:
                        grouped[key] = []
                    grouped[key].append(listing)
            
            for key, group in grouped.items():
                make, model = key.split("|") if "|" in key else (key, "")
                if not make or not model:
                    continue
                
                # Calculate statistics
                prices = [l.get("price", 0) for l in group if l.get("price") and l.get("price") > 0]
                if not prices:
                    continue
                
                avg_price = sum(prices) / len(prices)
                min_price = min(prices)
                max_price = max(prices)
                median_price = sorted(prices)[len(prices) // 2]
                
                # Insert or update market price
                existing = self.supabase.table("market_prices").select("id").eq("make", make).eq("model", model).execute()
                
                price_data = {
                    "make": make,
                    "model": model,
                    "avg_price": avg_price,
                    "min_price": min_price,
                    "max_price": max_price,
                    "median_price": median_price,
                    "sample_count": len(prices),
                    "source": self.source_name,
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                if existing.data:
                    self.supabase.table("market_prices").update(price_data).eq("id", existing.data[0]["id"]).execute()
                else:
                    self.supabase.table("market_prices").insert(price_data).execute()
                    
        except Exception as e:
            logger.error(f"Error updating market prices: {str(e)}")
    
    # ─── NORMALIZATION ────────────────────────────────────────────
    
    def normalize_listing(self, listing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert marketplace data into Auto-D format.
        
        Args:
            listing: Raw listing data from marketplace
            
        Returns:
            Dict[str, Any]: Normalized listing data
        """
        return {
            "source": self.source_name,
            "listing_id": listing.get("listing_id"),
            "source_id": listing.get("source_id"),
            "url": listing.get("url"),
            "make": listing.get("make"),
            "model": listing.get("model"),
            "variant": listing.get("trim") or listing.get("variant"),
            "trim": listing.get("trim"),
            "year": listing.get("year"),
            "price": listing.get("price"),
            "currency": listing.get("currency", "KES"),
            "mileage": listing.get("mileage"),
            "engine_size": listing.get("engine_size"),
            "fuel_type": listing.get("fuel_type"),
            "transmission": listing.get("transmission"),
            "body_type": listing.get("body_type"),
            "location": listing.get("location"),
            "seller": listing.get("seller"),
            "title": listing.get("title"),
            "description": listing.get("description"),
            "image_url": listing.get("image_url"),
            "scraped_at": datetime.utcnow().isoformat()
        }
    
    # ─── CLEANUP ──────────────────────────────────────────────────
    
    async def _cleanup(self) -> None:
        """
        Clean up resources.
        """
        if self.session and not self.session.is_closed:
            await self.session.aclose()
            self.session = None
    
    # ─── ABSTRACT METHODS ─────────────────────────────────────────
    
    @abstractmethod
    async def scrape(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Main scrape method to be implemented by subclasses.
        
        Returns:
            List[Dict[str, Any]]: List of scraped listings
        """
        pass
    
    # ─── RUN METHOD ──────────────────────────────────────────────
    
    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Run the scraper and return results with statistics.
        
        Args:
            **kwargs: Additional arguments for the scraper
            
        Returns:
            Dict[str, Any]: Scraper results and statistics
        """
        self.stats["start_time"] = datetime.utcnow()
        
        try:
            logger.info(f"Starting scraper: {self.source_name}")
            self.results = await self.scrape(**kwargs)
            self.stats["successful"] = len(self.results)
            self.stats["total_scraped"] = len(self.results)
            
            # Normalize all listings
            normalized_listings = [self.normalize_listing(r) for r in self.results]
            
            # Save to database
            saved = await self._save_to_database(normalized_listings)
            
            # Update market prices
            await self._update_market_prices(normalized_listings)
            
            logger.info(f"Scraper {self.source_name} completed: {saved} new listings")
            
        except Exception as e:
            logger.error(f"Scraper {self.source_name} failed: {str(e)}")
            self.stats["failed"] = 1
            
        finally:
            await self._cleanup()
            self.stats["end_time"] = datetime.utcnow()
            duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
            self.stats["duration_seconds"] = round(duration, 2)
        
        return {
            "source": self.source_name,
            "stats": self.stats,
            "results": self.results[:100]  # Return first 100 results
        }
