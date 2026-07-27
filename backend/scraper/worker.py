"""
Auto-D Market Scraper Worker

Runs all scrapers and stores results.
"""

import logging
from datetime import datetime

from scrapers.autochek_scraper import AutoChekScraper
from scrapers.jiji_scraper import JijiScraper
from scrapers.carapi_scraper import CarApiScraper

from services.market_pricing import (
    save_market_listing,
    update_market_prices
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

logger = logging.getLogger("worker")


SCRAPERS = [
    AutoChekScraper(),
    JijiScraper(),

    # CarAPI is optional if you have an API key
    # CarApiScraper(api_key="YOUR_API_KEY")
]


def run_scraper(scraper):

    logger.info(f"Starting {scraper.source}")

    try:

        listings = scraper.scrape()

        saved = 0

        for listing in listings:

            if save_market_listing(listing):
                saved += 1

        logger.info(
            f"{scraper.source}: {saved} listings processed."
        )

        return saved

    except Exception as e:

        logger.exception(
            f"{scraper.source} failed: {e}"
        )

        return 0


def run():

    logger.info("=" * 60)
    logger.info("AUTO-D MARKET SCRAPER STARTED")
    logger.info("=" * 60)

    start = datetime.utcnow()

    total = 0

    for scraper in SCRAPERS:

        total += run_scraper(scraper)

    logger.info("Updating market prices...")

    update_market_prices()

    end = datetime.utcnow()

    logger.info("=" * 60)
    logger.info("Completed")
    logger.info(f"Listings processed : {total}")
    logger.info(f"Started            : {start}")
    logger.info(f"Finished           : {end}")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
