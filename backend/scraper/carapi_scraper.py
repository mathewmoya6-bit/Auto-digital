"""
CarAPI.dev Scraper
Auto-D Kenya

https://carapi.app/

"""

import requests

from .base_scraper import BaseScraper


class CarApiScraper(BaseScraper):

    BASE_URL = "https://carapi.app/api"

    def __init__(self, api_key=None):
        super().__init__("CarAPI")
        self.api_key = api_key

        self.headers = {
            "Accept": "application/json"
        }

        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def scrape_makes(self):
        """
        Fetch all vehicle makes.
        """

        response = requests.get(
            f"{self.BASE_URL}/makes",
            headers=self.headers,
            timeout=30
        )

        response.raise_for_status()

        return response.json()

    def scrape_models(self, make):
        """
        Fetch models for a make.
        """

        response = requests.get(
            f"{self.BASE_URL}/models",
            params={
                "make": make
            },
            headers=self.headers,
            timeout=30
        )

        response.raise_for_status()

        return response.json()

    def scrape_trims(self, make, model, year):
        """
        Fetch trims.
        """

        response = requests.get(
            f"{self.BASE_URL}/trims",
            params={
                "make": make,
                "model": model,
                "year": year
            },
            headers=self.headers,
            timeout=30
        )

        response.raise_for_status()

        return response.json()

    def scrape(self):

        vehicles = []

        makes = self.scrape_makes()

        for make in makes.get("data", []):

            make_name = make["name"]

            print(f"Loading {make_name}")

            models = self.scrape_models(make_name)

            for model in models.get("data", []):

                model_name = model["name"]

                year = model.get("year")

                trims = self.scrape_trims(
                    make_name,
                    model_name,
                    year
                )

                for trim in trims.get("data", []):

                    vehicle = {
                        "listing_id": trim.get("id"),
                        "url": None,
                        "make": make_name,
                        "model": model_name,
                        "trim": trim.get("trim"),
                        "year": year,
                        "price": None,
                        "currency": "KES",
                        "mileage": None,
                        "engine_size": trim.get("engine_displacement"),
                        "fuel_type": trim.get("fuel_type"),
                        "transmission": trim.get("transmission"),
                        "body_type": trim.get("body_type"),
                        "location": None,
                        "seller": "CarAPI"
                    }

                    vehicles.append(
                        self.normalize_listing(vehicle)
                    )

        return vehicles
