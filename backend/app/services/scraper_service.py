    # ─── Mock Scraper ───────────────────────────────────────────────
    
    async def _mock_scrape(
        self,
        source: str,
        make: Optional[str] = None,
        model: Optional[str] = None,
        max_results: int = 100,
        start_time: Optional[float] = None
    ) -> Dict:
        """Generate mock listings for testing."""
        if not start_time:
            start_time = time.time()
        
        # Simulate scraping delay
        await asyncio.sleep(random.uniform(0.5, 2))
        
        # Generate mock data
        listings = self._generate_mock_listings(
            source=source,
            make=make,
            model=model,
            count=min(random.randint(5, max_results), 50)
        )
        
        # Save to database
        saved_count = await self._save_listings(listings)
        
        return {
            "source": source,
            "success": True,
            "items_scraped": len(listings),
            "saved_count": saved_count,
            "duration_seconds": round(time.time() - start_time, 2),
            "mock": True
        }
    
    def _generate_mock_listings(
        self,
        source: str,
        make: Optional[str] = None,
        model: Optional[str] = None,
        count: int = 20
    ) -> List[Dict]:
        """Generate mock listings for testing."""
        makes = [
            "Toyota", "Honda", "Nissan", "Mazda", "Subaru", 
            "Mercedes", "BMW", "Audi", "Ford", "Volkswagen",
            "Lexus", "Land Rover", "Range Rover", "Porsche", "Volvo"
        ]
        
        models_by_make = {
            "Toyota": ["Corolla", "Camry", "RAV4", "Hilux", "Land Cruiser", "Prado", "Avalon"],
            "Honda": ["Civic", "Accord", "CR-V", "HR-V", "Fit", "Odyssey"],
            "Nissan": ["X-Trail", "Qashqai", "Juke", "Patrol", "Navara", "Leaf"],
            "Mazda": ["CX-5", "CX-3", "CX-9", "Mazda3", "Mazda6", "MX-5"],
            "Subaru": ["Forester", "Outback", "Impreza", "Legacy", "XV", "Ascent"],
            "Mercedes": ["E-Class", "C-Class", "S-Class", "GLE", "GLC", "G-Wagon"],
            "BMW": ["3 Series", "5 Series", "7 Series", "X3", "X5", "X7"],
            "Audi": ["A4", "A6", "A8", "Q5", "Q7", "Q8"],
            "Ford": ["Focus", "Fiesta", "Mustang", "Explorer", "Ranger", "Edge"],
            "Volkswagen": ["Golf", "Passat", "Tiguan", "Atlas", "Polo", "Jetta"]
        }
        
        years = list(range(2010, 2025))
        conditions = ["excellent", "very_good", "good", "fair"]
        fuel_types = ["petrol", "diesel", "electric", "hybrid"]
        transmissions = ["automatic", "manual"]
        locations = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Thika", "Kiambu", "Kajiado"]
        
        listings = []
        for i in range(count):
            selected_make = make or random.choice(makes)
            selected_models = models_by_make.get(selected_make, ["Model"])
            selected_model = model or random.choice(selected_models)
            
            year = random.choice(years)
            price = random.randint(500000, 8000000)
            mileage = random.randint(10000, 150000)
            
            listings.append({
                "source": source,
                "make": selected_make,
                "model": selected_model,
                "year": year,
                "price": price,
                "mileage": mileage,
                "condition": random.choice(conditions),
                "fuel_type": random.choice(fuel_types),
                "transmission": random.choice(transmissions),
                "location": random.choice(locations),
                "description": f"{selected_make} {selected_model} for sale in Kenya",
                "listing_url": f"https://{source}.com/listing/{i}",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
        
        return listings
    
    # ─── Logging ──────────────────────────────────────────────────
    
    def add_scraper_log(self, message: str, level: str = "info"):
        """Add entry to scraper log."""
        try:
            supabase.table("scraper_logs").insert({
                "message": message,
                "level": level,
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"❌ Error adding scraper log: {e}")
    
    # ─── Scraper Endpoints ──────────────────────────────────────
    
    async def scrape_autochek(self, task_id: Optional[str] = None, **kwargs):
        """Scrape Autochek."""
        return await self._scrape_autochek(**kwargs)
    
    async def scrape_jiji(self, task_id: Optional[str] = None, **kwargs):
        """Scrape Jiji."""
        return await self._scrape_jiji(**kwargs)
    
    async def scrape_carapi(self, task_id: Optional[str] = None, **kwargs):
        """Scrape CarAPI."""
        return await self._scrape_carapi(**kwargs)


# ─── Singleton ─────────────────────────────────────────────────────

_scraper_service: Optional[ScraperService] = None


def get_scraper_service() -> ScraperService:
    """Get or create ScraperService singleton."""
    global _scraper_service
    if _scraper_service is None:
        _scraper_service = ScraperService()
    return _scraper_service


# ─── Export ─────────────────────────────────────────────────────

__all__ = [
    "ScraperService",
    "get_scraper_service",
    "ScraperError",
    "SourceUnavailableError",
    "RateLimitError",
    "ParseError",
]
