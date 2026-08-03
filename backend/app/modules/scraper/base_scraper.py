# app/modules/scraper/base_scraper.py
# ================================================================
# Auto-D Kenya - Base Scraper
# ================================================================

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
    Base scraper used by all vehicle scrapers.
    """

    USER_AGENTS = [
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/138.0 Safari/537.36"
        ),
        (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/138.0 Safari/537.36"
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 "
            "(KHTML, like Gecko)"
        ),
    ]

    def __init__(
        self,
        source_name: str,
        base_url: str,
    ):

        self.source_name = source_name
        self.base_url = base_url

        self.headers = {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": (
                "text/html,"
                "application/xhtml+xml,"
                "application/xml;q=0.9,"
                "*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Referer": base_url,
        }

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
            headers=self.headers,
        )

    # ============================================================
    # ENTRY POINT
    # ============================================================

    async def run(
        self,
        pages: int = 3,
        limit_per_page: int = 20,
    ) -> Dict[str, Any]:

        logger.info(
            "[%s] Starting scraper",
            self.source_name,
        )

        try:

            result = await self.scrape(
                pages=pages,
                limit_per_page=limit_per_page,
            )

            logger.info(
                "[%s] Completed (%d listings)",
                self.source_name,
                len(result.get("listings", [])),
            )

            return result

        except Exception:

            logger.exception(
                "[%s] Scraper crashed",
                self.source_name,
            )

            return {
                "status": "failed",
                "listings": [],
                "error": "Scraper crashed",
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
    # FETCH PAGE
    # ============================================================

    async def _fetch_page(
        self,
        url: str,
        params: Optional[dict] = None,
    ) -> Optional[BeautifulSoup]:

        retries = 3

        for attempt in range(retries):

            try:

                logger.info(
                    "[%s] GET %s",
                    self.source_name,
                    url,
                )

                response = await self.client.get(
                    url,
                    params=params,
                )

                response.raise_for_status()

                await asyncio.sleep(
                    random.uniform(0.5, 1.5)
                )

                return BeautifulSoup(
                    response.text,
                    "html.parser",
                )

            except Exception as e:

                logger.warning(
                    "[%s] Attempt %d/%d failed: %s",
                    self.source_name,
                    attempt + 1,
                    retries,
                    str(e),
                )

                await asyncio.sleep(
                    2 ** attempt
                )

        logger.error(
            "[%s] Failed fetching %s",
            self.source_name,
            url,
        )

        return None

    # ============================================================
    # HELPERS
    # ============================================================

    def _clean_text(
        self,
        value: Optional[str],
    ) -> str:

        if not value:
            return ""

        return " ".join(
            value.split()
        ).strip()

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

    def _parse_price(
        self,
        text: str,
    ) -> Optional[int]:

        if not text:
            return None

        text = (
            text.replace("KSh", "")
            .replace("Ksh", "")
            .replace("KES", "")
            .replace(",", "")
        )

        match = re.search(
            r"(\d{3,})",
            text,
        )

        if not match:
            return None

        return self._parse_int(
            match.group(1)
        )

    def _parse_year(
        self,
        text: str,
    ) -> Optional[int]:

        match = re.search(
            r"\b(19|20)\d{2}\b",
            text,
        )

        if match:
            return int(match.group())

        return None

    def _parse_mileage(
        self,
        text: str,
    ) -> Optional[int]:

        match = re.search(
            r"([\d,]+)\s*(km|kms)",
            text,
            re.I,
        )

        if not match:
            return None

        return self._parse_int(
            match.group(1)
        )

    def _parse_engine_size(
        self,
        text: str,
    ) -> Optional[float]:

        match = re.search(
            r"(\d\.\d|\d{3,4})\s*(cc|l)",
            text,
            re.I,
        )

        if not match:
            return None

        return self._parse_float(
            match.group(1)
        )

    # ============================================================
    # CLEANUP
    # ============================================================

    async def close(self):

        await self.client.aclose()
