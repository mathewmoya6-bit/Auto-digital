from abc import ABC, abstractmethod
from datetime import datetime


class BaseScraper(ABC):
    """
    Base class for every marketplace scraper.
    """

    def __init__(self, source):
        self.source = source

    @abstractmethod
    def scrape(self):
        pass

    def normalize_listing(self, listing):
        """
        Convert marketplace data into Auto-D format.
        """

        return {
            "source": self.source,
            "listing_id": listing.get("listing_id"),
            "url": listing.get("url"),
            "make": listing.get("make"),
            "model": listing.get("model"),
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
            "scraped_at": datetime.utcnow()
        }
