# app/modules/scraper/__init__.py
# Auto-D Kenya - Scraper Module
# ================================================================

"""Scraper module for Auto-D Kenya."""

from .router import router
from .service import ScraperService
from .worker import ScraperWorker
from .autochek import AutochekScraper
from .jiji import JijiScraper
from .carapi import CarApiScraper
from .schemas import (
    ScraperRunRequest,
    ScraperRunResponse,
    ScraperStatusResponse,
    ScraperSourceResponse,
    ScraperHealthResponse
)

__all__ = [
    "router",
    "ScraperService",
    "ScraperWorker",
    "AutochekScraper",
    "JijiScraper",
    "CarApiScraper",
    "ScraperRunRequest",
    "ScraperRunResponse",
    "ScraperStatusResponse",
    "ScraperSourceResponse",
    "ScraperHealthResponse"
]
