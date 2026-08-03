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
    Base class for all scrapers.
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
    # PUBLIC ENTRY POINT
    # ============================================================

    async def run(
        self,
        pages: int = 3,
        limit_per_page: int = 20,
    ) -> Dict[str, Any]:
        """
        Called by ScraperWorker.
        """

        logger.info(
            f"[{self.source_name}] starting scraper"
        )

        try:

            result = await self.scrape(
                pages=pages,
                limit_per_page=limit_per_page,
            )

            logger.info(
                f"[{self.source_name}] scraper completed"
            )

            return result

        except Exception:

            logger.exception(
                f"[{self.source_name}] scraper crashed"
            )

            return {
                "status": "failed",
                "listings": [],
                "error": "Scraper crashed",
            }

    # ============================================================
    # IMPLEMENTED BY CHILD CLASSES
    # ============================================================

    @abstractmethod
    async def scrape(
        self,
        pages: int = 3,
        limit_per_page: int = 20,
    ) -> Dict[str, Any]:
        pass

    # ============================================================
    # FETCH HTML
    # ============================================================

    async def _fetch_page(
        self,
        url: str,
        params: Optional[dict] = None,
    ) -> Optional[BeautifulSoup]:

        try:

            async with httpx.AsyncClient(
                timeout=30,
                follow_redirects=True,
                headers=self.headers,
            ) as client:

                response = await client.get(
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

        except Exception:

            logger.exception(
                f"Failed fetching {url}"
            )

            return None

    # ============================================================
    # PRICE PARSER
    # ============================================================

    def _parse_price(
        self,
        text: str,
    ) -> Optional[int]:

        if not text:
            return None

        match = re.search(
            r"([\d,]+)",
            text.replace("KSh", "")
                .replace("KES", "")
                .replace("Ksh", ""),
        )

        if not match:
            return None

        try:
            return int(
                match.group(1).replace(",", "")
            )
        except Exception:
            return None

    # ============================================================
    # INTEGER PARSER
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

    # ============================================================
    # FLOAT PARSER
    # ============================================================

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
    # CLEAN STRING
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
