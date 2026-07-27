import requests

from .base_scraper import BaseScraper


class AutoChekScraper(BaseScraper):

    BASE_URL = "https://autochek.africa"

    def __init__(self):
        super().__init__("AutoChek")

    def scrape(self):

        vehicles = []

        #
        # TODO:
        # Replace with actual AutoChek API
        #

        response = requests.get(self.BASE_URL)

        if response.status_code != 200:
            return vehicles

        #
        # Parse HTML or API response
        #

        return vehicles
