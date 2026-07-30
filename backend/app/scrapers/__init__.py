# app/scrapers/__init__.py
# Auto-D Kenya - Scrapers Package
# ================================================================

"""Scrapers package for Auto-D Kenya."""

from .base_scraper import BaseScraper
from .jiji import JijiScraper
from .cheki import ChekiScraper
from .autochek import AutochekScraper
from .beepbeep import BeepBeepScraper
from .pigiame import PigiameScraper

__all__ = [
    "BaseScraper",
    "JijiScraper",
    "ChekiScraper",
    "AutochekScraper",
    "BeepBeepScraper",
    "PigiameScraper"
]
