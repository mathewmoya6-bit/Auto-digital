import requests

from .base_scraper import BaseScraper


class JijiScraper(BaseScraper):

    BASE_URL = "https://jiji.co.ke"

    def __init__(self):
        super().__init__("Jiji")

    def scrape(self):

        vehicles = []

        #
        # TODO:
        # Parse listings
        #

        response = requests.get(self.BASE_URL)

        if response.status_code != 200:
            return vehicles

        return vehicles
