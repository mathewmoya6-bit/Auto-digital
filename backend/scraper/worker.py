from scrapers.autochek_scraper import AutoChekScraper
from scrapers.jiji_scraper import JijiScraper

from services.market_pricing import save_market_listing


SCRAPERS = [
    AutoChekScraper(),
    JijiScraper()
]


def run():

    total = 0

    for scraper in SCRAPERS:

        print(f"Running {scraper.source}")

        try:

            listings = scraper.scrape()

            for listing in listings:
                save_market_listing(listing)

            print(f"Saved {len(listings)} listings")

            total += len(listings)

        except Exception as e:
            print(e)

    print(f"Completed. Total listings: {total}")


if __name__ == "__main__":
    run()
