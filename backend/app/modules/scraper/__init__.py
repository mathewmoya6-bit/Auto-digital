# app/modules/scraper/__init__.py
# ================================================================
# Auto-D Kenya - Scraper Module
# ================================================================


from app.modules.scraper.base_scraper import BaseScraper

from app.modules.scraper.jiji import JijiScraper

from app.modules.scraper.cheki import ChekiScraper

from app.modules.scraper.autochek import AutochekScraper

from app.modules.scraper.beepbeep import BeepBeepScraper

from app.modules.scraper.worker import ScraperWorker

from app.modules.scraper.service import ScraperService



__all__ = [

    "BaseScraper",

    "JijiScraper",

    "ChekiScraper",

    "AutochekScraper",

    "BeepBeepScraper",

    "ScraperWorker",

    "ScraperService"

]
