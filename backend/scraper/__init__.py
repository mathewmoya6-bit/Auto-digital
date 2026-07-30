# scrapers/__init__.py
# Auto-D Kenya - Scrapers Package
# ================================================================
# TYPE: SERVICE - Package initialization

from .base_scraper import BaseScraper
from .jiji_scraper import JijiScraper
from .cheki_scraper import ChekiScraper
from .autochek_scraper import AutochekScraper
from .beepbeep_scraper import BeepBeepScraper
from .pigiame_scraper import PigiameScraper

__all__ = [
    "BaseScraper",
    "JijiScraper",
    "ChekiScraper",
    "AutochekScraper",
    "BeepBeepScraper",
    "PigiameScraper"
]
