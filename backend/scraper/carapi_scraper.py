"""
carapi_scraper.py
==================
Unlike autochek_scraper / jiji_scraper, this doesn't scrape HTML - CarAPI
(https://carapi.app) is a real REST/JSON vehicle-data API, so we just call it.
It's kept in `scrapers/` (rather than `services/`) because it plugs into the
same BaseScraper.run() pipeline and feeds the same `scraped_listings`-adjacent
tables - here specifically a `vehicle_reference` table used by
services/vehicle_matcher.py to normalize make/model/trim spellings.

Auth flow (per CarAPI docs, verified July 2026):
    POST https://carapi.app/api/auth/login   {"api_token": ..., "api_secret": ...}
    -> raw JWT string in the response body
    Authorization: Bearer <jwt>   on all subsequent requests
    Tokens expire after 7 days, so we cache + refresh lazily.

Endpoints used:
    GET /api/makes                       -> list of makes
    GET /api/models?make=<make>&year=<y>  -> models for a make/year
    GET /api/trims?make=<make>&model=<model>&year=<y>  -> trim-level specs

Credentials: set CARAPI_TOKEN / CARAPI_SECRET env vars (from your CarAPI account).
"""

from __future__ import annotations

import os
import time
from typing import Iterable, Optional

from scrapers.base_scraper import BaseScraper, ListingRecord
from services.scraper_logger import get_logger

logger = get_logger(__name__)

CARAPI_BASE = "https://carapi.app/api"


class CarApiScraper(BaseScraper):
    """Pulls canonical make/model/trim reference data from CarAPI.

    This intentionally does NOT produce `ListingRecord`s (there's no price/listing
    here, just reference specs) - it overrides `run()` with its own simpler loop
    rather than forcing reference data through the marketplace-listing shape.
    """

    source_name = "carapi"

    def __init__(
        self,
        years: Optional[list[int]] = None,
        makes: Optional[list[str]] = None,
        api_token: Optional[str] = None,
        api_secret: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.years = years or [2018, 2019, 2020, 2021, 2022, 2023, 2024]
        self.makes = makes  # None => fetch all makes first
        self.api_token = api_token or os.environ.get("CARAPI_TOKEN")
        self.api_secret = api_secret or os.environ.get("CARAPI_SECRET")
        self._jwt: Optional[str] = None
        self._jwt_fetched_at: float = 0.0

    # ------------------------------------------------------------------ #
    # Auth
    # ------------------------------------------------------------------ #

    def _ensure_jwt(self) -> Optional[str]:
        """CarAPI's public dataset works without auth for limited use, but a
        token unlocks full rate limits. Auth is optional - if creds are missing
        we just proceed unauthenticated and let CarAPI apply its free-tier limits."""
        if not self.api_token or not self.api_secret:
            return None

        seven_days = 7 * 24 * 3600
        if self._jwt and (time.time() - self._jwt_fetched_at) < (seven_days - 3600):
            return self._jwt

        # NOTE: base `get()` is GET-only; login is a POST, so call the session directly.
        resp = self.session.post(
            f"{CARAPI_BASE}/auth/login",
            json={"api_token": self.api_token, "api_secret": self.api_secret},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        self._jwt = resp.text.strip().strip('"')
        self._jwt_fetched_at = time.time()
        return self._jwt

    def _auth_headers(self) -> dict:
        jwt = self._ensure_jwt()
        return {"Authorization": f"Bearer {jwt}"} if jwt else {}

    # ------------------------------------------------------------------ #
    # BaseScraper interface (not really used here - see run() override below)
    # ------------------------------------------------------------------ #

    def fetch_listing_urls(self, max_listings: int) -> Iterable[str]:
        raise NotImplementedError("CarApiScraper overrides run() directly; see sync_reference_data().")

    def parse_listing(self, html: str, url: str) -> Optional[ListingRecord]:
        raise NotImplementedError("CarApiScraper overrides run() directly; see sync_reference_data().")

    # ------------------------------------------------------------------ #
    # Reference-data sync (the actual job this scraper does)
    # ------------------------------------------------------------------ #

    def _get_makes(self) -> list[str]:
        resp = self.get(f"{CARAPI_BASE}/makes", headers=self._auth_headers(), params={"limit": 1000})
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return [m["name"] for m in data if "name" in m]

    def _get_models(self, make: str, year: int) -> list[dict]:
        resp = self.get(
            f"{CARAPI_BASE}/models",
            headers=self._auth_headers(),
            params={"make": make, "year": year, "limit": 1000},
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    def sync_reference_data(self, upsert: bool = True) -> dict:
        """Fetch make/model/year combos into the `vehicle_reference` table.

        Expected Supabase schema:
            vehicle_reference (
                id bigserial primary key,
                make text, model text, year int,
                submodel text, body_type text,
                synced_at timestamptz,
                unique (make, model, year, submodel)
            )
        """
        run_logger = None
        from services.scraper_logger import ScraperRunLogger

        run_logger = ScraperRunLogger(source=self.source_name, supabase_client=self.supabase)
        run_logger.start()

        makes = self.makes or self._get_makes()
        fetched = saved = errors = 0

        for make in makes:
            for year in self.years:
                try:
                    models = self._get_models(make, year)
                except Exception as exc:  # noqa: BLE001
                    errors += 1
                    run_logger.log_error(f"{make}/{year}", exc)
                    continue

                for model in models:
                    fetched += 1
                    row = {
                        "make": make,
                        "model": model.get("name"),
                        "year": year,
                        "submodel": model.get("submodel"),
                        "body_type": model.get("body_type"),
                    }
                    if upsert and not self.dry_run and self.supabase is not None:
                        try:
                            self.supabase.table("vehicle_reference").upsert(
                                row, on_conflict="make,model,year,submodel"
                            ).execute()
                            saved += 1
                        except Exception as exc:  # noqa: BLE001
                            errors += 1
                            run_logger.log_error(f"{make}/{model.get('name')}/{year}", exc)
                    elif self.dry_run:
                        logger.info("[dry-run] %s", row)

        summary = {"found": fetched, "parsed": fetched, "saved": saved, "errors": errors}
        run_logger.finish(summary)
        return summary


if __name__ == "__main__":
    # Manual smoke test: `python -m scrapers.carapi_scraper`
    scraper = CarApiScraper(years=[2020], makes=["Toyota"], dry_run=True)
    print(scraper.sync_reference_data())
