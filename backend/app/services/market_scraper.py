# app/services/market_scraper.py
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple
import re
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
import json
from app.services.supabase_service import SupabaseService
from app.models.price import PriceSource, VehicleCondition
from app.config import settings

logger = logging.getLogger(__name__)

class MarketScraper:
    def __init__(self, supabase_service: SupabaseService):
        self.supabase = supabase_service
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache'
        }
        self.kenyan_counties = [
            'Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Eldoret', 
            'Kiambu', 'Kajiado', 'Machakos', 'Thika', 'Malindi'
        ]

    async def scrape_all_sources(self) -> int:
        """Scrape prices from all sources"""
        total_updated = 0
        
        # Priority: Jiji > Cheki > Autochek
        sources = [
            self.scrape_jiji,
            self.scrape_cheki,
            self.scrape_autochek,
            self.scrape_beepbeep,
            self.scrape_pigiame
        ]
        
        for source in sources:
            try:
                prices = await source()
                if prices:
                    saved = await self._save_prices(prices, source.__name__)
                    total_updated += saved
                    logger.info(f"✅ {source.__name__}: saved {saved} prices")
                else:
                    logger.info(f"ℹ️ {source.__name__}: no prices found")
            except Exception as e:
                logger.error(f"❌ {source.__name__} failed: {e}")
        
        return total_updated

    # ============================================================
    # JIJI KENYA - Largest volume of private vehicle listings
    # ============================================================
    async def scrape_jiji(self) -> List[Dict]:
        """Scrape prices from Jiji Kenya - Primary source for market prices"""
        prices = []
        
        # Jiji Kenya car categories
        categories = [
            ("cars", "https://jiji.co.ke/cars"),
            ("suvs", "https://jiji.co.ke/suvs"),
            ("trucks", "https://jiji.co.ke/trucks"),
            ("vans", "https://jiji.co.ke/vans"),
            ("buses", "https://jiji.co.ke/buses")
        ]
        
        # County-specific search URLs
        counties = ['nairobi', 'mombasa', 'kisumu', 'nakuru', 'eldoret', 'kiambu']
        
        async with aiohttp.ClientSession() as session:
            for category_name, base_url in categories:
                # Scrape main category
                for page in range(1, settings.MAX_SCRAPE_PAGES + 1):
                    try:
                        url = f"{base_url}?page={page}"
                        logger.info(f"Scraping Jiji {category_name}: {url}")
                        
                        async with session.get(url, headers=self.headers, timeout=30) as response:
                            if response.status != 200:
                                logger.warning(f"Jiji {category_name} page {page} returned {response.status}")
                                continue
                            
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Jiji specific selectors
                            listings = soup.select('.b-list-advert, .b-advert, .b-list-item, .advert-item')
                            
                            if not listings:
                                listings = soup.select('[class*="advert"], [class*="listing"], [class*="item"]')
                            
                            for listing in listings:
                                price_data = self._parse_jiji_listing(listing, category_name)
                                if price_data:
                                    prices.append(price_data)
                            
                            # Check if there's a next page
                            next_page = soup.select_one('a[rel="next"], .pagination .next, .pagination .next-page')
                            if not next_page:
                                break
                            
                            await asyncio.sleep(2)
                            
                    except Exception as e:
                        logger.error(f"Jiji error {category_name} page {page}: {e}")
                
                # Scrape county-specific listings
                for county in counties:
                    for page in range(1, 3):  # Limit county searches to 2 pages
                        try:
                            url = f"{base_url}?page={page}&location={county}"
                            logger.info(f"Scraping Jiji {category_name} in {county}: {url}")
                            
                            async with session.get(url, headers=self.headers, timeout=30) as response:
                                if response.status != 200:
                                    continue
                                
                                html = await response.text()
                                soup = BeautifulSoup(html, 'html.parser')
                                
                                listings = soup.select('.b-list-advert, .b-advert, .b-list-item')
                                
                                for listing in listings:
                                    price_data = self._parse_jiji_listing(listing, category_name, county)
                                    if price_data:
                                        prices.append(price_data)
                                
                                await asyncio.sleep(2)
                                
                        except Exception as e:
                            logger.error(f"Jiji {category_name} {county} error: {e}")
        
        return prices

    def _parse_jiji_listing(self, listing, category: str = 'cars', county: str = None) -> Optional[Dict]:
        """Parse a Jiji listing"""
        try:
            # Extract title
            title_elem = listing.select_one('.b-advert-title, .title, h3, .advert-title, .item-title')
            title = title_elem.text.strip() if title_elem else ''
            
            if not title:
                return None
            
            # Extract price - Jiji specific
            price_elem = listing.select_one('.b-advert-price, .price, .amount, .advert-price, .item-price')
            if not price_elem:
                return None
            
            price_text = price_elem.text.strip()
            price = self._extract_price(price_text)
            if not price:
                # Try to find price in attributes
                price_attr = listing.get('data-price')
                if price_attr:
                    price = self._extract_price(price_attr)
                if not price:
                    return None
            
            # Extract year
            year = self._extract_year_jiji(listing, title)
            
            # Extract mileage
            mileage = self._extract_mileage_jiji(listing)
            
            # Extract location
            location = self._extract_location_jiji(listing, county)
            
            # Extract transmission
            transmission = self._extract_transmission_jiji(listing)
            
            # Extract fuel type
            fuel_type = self._extract_fuel_type_jiji(listing)
            
            # Extract engine size
            engine_size = self._extract_engine_size_jiji(listing)
            
            # Determine condition
            condition = self._determine_condition_jiji(listing)
            
            # Extract images count (indicates listing quality)
            images = listing.select('img')
            image_count = len(images)
            
            # Extract listing age
            age_text = listing.select_one('.b-advert-date, .date, .posted-time, .listing-date')
            listing_age = age_text.text.strip() if age_text else None
            
            return {
                'title': title,
                'price_kes': price,
                'year': year,
                'mileage_km': mileage,
                'condition': condition.value,
                'location': location,
                'transmission': transmission,
                'fuel_type': fuel_type,
                'engine_size_cc': engine_size,
                'image_count': image_count,
                'listing_age': listing_age,
                'category': category,
                'source': 'jiji.co.ke',
                'source_type': 'private' if 'private' in str(listing).lower() else 'dealer',
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing Jiji listing: {e}")
            return None

    def _extract_year_jiji(self, element, title: str = '') -> Optional[int]:
        """Extract year from Jiji listing"""
        # Jiji specific year selectors
        year_selectors = ['.b-advert-attributes .year', '.attribute-year', '.year', 
                         '.spec-year', '[class*="year"]', '[data-year]']
        
        for selector in year_selectors:
            year_elem = element.select_one(selector)
            if year_elem:
                year_text = year_elem.text.strip()
                year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
                if year_match:
                    year = int(year_match.group())
                    if 1980 <= year <= datetime.now().year + 1:
                        return year
            
            # Check for data attribute
            if element.get('data-year'):
                year = int(element.get('data-year'))
                if 1980 <= year <= datetime.now().year + 1:
                    return year
        
        # Try to find year in the title
        if title:
            year_match = re.search(r'\b(19|20)\d{2}\b', title)
            if year_match:
                year = int(year_match.group())
                if 1980 <= year <= datetime.now().year + 1:
                    return year
        
        # Try full text
        full_text = element.get_text()
        year_match = re.search(r'(19|20)\d{2}', full_text)
        if year_match:
            year = int(year_match.group())
            if 1980 <= year <= datetime.now().year + 1:
                return year
        
        return None

    def _extract_mileage_jiji(self, element) -> Optional[int]:
        """Extract mileage from Jiji listing"""
        mileage_selectors = ['.b-advert-attributes .mileage', '.attribute-mileage', '.mileage', 
                            '.spec-mileage', '[class*="mileage"]', '[data-mileage]']
        
        for selector in mileage_selectors:
            mileage_elem = element.select_one(selector)
            if mileage_elem:
                mileage_text = mileage_elem.text.strip()
                mileage_match = re.search(r'[\d,]+', mileage_text)
                if mileage_match:
                    mileage = int(mileage_match.group().replace(',', ''))
                    if 0 < mileage < 1000000:
                        return mileage
            
            # Check for data attribute
            if element.get('data-mileage'):
                mileage = int(element.get('data-mileage'))
                if 0 < mileage < 1000000:
                    return mileage
        
        # Try to find in full text
        full_text = element.get_text()
        mileage_patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*(?:km|KM|kms|Kms)',
            r'(?:km|KM|kms|Kms)\s*(\d{1,3}(?:,\d{3})*)'
        ]
        
        for pattern in mileage_patterns:
            match = re.search(pattern, full_text)
            if match:
                mileage = int(match.group(1).replace(',', ''))
                if 0 < mileage < 1000000:
                    return mileage
        
        return None

    def _extract_location_jiji(self, element, county: str = None) -> Optional[str]:
        """Extract location from Jiji listing"""
        if county:
            return county.title()
        
        location_selectors = ['.b-advert-location', '.location', '.area', '.city', '.region', 
                             '[class*="location"]', '[data-location]']
        
        for selector in location_selectors:
            loc_elem = element.select_one(selector)
            if loc_elem:
                location = loc_elem.text.strip()
                for kenyan_county in self.kenyan_counties:
                    if kenyan_county.lower() in location.lower():
                        return kenyan_county
                return location
        
        return None

    def _extract_transmission_jiji(self, element) -> Optional[str]:
        """Extract transmission from Jiji listing"""
        trans_selectors = ['.b-advert-attributes .transmission', '.attribute-transmission', 
                          '.transmission', '[class*="transmission"]', '[data-transmission]']
        
        for selector in trans_selectors:
            trans_elem = element.select_one(selector)
            if trans_elem:
                trans_text = trans_elem.text.strip().lower()
                if 'automatic' in trans_text or 'auto' in trans_text:
                    return 'Automatic'
                elif 'manual' in trans_text:
                    return 'Manual'
                elif 'cvt' in trans_text:
                    return 'CVT'
        
        # Try full text
        full_text = element.get_text().lower()
        if 'automatic' in full_text or 'auto' in full_text:
            return 'Automatic'
        elif 'manual' in full_text:
            return 'Manual'
        elif 'cvt' in full_text:
            return 'CVT'
        
        return None

    def _extract_fuel_type_jiji(self, element) -> Optional[str]:
        """Extract fuel type from Jiji listing"""
        fuel_selectors = ['.b-advert-attributes .fuel', '.attribute-fuel', '.fuel', 
                         '[class*="fuel"]', '[data-fuel]']
        
        for selector in fuel_selectors:
            fuel_elem = element.select_one(selector)
            if fuel_elem:
                fuel_text = fuel_elem.text.strip().lower()
                if 'petrol' in fuel_text or 'gasoline' in fuel_text:
                    return 'Petrol'
                elif 'diesel' in fuel_text:
                    return 'Diesel'
                elif 'electric' in fuel_text or 'ev' in fuel_text:
                    return 'Electric'
                elif 'hybrid' in fuel_text:
                    return 'Hybrid'
        
        # Try full text
        full_text = element.get_text().lower()
        if 'petrol' in full_text or 'gasoline' in full_text:
            return 'Petrol'
        elif 'diesel' in full_text:
            return 'Diesel'
        elif 'electric' in full_text or 'ev' in full_text:
            return 'Electric'
        elif 'hybrid' in full_text:
            return 'Hybrid'
        
        return None

    def _extract_engine_size_jiji(self, element) -> Optional[int]:
        """Extract engine size from Jiji listing"""
        engine_selectors = ['.b-advert-attributes .engine', '.attribute-engine', '.engine', 
                           '.cc', '[class*="engine"]', '[class*="cc"]']
        
        for selector in engine_selectors:
            engine_elem = element.select_one(selector)
            if engine_elem:
                engine_text = engine_elem.text.strip()
                # Look for patterns like "2000cc", "2.0L"
                match = re.search(r'(\d+)\s*(?:cc|CC)', engine_text)
                if match:
                    return int(match.group(1))
                match = re.search(r'(\d+\.\d+)\s*(?:L|l)', engine_text)
                if match:
                    return int(float(match.group(1)) * 1000)
        
        return None

    def _determine_condition_jiji(self, element) -> VehicleCondition:
        """Determine vehicle condition from Jiji listing"""
        condition_selectors = ['.b-advert-attributes .condition', '.attribute-condition', 
                              '.condition', '[class*="condition"]']
        
        for selector in condition_selectors:
            cond_elem = element.select_one(selector)
            if cond_elem:
                cond_text = cond_elem.text.strip().lower()
                if 'new' in cond_text:
                    return VehicleCondition.NEW
                elif 'excellent' in cond_text or 'mint' in cond_text:
                    return VehicleCondition.EXCELLENT
                elif 'good' in cond_text:
                    return VehicleCondition.GOOD
                elif 'fair' in cond_text:
                    return VehicleCondition.FAIR
                elif 'poor' in cond_text or 'bad' in cond_text:
                    return VehicleCondition.POOR
        
        # Try full text
        full_text = element.get_text().lower()
        if 'new' in full_text:
            return VehicleCondition.NEW
        elif 'excellent' in full_text or 'mint' in full_text:
            return VehicleCondition.EXCELLENT
        elif 'good' in full_text:
            return VehicleCondition.GOOD
        elif 'fair' in full_text:
            return VehicleCondition.FAIR
        
        return VehicleCondition.GOOD

    # ============================================================
    # CHEKI KENYA - Dealer-focused listings with detailed specs
    # ============================================================
    async def scrape_cheki(self) -> List[Dict]:
        """Scrape prices from Cheki Kenya - Dealer pricing"""
        prices = []
        base_urls = [
            "https://www.cheki.co.ke/cars",
            "https://www.cheki.co.ke/used-cars",
            "https://www.cheki.co.ke/suvs",
            "https://www.cheki.co.ke/trucks",
            "https://www.cheki.co.ke/vans"
        ]
        
        async with aiohttp.ClientSession() as session:
            for base_url in base_urls:
                for page in range(1, settings.MAX_SCRAPE_PAGES + 1):
                    try:
                        url = f"{base_url}?page={page}"
                        logger.info(f"Scraping Cheki: {url}")
                        
                        async with session.get(url, headers=self.headers, timeout=30) as response:
                            if response.status != 200:
                                continue
                            
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Cheki specific selectors
                            listings = soup.select('.vehicle-card, .listing-item, .ad-item, .car-item, .search-result')
                            
                            for listing in listings:
                                price_data = self._parse_cheki_listing(listing)
                                if price_data:
                                    prices.append(price_data)
                            
                            if not listings:
                                break
                            
                            await asyncio.sleep(2)
                            
                    except Exception as e:
                        logger.error(f"Cheki error page {page}: {e}")
        
        return prices

    def _parse_cheki_listing(self, listing) -> Optional[Dict]:
        """Parse a Cheki listing"""
        try:
            title_elem = listing.select_one('.title, .heading, .car-name, h3, .vehicle-title')
            title = title_elem.text.strip() if title_elem else ''
            
            if not title:
                return None
            
            price_elem = listing.select_one('.price, .amount, .cost, .price-tag, .listing-price')
            if not price_elem:
                return None
            
            price_text = price_elem.text.strip()
            price = self._extract_price(price_text)
            if not price:
                return None
            
            year = self._extract_year(listing, title)
            mileage = self._extract_mileage(listing)
            location = self._extract_location(listing)
            condition = self._determine_condition(listing)
            transmission = self._extract_transmission(listing)
            fuel_type = self._extract_fuel_type(listing)
            engine_size = self._extract_engine_size(listing)
            
            return {
                'title': title,
                'price_kes': price,
                'year': year,
                'mileage_km': mileage,
                'condition': condition.value,
                'location': location,
                'transmission': transmission,
                'fuel_type': fuel_type,
                'engine_size_cc': engine_size,
                'source': 'cheki.co.ke',
                'source_type': 'dealer',
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing Cheki listing: {e}")
            return None

    # ============================================================
    # AUTOCHEK KENYA - Quality-inspected vehicles (Premium market)
    # ============================================================
    async def scrape_autochek(self) -> List[Dict]:
        """Scrape prices from Autochek Kenya - Premium market pricing"""
        prices = []
        base_urls = [
            "https://www.autochek.co.ke/",
            "https://www.autochek.co.ke/cars-for-sale",
            "https://www.autochek.co.ke/used-cars",
            "https://www.autochek.co.ke/vehicles",
            "https://www.autochek.co.ke/listings"
        ]
        
        async with aiohttp.ClientSession() as session:
            for base_url in base_urls:
                for page in range(1, settings.MAX_SCRAPE_PAGES + 1):
                    try:
                        if "?" in base_url:
                            url = f"{base_url}&page={page}"
                        else:
                            url = f"{base_url}?page={page}"
                        
                        logger.info(f"Scraping Autochek: {url}")
                        
                        async with session.get(url, headers=self.headers, timeout=30) as response:
                            if response.status != 200:
                                logger.warning(f"Autochek page {page} returned {response.status}")
                                continue
                            
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Autochek specific selectors
                            listings = soup.select('.listing, .car-card, .vehicle-item, .ad-listing, .result-item, .search-result')
                            
                            if not listings:
                                listings = soup.select('[class*="car"], [class*="vehicle"], [class*="listing"]')
                            
                            if not listings:
                                listings = soup.select('article')
                            
                            for listing in listings:
                                price_data = self._parse_autochek_listing(listing)
                                if price_data:
                                    prices.append(price_data)
                            
                            # Check for next page
                            next_page = soup.select_one('a.next, a[rel="next"], .pagination .next')
                            if not next_page:
                                break
                            
                            await asyncio.sleep(2)
                            
                    except Exception as e:
                        logger.error(f"Autochek error page {page}: {e}")
        
        return prices

    def _parse_autochek_listing(self, listing) -> Optional[Dict]:
        """Parse an Autochek listing"""
        try:
            title_elem = listing.select_one('.title, .car-title, .vehicle-title, h3, .heading, .name, .listing-title')
            title = title_elem.text.strip() if title_elem else ''
            
            if not title:
                img = listing.select_one('img')
                if img and img.get('alt'):
                    title = img.get('alt').strip()
            
            if not title:
                return None
            
            price_elem = listing.select_one('.price, .cost, .amount, .listing-price, .price-tag, .vehicle-price')
            if not price_elem:
                price_text = listing.get_text()
                price_matches = re.findall(r'[KShs|Ksh|KES|KSh]\s*[\d,]+', price_text, re.IGNORECASE)
                if price_matches:
                    price_text = price_matches[0]
                else:
                    return None
            
            price_text = price_elem.text.strip() if price_elem else price_text
            price = self._extract_price(price_text)
            if not price:
                full_text = listing.get_text()
                price = self._extract_price(full_text)
                if not price:
                    return None
            
            year = self._extract_year(listing, title)
            mileage = self._extract_mileage(listing)
            location = self._extract_location(listing)
            condition = self._determine_condition(listing)
            transmission = self._extract_transmission(listing)
            fuel_type = self._extract_fuel_type(listing)
            engine_size = self._extract_engine_size(listing)
            
            # Autochek specific: check for certified/inspected badge
            inspected = bool(listing.select_one('.certified, .inspected, .quality-check, .verified'))
            
            return {
                'title': title,
                'price_kes': price,
                'year': year,
                'mileage_km': mileage,
                'condition': condition.value,
                'location': location,
                'transmission': transmission,
                'fuel_type': fuel_type,
                'engine_size_cc': engine_size,
                'inspected': inspected,
                'source': 'autochek.co.ke',
                'source_type': 'dealer',
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing Autochek listing: {e}")
            return None

    # ============================================================
    # Helper Methods
    # ============================================================
    def _extract_price(self, text: str) -> Optional[int]:
        """Extract price from text"""
        # Remove commas and currency symbols
        cleaned = re.sub(r'[^0-9,]', '', text)
        cleaned = cleaned.replace(',', '')
        if cleaned and cleaned.isdigit():
            return int(cleaned)
        return None

    def _extract_year(self, element, title: str = '') -> Optional[int]:
        """Extract year from element"""
        year_selectors = ['.year', '.reg-year', '.manufacture-year', '.reg-date', '.year-field', 
                         '.vehicle-year', '.car-year', '[class*="year"]', '[data-year]']
        
        for selector in year_selectors:
            year_elem = element.select_one(selector)
            if year_elem:
                year_text = year_elem.text.strip()
                year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
                if year_match:
                    year = int(year_match.group())
                    if 1980 <= year <= datetime.now().year + 1:
                        return year
            
            # Check for data attribute
            if element.get('data-year'):
                year = int(element.get('data-year'))
                if 1980 <= year <= datetime.now().year + 1:
                    return year
        
        if title:
            year_match = re.search(r'\b(19|20)\d{2}\b', title)
            if year_match:
                year = int(year_match.group())
                if 1980 <= year <= datetime.now().year + 1:
                    return year
        
        full_text = element.get_text()
        year_match = re.search(r'(19|20)\d{2}', full_text)
        if year_match:
            year = int(year_match.group())
            if 1980 <= year <= datetime.now().year + 1:
                return year
        
        return None

    def _extract_mileage(self, element) -> Optional[int]:
        """Extract mileage from element"""
        mileage_selectors = ['.mileage', '.km', '.odometer', '.distance', '.km-field', 
                            '.vehicle-mileage', '.car-mileage', '[class*="mileage"]', '[data-mileage]']
        
        for selector in mileage_selectors:
            mileage_elem = element.select_one(selector)
            if mileage_elem:
                mileage_text = mileage_elem.text.strip()
                mileage_match = re.search(r'[\d,]+', mileage_text)
                if mileage_match:
                    mileage = int(mileage_match.group().replace(',', ''))
                    if 0 < mileage < 1000000:
                        return mileage
            
            if element.get('data-mileage'):
                mileage = int(element.get('data-mileage'))
                if 0 < mileage < 1000000:
                    return mileage
        
        full_text = element.get_text()
        mileage_patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*(?:km|KM|kms|Kms)',
            r'(?:km|KM|kms|Kms)\s*(\d{1,3}(?:,\d{3})*)'
        ]
        
        for pattern in mileage_patterns:
            match = re.search(pattern, full_text)
            if match:
                mileage = int(match.group(1).replace(',', ''))
                if 0 < mileage < 1000000:
                    return mileage
        
        return None

    def _extract_location(self, element) -> Optional[str]:
        """Extract location from element"""
        location_selectors = ['.location', '.area', '.city', '.region', '.county', 
                             '[class*="location"]', '[data-location]']
        
        for selector in location_selectors:
            loc_elem = element.select_one(selector)
            if loc_elem:
                location = loc_elem.text.strip()
                for county in self.kenyan_counties:
                    if county.lower() in location.lower():
                        return county
                return location
        
        return None

    def _extract_transmission(self, element) -> Optional[str]:
        """Extract transmission type"""
        trans_selectors = ['.transmission', '.gear', '.gearbox', '[class*="transmission"]', 
                          '.spec-transmission', '[data-transmission]']
        
        for selector in trans_selectors:
            trans_elem = element.select_one(selector)
            if trans_elem:
                trans_text = trans_elem.text.strip().lower()
                if 'automatic' in trans_text or 'auto' in trans_text:
                    return 'Automatic'
                elif 'manual' in trans_text:
                    return 'Manual'
                elif 'cvt' in trans_text:
                    return 'CVT'
        
        full_text = element.get_text().lower()
        if 'automatic' in full_text or 'auto' in full_text:
            return 'Automatic'
        elif 'manual' in full_text:
            return 'Manual'
        elif 'cvt' in full_text:
            return 'CVT'
        
        return None

    def _extract_fuel_type(self, element) -> Optional[str]:
        """Extract fuel type"""
        fuel_selectors = ['.fuel', '.fuel-type', '.engine', '[class*="fuel"]', '.spec-fuel', '[data-fuel]']
        
        for selector in fuel_selectors:
            fuel_elem = element.select_one(selector)
            if fuel_elem:
                fuel_text = fuel_elem.text.strip().lower()
                if 'petrol' in fuel_text or 'gasoline' in fuel_text:
                    return 'Petrol'
                elif 'diesel' in fuel_text:
                    return 'Diesel'
                elif 'electric' in fuel_text or 'ev' in fuel_text:
                    return 'Electric'
                elif 'hybrid' in fuel_text:
                    return 'Hybrid'
        
        full_text = element.get_text().lower()
        if 'petrol' in full_text or 'gasoline' in full_text:
            return 'Petrol'
        elif 'diesel' in full_text:
            return 'Diesel'
        elif 'electric' in full_text or 'ev' in full_text:
            return 'Electric'
        elif 'hybrid' in full_text:
            return 'Hybrid'
        
        return None

    def _extract_engine_size(self, element) -> Optional[int]:
        """Extract engine size in CC"""
        engine_selectors = ['.engine', '.engine-size', '.cc', '.spec-engine', '[class*="engine"]', '[class*="cc"]']
        
        for selector in engine_selectors:
            engine_elem = element.select_one(selector)
            if engine_elem:
                engine_text = engine_elem.text.strip()
                match = re.search(r'(\d+)\s*(?:cc|CC)', engine_text)
                if match:
                    return int(match.group(1))
                match = re.search(r'(\d+\.\d+)\s*(?:L|l)', engine_text)
                if match:
                    return int(float(match.group(1)) * 1000)
        
        return None

    def _determine_condition(self, element) -> VehicleCondition:
        """Determine vehicle condition"""
        condition_selectors = ['.condition', '.status', '.state', '[class*="condition"]']
        
        for selector in condition_selectors:
            cond_elem = element.select_one(selector)
            if cond_elem:
                cond_text = cond_elem.text.strip().lower()
                if 'excellent' in cond_text or 'mint' in cond_text:
                    return VehicleCondition.EXCELLENT
                elif 'good' in cond_text:
                    return VehicleCondition.GOOD
                elif 'fair' in cond_text:
                    return VehicleCondition.FAIR
                elif 'poor' in cond_text or 'bad' in cond_text:
                    return VehicleCondition.POOR
                elif 'new' in cond_text:
                    return VehicleCondition.NEW
        
        full_text = element.get_text().lower()
        if 'new' in full_text:
            return VehicleCondition.NEW
        elif 'excellent' in full_text or 'mint' in full_text:
            return VehicleCondition.EXCELLENT
        elif 'good' in full_text:
            return VehicleCondition.GOOD
        elif 'fair' in full_text:
            return VehicleCondition.FAIR
        
        return VehicleCondition.GOOD

    async def _save_prices(self, prices: List[Dict], source_name: str) -> int:
        """Save scraped prices to database"""
        saved_count = 0
        
        for price_data in prices:
            try:
                # Try to find matching variant
                variant = await self._find_variant(price_data['title'])
                if not variant:
                    logger.debug(f"No variant found for: {price_data['title']}")
                    continue
                
                # Prepare price data for insertion
                market_price = {
                    'variant_id': variant['id'],
                    'year': price_data.get('year', datetime.now().year),
                    'price_kes': price_data['price_kes'],
                    'source': price_data.get('source', 'market_average'),
                    'source_url': price_data.get('source_url'),
                    'condition': price_data.get('condition', 'good'),
                    'mileage_km': price_data.get('mileage_km'),
                    'recorded_at': datetime.now().isoformat(),
                    'is_active': True
                }
                
                saved = await self.supabase.save_market_price(market_price)
                if saved:
                    saved_count += 1
                    
            except Exception as e:
                logger.error(f"Error saving price for {price_data.get('title', 'unknown')}: {e}")
        
        return saved_count

    async def _find_variant(self, title: str) -> Optional[Dict]:
        """Find matching variant in database"""
        try:
            title_clean = re.sub(r'[^\w\s]', '', title).lower().strip()
            parts = title_clean.split()
            if len(parts) < 2:
                return None
            
            make = parts[0]
            
            model_attempts = []
            if len(parts) >= 3:
                model_attempts.append(' '.join(parts[1:3]))
            model_attempts.append(' '.join(parts[1:2]))
            
            for model in model_attempts:
                if len(model) < 2:
                    continue
                
                try:
                    response = self.supabase.client.table('vehicle_variants')\
                        .select('*, generation:generation_id(model:model_id(make:make_id(*)))')\
                        .ilike('name', f'%{model}%')\
                        .execute()
                    
                    if response.data and len(response.data) > 0:
                        for variant in response.data:
                            make_name = variant.get('generation', {}).get('model', {}).get('make', {}).get('name', '')
                            if make_name and make.lower() in make_name.lower():
                                return variant
                        return response.data[0]
                        
                except Exception as e:
                    logger.error(f"Error querying variant: {e}")
                    continue
            
            try:
                response = self.supabase.client.table('vehicle_variants')\
                    .select('*, generation:generation_id(model:model_id(make:make_id(*)))')\
                    .ilike('generation.model.make.name', f'%{make}%')\
                    .limit(1)\
                    .execute()
                
                if response.data and len(response.data) > 0:
                    return response.data[0]
            except Exception as e:
                logger.error(f"Error querying by make: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding variant for '{title}': {e}")
            return None

    async def scrape_beepbeep(self) -> List[Dict]:
        """Scrape prices from BeepBeep Kenya - Secondary source"""
        prices = []
        base_url = "https://www.beepbeep.co.ke/cars"
        
        async with aiohttp.ClientSession() as session:
            for page in range(1, settings.MAX_SCRAPE_PAGES + 1):
                try:
                    url = f"{base_url}?page={page}"
                    logger.info(f"Scraping BeepBeep: {url}")
                    
                    async with session.get(url, headers=self.headers, timeout=30) as response:
                        if response.status != 200:
                            continue
                        
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        listings = soup.select('.car-listing, .vehicle-item, .listing-card, .ad-card')
                        
                        for listing in listings:
                            price_data = self._parse_beepbeep_listing(listing)
                            if price_data:
                                prices.append(price_data)
                        
                        if not listings:
                            break
                        
                        await asyncio.sleep(2)
                        
                except Exception as e:
                    logger.error(f"BeepBeep error page {page}: {e}")
        
        return prices

    def _parse_beepbeep_listing(self, listing) -> Optional[Dict]:
        """Parse a BeepBeep listing"""
        try:
            title_elem = listing.select_one('.title, .car-title, h3, .name')
            title = title_elem.text.strip() if title_elem else ''
            
            if not title:
                return None
            
            price_elem = listing.select_one('.price, .cost, .amount, .listing-price')
            if not price_elem:
                return None
            
            price_text = price_elem.text.strip()
            price = self._extract_price(price_text)
            if not price:
                return None
            
            year = self._extract_year(listing, title)
            mileage = self._extract_mileage(listing)
            location = self._extract_location(listing)
            condition = self._determine_condition(listing)
            
            return {
                'title': title,
                'price_kes': price,
                'year': year,
                'mileage_km': mileage,
                'condition': condition.value,
                'location': location,
                'source': 'beepbeep.co.ke',
                'source_type': 'dealer',
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing BeepBeep listing: {e}")
            return None

    async def scrape_pigiame(self) -> List[Dict]:
        """Scrape prices from PigiaMe Kenya - Secondary source"""
        prices = []
        base_url = "https://www.pigiame.co.ke/vehicles/cars"
        
        async with aiohttp.ClientSession() as session:
            for page in range(1, settings.MAX_SCRAPE_PAGES + 1):
                try:
                    url = f"{base_url}?page={page}"
                    logger.info(f"Scraping PigiaMe: {url}")
                    
                    async with session.get(url, headers=self.headers, timeout=30) as response:
                        if response.status != 200:
                            continue
                        
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        listings = soup.select('.listing, .ad-item, .card, .result-item')
                        
                        for listing in listings:
                            price_data = self._parse_pigiame_listing(listing)
                            if price_data:
                                prices.append(price_data)
                        
                        if not listings:
                            break
                        
                        await asyncio.sleep(2)
                        
                except Exception as e:
                    logger.error(f"PigiaMe error page {page}: {e}")
        
        return prices

    def _parse_pigiame_listing(self, listing) -> Optional[Dict]:
        """Parse a PigiaMe listing"""
        try:
            title_elem = listing.select_one('.title, .ad-title, h3, .heading')
            title = title_elem.text.strip() if title_elem else ''
            
            if not title:
                return None
            
            price_elem = listing.select_one('.price, .amount, .cost')
            if not price_elem:
                return None
            
            price_text = price_elem.text.strip()
            price = self._extract_price(price_text)
            if not price:
                return None
            
            year = self._extract_year(listing, title)
            mileage = self._extract_mileage(listing)
            location = self._extract_location(listing)
            condition = self._determine_condition(listing)
            
            return {
                'title': title,
                'price_kes': price,
                'year': year,
                'mileage_km': mileage,
                'condition': condition.value,
                'location': location,
                'source': 'pigiame.co.ke',
                'source_type': 'private',
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing PigiaMe listing: {e}")
            return None
