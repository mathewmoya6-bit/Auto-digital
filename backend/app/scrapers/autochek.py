# app/scrapers/autochek.py
# Auto-D Kenya - Autochek Scraper
# ================================================================
# TYPE: SCRAPER - Autochek.co.ke vehicle listings scraper

import asyncio
import random
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urljoin, urlparse

import httpx

from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class AutochekScraper(BaseScraper):
    """
    Scraper for Autochek.co.ke vehicle listings via API.
    
    Autochek is a leading automotive marketplace in Kenya.
    This scraper extracts vehicle listings with details like:
    - Make, Model, Year, Mileage
    - Price, Location
    - Images and descriptions
    
    The scraper uses the official Autochek API to fetch listings
    in a structured format, making it more reliable than HTML scraping.
    """
    
    def __init__(self):
        super().__init__(
            source_name="autochek",
            base_url="https://www.autochek.co.ke"
        )
        self.api_url = "https://api.autochek.co.ke/v1/listings"
        
        # Additional API endpoints for more data
        self.vehicle_details_url = "https://api.autochek.co.ke/v1/vehicles"
        self.makes_url = "https://api.autochek.co.ke/v1/makes"
        self.models_url = "https://api.autochek.co.ke/v1/models"
    
    async def scrape(
        self, 
        pages: int = 3, 
        limit_per_page: int = 20,
        make: Optional[str] = None,
        model: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape vehicle listings from Autochek via API.
        
        Args:
            pages: Number of pages to scrape (default: 3)
            limit_per_page: Number of listings per page (default: 20)
            make: Filter by make (optional)
            model: Filter by model (optional)
            min_price: Minimum price filter (optional)
            max_price: Maximum price filter (optional)
            year: Filter by year (optional)
            
        Returns:
            List of vehicle listings with normalized data
        """
        all_listings = []
        
        for page in range(1, pages + 1):
            logger.info(f"📄 Scraping Autochek page {page}")
            
            try:
                # Build query parameters
                params = {
                    "page": page,
                    "limit": limit_per_page,
                    "status": "active",
                    "sort": "newest"
                }
                
                # Add optional filters
                if make:
                    params["make"] = make
                if model:
                    params["model"] = model
                if min_price:
                    params["min_price"] = min_price
                if max_price:
                    params["max_price"] = max_price
                if year:
                    params["year"] = year
                
                # Fetch listings from API
                data = await self._fetch_json(self.api_url, params)
                
                if not data or not data.get("data"):
                    logger.warning(f"No listings found on page {page}")
                    break
                
                listings_data = data.get("data", [])
                pagination = data.get("meta", {}).get("pagination", {})
                total_pages = pagination.get("total_pages", 0)
                
                logger.info(f"Found {len(listings_data)} listings on page {page} (total pages: {total_pages})")
                
                # Parse each listing
                for item in listings_data:
                    try:
                        listing = await self._parse_listing(item)
                        if listing:
                            all_listings.append(listing)
                            self.stats["successful"] += 1
                    except Exception as e:
                        logger.error(f"Error parsing listing: {str(e)}")
                        self.stats["failed"] += 1
                
                # If we've reached the last page, break
                if page >= total_pages:
                    logger.info(f"Reached last page ({total_pages})")
                    break
                
                # Delay between pages to avoid rate limiting
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                logger.error(f"Error scraping Autochek page {page}: {str(e)}")
                break
        
        logger.info(f"✅ Scraped {len(all_listings)} total listings from Autochek")
        return all_listings
    
    async def _parse_listing(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse listing from API data.
        
        Args:
            data: Raw API data for a listing
            
        Returns:
            Dict with normalized listing data or None if parsing fails
        """
        try:
            listing_id = str(data.get("id", ""))
            
            # Extract make, model, variant from nested objects
            make_data = data.get("make", {})
            model_data = data.get("model", {})
            variant_data = data.get("variant", {})
            
            make = make_data.get("name", "") if make_data else ""
            model = model_data.get("name", "") if model_data else ""
            variant = variant_data.get("name", "") if variant_data else ""
            
            # Extract location
            location_data = data.get("location", {})
            location = location_data.get("city", "") if location_data else ""
            state = location_data.get("state", "") if location_data else ""
            country = location_data.get("country", "") if location_data else ""
            
            # Format location string
            location_parts = [p for p in [location, state, country] if p]
            location_str = ", ".join(location_parts) if location_parts else ""
            
            # Extract images
            images = data.get("images", [])
            image_url = images[0].get("url", "") if images else ""
            
            # Extract seller
            seller_data = data.get("seller", {})
            seller = seller_data.get("name", "") if seller_data else ""
            seller_type = seller_data.get("type", "") if seller_data else ""
            
            # Extract features
            features = data.get("features", [])
            feature_list = [f.get("name", "") for f in features if f.get("name")]
            
            # Build normalized listing
            listing = {
                "listing_id": listing_id,
                "source_id": f"autochek_{listing_id}",
                "title": data.get("title", ""),
                "price": data.get("price", 0),
                "currency": data.get("currency", "KES"),
                "description": data.get("description", ""),
                "mileage": data.get("mileage", 0),
                "year": data.get("year", 0),
                "make": make,
                "model": model,
                "variant": variant,
                "trim": data.get("trim_level", ""),
                "location": location_str,
                "city": location,
                "state": state,
                "country": country,
                "url": data.get("url", ""),
                "image_url": image_url,
                "fuel_type": self._parse_fuel_type(data.get("fuel_type", "")),
                "transmission": self._parse_transmission(data.get("transmission", "")),
                "body_type": self._parse_body_type(data.get("body_type", "")),
                "engine_size": data.get("engine_size", ""),
                "engine_type": data.get("engine_type", ""),
                "drive_type": data.get("drive_type", ""),
                "color": data.get("color", ""),
                "seats": data.get("seats", 0),
                "doors": data.get("doors", 0),
                "seller": seller,
                "seller_type": seller_type,
                "features": feature_list,
                "status": data.get("status", "active"),
                "views": data.get("views", 0),
                "created_at": data.get("created_at", ""),
                "updated_at": data.get("updated_at", ""),
                "scraped_at": datetime.utcnow().isoformat()
            }
            
            return listing
            
        except Exception as e:
            logger.error(f"Error parsing Autochek listing: {str(e)}")
            return None
    
    async def get_makes(self) -> List[Dict[str, Any]]:
        """
        Get all available makes from Autochek.
        
        Returns:
            List of makes with id and name
        """
        try:
            data = await self._fetch_json(self.makes_url)
            if data and data.get("data"):
                return data.get("data", [])
            return []
        except Exception as e:
            logger.error(f"Error fetching makes from Autochek: {str(e)}")
            return []
    
    async def get_models(self, make_id: str) -> List[Dict[str, Any]]:
        """
        Get models for a specific make.
        
        Args:
            make_id: ID of the make
            
        Returns:
            List of models with id and name
        """
        try:
            url = f"{self.models_url}?make_id={make_id}"
            data = await self._fetch_json(url)
            if data and data.get("data"):
                return data.get("data", [])
            return []
        except Exception as e:
            logger.error(f"Error fetching models from Autochek: {str(e)}")
            return []
    
    async def get_vehicle_details(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific vehicle.
        
        Args:
            vehicle_id: ID of the vehicle
            
        Returns:
            Vehicle details or None if not found
        """
        try:
            url = f"{self.vehicle_details_url}/{vehicle_id}"
            data = await self._fetch_json(url)
            if data and data.get("data"):
                return data.get("data")
            return None
        except Exception as e:
            logger.error(f"Error fetching vehicle details from Autochek: {str(e)}")
            return None
    
    async def scrape_by_make(
        self,
        make: str,
        pages: int = 2,
        limit_per_page: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Scrape listings filtered by make.
        
        Args:
            make: Make name to filter by
            pages: Number of pages to scrape
            limit_per_page: Items per page
            
        Returns:
            List of vehicle listings
        """
        return await self.scrape(
            pages=pages,
            limit_per_page=limit_per_page,
            make=make
        )
    
    async def scrape_by_model(
        self,
        make: str,
        model: str,
        pages: int = 2,
        limit_per_page: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Scrape listings filtered by make and model.
        
        Args:
            make: Make name
            model: Model name
            pages: Number of pages to scrape
            limit_per_page: Items per page
            
        Returns:
            List of vehicle listings
        """
        return await self.scrape(
            pages=pages,
            limit_per_page=limit_per_page,
            make=make,
            model=model
        )
    
    async def scrape_by_price_range(
        self,
        min_price: int,
        max_price: int,
        pages: int = 2,
        limit_per_page: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Scrape listings filtered by price range.
        
        Args:
            min_price: Minimum price
            max_price: Maximum price
            pages: Number of pages to scrape
            limit_per_page: Items per page
            
        Returns:
            List of vehicle listings
        """
        return await self.scrape(
            pages=pages,
            limit_per_page=limit_per_page,
            min_price=min_price,
            max_price=max_price
        )
    
    async def scrape_by_year(
        self,
        year: int,
        pages: int = 2,
        limit_per_page: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Scrape listings filtered by year.
        
        Args:
            year: Year to filter by
            pages: Number of pages to scrape
            limit_per_page: Items per page
            
        Returns:
            List of vehicle listings
        """
        return await self.scrape(
            pages=pages,
            limit_per_page=limit_per_page,
            year=year
        )
