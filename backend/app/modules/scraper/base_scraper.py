# app/modules/scraper/base_scraper.py

import asyncio
import logging
import random
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import httpx
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Base class for all marketplace scrapers.
    """

    def __init__(
        self,
        source_name: str,
        base_url: str,
    ):
        self.source_name = source_name
        self.base_url = base_url

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/138.0 Safari/537.36"
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

    # ============================================================
    # ENTRY POINT
    # ============================================================

    async def run(
        self,
        pages: int = 3,
        limit_per_page: int = 20,
    ) -> Dict[str, Any]:

        logger.info("[%s] scraper started", self.source_name)

        try:

            result = await self.scrape(
                pages=pages,
                limit_per_page=limit_per_page,
            )

            result.setdefault("status", "success")
            result.setdefault("listings", [])
            result.setdefault(
                "listings_found",
                len(result["listings"]),
            )

            logger.info("[%s] scraper finished", self.source_name)

            return result

        except Exception:

            logger.exception(
                "[%s] scraper crashed",
                self.source_name,
            )

            return {
                "status": "failed",
                "error": "Scraper crashed",
                "listings": [],
                "listings_found": 0,
                "listings_saved": 0,
            }

    # ============================================================
    # CHILD IMPLEMENTATION
    # ============================================================

    @abstractmethod
    async def scrape(
        self,
        pages: int = 3,
        limit_per_page: int = 20,
    ) -> Dict[str, Any]:
        pass

    # ============================================================
    # HTTP
    # ============================================================

    async def _fetch_page(
        self,
        url: str,
        params: Optional[dict] = None,
    ) -> Optional[BeautifulSoup]:

        try:

            async with httpx.AsyncClient(
                timeout=30,
                headers=self.headers,
                follow_redirects=True,
            ) as client:

                response = await client.get(
                    url,
                    params=params,
                )

                response.raise_for_status()

                await asyncio.sleep(
                    random.uniform(0.5, 1.2)
                )

                return BeautifulSoup(
                    response.text,
                    "html.parser",
                )

        except Exception:

            logger.exception(
                "Failed fetching %s",
                url,
            )

            return None

    # ============================================================
    # TEXT
    # ============================================================

    def _clean_text(
        self,
        value: Optional[str],
    ) -> str:

        if not value:
            return ""

        return " ".join(value.split()).strip()

    # ============================================================
    # NUMBER PARSERS
    # ============================================================

    def _parse_int(
        self,
        value: Optional[str],
    ) -> Optional[int]:

        if not value:
            return None

        try:
            return int(
                re.sub(
                    r"[^\d]",
                    "",
                    str(value),
                )
            )
        except Exception:
            return None

    def _parse_float(
        self,
        value: Optional[str],
    ) -> Optional[float]:

        if not value:
            return None

        try:
            return float(
                re.sub(
                    r"[^\d.]",
                    "",
                    str(value),
                )
            )
        except Exception:
            return None

    # ============================================================
    # VEHICLE HELPERS
    # ============================================================

    def _parse_price(
        self,
        text: str,
    ) -> Optional[int]:

        if not text:
            return None

        text = (
            text.replace("KSh", "")
            .replace("KES", "")
            .replace("Ksh", "")
            .replace(",", "")
        )

        match = re.search(r"\d{3,}", text)

        if not match:
            return None

        try:
            return int(match.group())
        except Exception:
            return None

    def _parse_year(
        self,
        text: str,
    ) -> Optional[int]:

        if not text:
            return None

        match = re.search(
            r"\b(19\d{2}|20\d{2})\b",
            text,
        )

        if match:
            return int(match.group())

        return None

    def _parse_mileage(
        self,
        text: str,
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

        try:
            return int(
                match.group(1).replace(",", "")
            )
        except Exception:
            return None

    def _parse_engine_size(
        self,
        text: str,
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
            try:
                return round(
                    int(match.group(1)) / 1000,
                    1,
                )
            except Exception:
                pass

        return None
