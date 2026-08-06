# app/modules/scraper/base_scraper.py

import asyncio
import logging
import random
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,"
        "application/xhtml+xml,"
        "application/xml;q=0.9,"
        "*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


class BaseScraper(ABC):
    """
    Base class for marketplace scrapers.

    Responsibilities:
        • HTTP requests
        • Shared parsing helpers
        • URL utilities

    The worker owns:
        • retries
        • scraper lifecycle
        • metrics
        • database persistence
        • error handling
    """

    REQUEST_TIMEOUT = 30
    REQUEST_DELAY = (0.5, 1.2)

    def __init__(
        self,
        source_name: str,
        base_url: str,
    ):
        self.source_name = source_name
        self.base_url = base_url.rstrip("/")

        self.client = httpx.AsyncClient(
            headers=DEFAULT_HEADERS.copy(),
            timeout=httpx.Timeout(self.REQUEST_TIMEOUT),
            follow_redirects=True,
        )

    # ==========================================================
    # ENTRY POINT
    # ==========================================================

    async def run(
        self,
        pages: int = 3,
        limit_per_page: int = 20,
    ) -> Dict[str, Any]:
        """
        Execute scraper.

        Worker handles failures and metrics.
        """
        logger.info("[%s] Starting scraper", self.source_name)

        result = await self.scrape(
            pages=pages,
            limit_per_page=limit_per_page,
        )

        logger.info("[%s] Finished scraper", self.source_name)

        return result

    @abstractmethod
    async def scrape(
        self,
        pages: int = 3,
        limit_per_page: int = 20,
    ) -> Dict[str, Any]:
        """
        Implement scraping logic.

        Expected return:

        {
            "listings": [...],
            "listings_found": int,
            "listings_saved": int,
        }
        """
        raise NotImplementedError

    # ==========================================================
    # HTTP
    # ==========================================================

    async def fetch(
        self,
        url: str,
        params: Optional[dict] = None,
    ) -> httpx.Response:
        """
        Perform HTTP GET request.
        """
        response = await self.client.get(
            url,
            params=params,
        )

        response.raise_for_status()

        await asyncio.sleep(
            random.uniform(*self.REQUEST_DELAY)
        )

        return response

    async def fetch_soup(
        self,
        url: str,
        params: Optional[dict] = None,
    ) -> BeautifulSoup:
        """
        Fetch page and return BeautifulSoup.
        """
        response = await self.fetch(
            url=url,
            params=params,
        )

        return BeautifulSoup(
            response.text,
            "html.parser",
        )

    async def close(self):
        """
        Close HTTP client.
        """
        await self.client.aclose()

    # ==========================================================
    # URLS
    # ==========================================================

    def absolute_url(self, url: str) -> str:
        """
        Convert relative URL to absolute.
        """
        return urljoin(self.base_url, url)

    # ==========================================================
    # TEXT
    # ==========================================================

    @staticmethod
    def clean_text(
        value: Optional[str],
    ) -> str:
        if not value:
            return ""

        return " ".join(value.split()).strip()

    # ==========================================================
    # NUMBERS
    # ==========================================================

    @staticmethod
    def parse_int(
        value: Optional[str],
    ) -> Optional[int]:
        if not value:
            return None

        digits = re.sub(r"[^\d]", "", str(value))

        if not digits:
            return None

        try:
            return int(digits)
        except ValueError:
            return None

    @staticmethod
    def parse_float(
        value: Optional[str],
    ) -> Optional[float]:
        if not value:
            return None

        digits = re.sub(r"[^\d.]", "", str(value))

        if not digits:
            return None

        try:
            return float(digits)
        except ValueError:
            return None

    # ==========================================================
    # VEHICLE HELPERS - UPDATED
    # ==========================================================

    @staticmethod
    def parse_price(
        text: Optional[str],
    ) -> Optional[int]:
        """
        Parse price from text.
        
        Handles:
        - KES 1,250,000
        - KSh 1,250,000
        - 1,250,000
        - 1250000
        - KES 1.25M
        """
        if not text:
            return None

        # Remove currency symbols and common separators
        cleaned = (
            text.replace("KES", "")
            .replace("KSh", "")
            .replace("Ksh", "")
            .replace("KSH", "")
            .replace("ksh", "")
            .replace("ksh", "")
            .replace(",", "")
            .replace(" ", "")
            .strip()
        )

        # Handle "M" (millions) format: 1.25M → 1250000
        if "M" in cleaned.upper():
            cleaned = cleaned.upper().replace("M", "")
            try:
                return int(float(cleaned) * 1000000)
            except (ValueError, TypeError):
                pass

        # Handle "K" (thousands) format: 1.25K → 1250
        if "K" in cleaned.upper():
            cleaned = cleaned.upper().replace("K", "")
            try:
                return int(float(cleaned) * 1000)
            except (ValueError, TypeError):
                pass

        # Extract the first number found
        match = re.search(
            r"\d+(?:\.\d+)?",
            cleaned,
        )

        if not match:
            return None

        try:
            return int(float(match.group()))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def parse_year(
        text: Optional[str],
    ) -> Optional[int]:
        """
        Parse year from text.
        
        Handles:
        - 2024
        - 2024/2025
        - Model Year 2024
        """
        if not text:
            return None

        match = re.search(
            r"\b(19\d{2}|20\d{2})\b",
            text,
        )

        return int(match.group()) if match else None

    @staticmethod
    def parse_mileage(
        text: Optional[str],
    ) -> Optional[int]:
        """
        Parse mileage from text.
        
        Handles:
        - 50,000 km
        - 50000km
        - 50,000 KM
        - 50000 KM
        - 50,000 kms
        """
        if not text:
            return None

        # Remove common patterns
        cleaned = re.sub(
            r"(km|kms|kilometers?|miles)",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # Remove commas and spaces
        cleaned = cleaned.replace(",", "").replace(" ", "")

        # Extract number
        match = re.search(
            r"(\d+)",
            cleaned,
        )

        if not match:
            return None

        try:
            return int(match.group(1))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def parse_engine_size(
        text: Optional[str],
    ) -> Optional[float]:
        """
        Parse engine size from text.
        
        Handles:
        - 1.5L → 1.5
        - 1500cc → 1.5
        - 2.0 litre → 2.0
        - 1800 cc → 1.8
        """
        if not text:
            return None

        # Remove common patterns
        cleaned = re.sub(
            r"(L|litre|liter|litres|liters|cc)",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # Remove spaces and commas
        cleaned = cleaned.replace(",", "").replace(" ", "")

        # Try to match decimal format (X.X)
        match = re.search(
            r"(\d+\.\d+)",
            cleaned,
        )

        if match:
            try:
                return float(match.group(1))
            except (ValueError, TypeError):
                pass

        # Try to match integer format (XXXX)
        match = re.search(
            r"(\d{3,4})",
            cleaned,
        )

        if match:
            try:
                cc = int(match.group(1))
                # If it's 3-4 digits, assume it's in cc
                if cc >= 1000:
                    return cc / 1000.0
                else:
                    return float(cc)
            except (ValueError, TypeError):
                pass

        return None

    # ==========================================================
    # COMPATIBILITY HELPERS (ADDED)
    # ==========================================================

    async def _fetch_page(
        self,
        url: str,
        params: Optional[dict] = None,
    ) -> Optional[BeautifulSoup]:
        """
        Compatibility wrapper used by all marketplace scrapers.
        Returns BeautifulSoup or None on failure.
        """
        try:
            return await self.fetch_soup(
                url=url,
                params=params,
            )
        except Exception as e:
            logger.debug(
                "[%s] Failed to fetch %s (%s)",
                self.source_name,
                url,
                e,
            )
            return None

    async def _rate_limit(self):
        """
        Apply rate limiting between requests.
        """
        await asyncio.sleep(random.uniform(*self.REQUEST_DELAY))

    def _clean_text(self, value: Optional[str]) -> str:
        """Clean text (compatibility wrapper)."""
        return self.clean_text(value)

    def _absolute_url(self, url: str) -> str:
        """Make URL absolute (compatibility wrapper)."""
        return self.absolute_url(url)

    def _parse_price(self, text: Optional[str]) -> Optional[int]:
        """Parse price (compatibility wrapper)."""
        return self.parse_price(text)

    def _parse_year(self, text: Optional[str]) -> Optional[int]:
        """Parse year (compatibility wrapper)."""
        return self.parse_year(text)

    def _parse_mileage(self, text: Optional[str]) -> Optional[int]:
        """Parse mileage (compatibility wrapper)."""
        return self.parse_mileage(text)

    def _parse_engine_size(self, text: Optional[str]) -> Optional[float]:
        """Parse engine size (compatibility wrapper)."""
        return self.parse_engine_size(text)

    # ==========================================================
    # CONTEXT MANAGER SUPPORT (RECOMMENDED)
    # ==========================================================

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup."""
        await self.close()
