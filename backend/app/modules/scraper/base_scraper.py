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
    # VEHICLE HELPERS
    # ==========================================================

    @staticmethod
    def parse_price(
        text: Optional[str],
    ) -> Optional[int]:
        if not text:
            return None

        cleaned = (
            text.replace("KSh", "")
            .replace("KES", "")
            .replace("Ksh", "")
            .replace(",", "")
        )

        match = re.search(r"\d{3,}", cleaned)

        if not match:
            return None

        return int(match.group())

    @staticmethod
    def parse_year(
        text: Optional[str],
    ) -> Optional[int]:
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
        if not text:
            return None

        match = re.search(
            r"([\d,]+)\s*(km|kms|kilometers?)",
            text,
            re.IGNORECASE,
        )

        if not match:
            return None

        return int(match.group(1).replace(",", ""))

    @staticmethod
    def parse_engine_size(
        text: Optional[str],
    ) -> Optional[float]:
        if not text:
            return None

        match = re.search(
            r"(\d\.\d)\s*(L|litre|liter)",
            text,
            re.IGNORECASE,
        )

        if match:
            return float(match.group(1))

        match = re.search(
            r"(\d{3,4})\s*cc",
            text,
            re.IGNORECASE,
        )

        if match:
            return round(
                int(match.group(1)) / 1000,
                1,
            )

        return None
