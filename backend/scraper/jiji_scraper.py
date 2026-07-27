"""
jiji_scraper.py
================
Scraper for jiji.co.ke's car marketplace.

Site shape (verified against the live site, July 2026):
  - Category root: https://jiji.co.ke/cars  (also /cars/<brand>, /<location>/cars)
  - Result cards link to detail pages at /cars/<slug>-<listing-id>.html style URLs
  - Card/detail text exposes: title ("Toyota Prado 2019"), price ("KSh 1,565,000"),
    condition ("Foreign Used" / "Local Used"), transmission ("Automatic"/"Manual"),
    engine cc, mileage ("52,000KM" / "52000km"), location, and sometimes a
    "X years on Jiji" seller-tenure badge.

Like AutoChek, this is a JS-enhanced but server-rendered listing site, so
requests + BeautifulSoup can read the initial HTML. If Jiji switches to a
client-side-rendered SPA shell (no listing data in the raw HTML), swap
`self.get()` for a Playwright-rendered fetch - the parsing functions below
don't need to change, since they operate on extracted page text either way.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper, ListingRecord

BASE_URL = "https://jiji.co.ke"

# Jiji listing detail pages end in "-<alphanumeric-id>.html" or similar unique suffix
LISTING_HREF_RE = re.compile(r"/(?:[a-z0-9\-]+/)?cars?/[a-z0-9\-]+_?\d+\.html", re.IGNORECASE)


class JijiScraper(BaseScraper):
    source_name = "jiji"

    def __init__(self, category_path: str = "/cars", location: Optional[str] = None, **kwargs):
        """
        category_path: e.g. "/cars", "/cars/toyota"
        location: optional Jiji location slug, e.g. "nairobi", "kilimani" -
                  when set, scrapes f"/{location}{category_path}" instead.
        """
        super().__init__(**kwargs)
        path = f"/{location}{category_path}" if location else category_path
        self.listing_index_url = urljoin(BASE_URL, path)

    # ------------------------------------------------------------------ #
    # Discovery
    # ------------------------------------------------------------------ #

    def fetch_listing_urls(self, max_listings: int) -> Iterable[str]:
        seen = set()
        page = 1
        while len(seen) < max_listings:
            # Jiji paginates via ?page=N
            resp = self.get(self.listing_index_url, params={"page": page})
            if resp.status_code == 404:
                break
            soup = BeautifulSoup(resp.text, "html.parser")

            page_urls = self._extract_listing_links(soup)
            if not page_urls:
                break

            new_this_page = 0
            for url in page_urls:
                if url not in seen:
                    seen.add(url)
                    new_this_page += 1
                    yield url
                    if len(seen) >= max_listings:
                        return
            if new_this_page == 0:
                break
            page += 1

    @staticmethod
    def _extract_listing_links(soup: BeautifulSoup) -> list[str]:
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if LISTING_HREF_RE.search(href):
                links.append(urljoin(BASE_URL, href))
        return list(dict.fromkeys(links))

    # ------------------------------------------------------------------ #
    # Parsing
    # ------------------------------------------------------------------ #

    def parse_listing(self, html: str, url: str) -> Optional[ListingRecord]:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n", strip=True)

        external_id = self._external_id_from_url(url)
        if not external_id:
            return None

        make, model, year = self._parse_make_model_year(text, soup)
        price = self._parse_price(text)
        mileage = self._parse_mileage(text)
        engine_cc = self._parse_engine_cc(text)
        transmission = self._parse_transmission(text)
        fuel_type = self._parse_fuel_type(text)
        condition = self._parse_condition(text)
        location = self._parse_location(text)
        seller_type = self._parse_seller_type(text)

        images = [
            img["src"]
            for img in soup.find_all("img", src=True)
            if img["src"].startswith("http") and "jiji" in img["src"]
        ]

        return ListingRecord(
            source=self.source_name,
            external_id=external_id,
            url=url,
            make=make,
            model=model,
            year=year,
            price=price,
            currency="KES",
            mileage_km=mileage,
            engine_cc=engine_cc,
            transmission=transmission,
            fuel_type=fuel_type,
            condition=condition,
            location=location,
            seller_type=seller_type,
            images=images[:5],
            raw_title=self._parse_title(soup),
        )

    # ------------------------------------------------------------------ #
    # Field parsers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _external_id_from_url(url: str) -> Optional[str]:
        m = re.search(r"([a-z0-9\-]+_?\d+)\.html", url, re.IGNORECASE)
        return m.group(1) if m else None

    @staticmethod
    def _parse_title(soup: BeautifulSoup) -> Optional[str]:
        h1 = soup.find("h1")
        return h1.get_text(strip=True) if h1 else None

    def _parse_make_model_year(self, text: str, soup: BeautifulSoup):
        title = self._parse_title(soup) or text.split("\n", 1)[0]
        year_m = re.search(r"\b(19|20)\d{2}\b", title)
        year = int(year_m.group(0)) if year_m else None

        # Titles are typically "<Make> <Model...> <Year> <Color>", e.g. "Toyota Prado 2019"
        # Strip the year and split the remainder into make (first word) / model (rest).
        without_year = re.sub(r"\b(19|20)\d{2}\b", "", title).strip()
        parts = without_year.split()
        make = parts[0].title() if parts else None
        model = " ".join(parts[1:]).title() if len(parts) > 1 else None
        return make, model, year

    @staticmethod
    def _parse_price(text: str) -> Optional[float]:
        m = re.search(r"KSh\s*([\d,]+)", text)
        return float(m.group(1).replace(",", "")) if m else None

    @staticmethod
    def _parse_mileage(text: str) -> Optional[int]:
        # e.g. "52,000KM", "52000km", "111,000 kms"
        m = re.search(r"([\d,]{3,})\s*[Kk][Mm][Ss]?\b", text)
        return int(m.group(1).replace(",", "")) if m else None

    @staticmethod
    def _parse_engine_cc(text: str) -> Optional[int]:
        m = re.search(r"(\d{3,5})\s*cc\b", text, re.IGNORECASE)
        if m:
            return int(m.group(1))
        m = re.search(r"(\d(?:\.\d)?)\s*[Ll]\b", text)  # "2.0L" style
        return int(float(m.group(1)) * 1000) if m else None

    @staticmethod
    def _parse_transmission(text: str) -> Optional[str]:
        m = re.search(r"\b(Automatic|Manual)\b", text, re.IGNORECASE)
        return m.group(1).title() if m else None

    @staticmethod
    def _parse_fuel_type(text: str) -> Optional[str]:
        m = re.search(r"\b(Petrol|Diesel|Hybrid|Electric)\b", text, re.IGNORECASE)
        return m.group(1).title() if m else None

    @staticmethod
    def _parse_condition(text: str) -> Optional[str]:
        m = re.search(r"\b(Foreign Used|Local Used|Brand New)\b", text, re.IGNORECASE)
        return m.group(1).title() if m else None

    @staticmethod
    def _parse_location(text: str) -> Optional[str]:
        # Jiji shows a standalone location line (e.g. "Nairobi, Kilimani") near the top.
        m = re.search(r"\n([A-Z][a-zA-Z]+,\s*[A-Za-z ]+)\n", text)
        return m.group(1).strip() if m else None

    @staticmethod
    def _parse_seller_type(text: str) -> Optional[str]:
        if re.search(r"\bENTERPRISE\b", text):
            return "dealer"
        if re.search(r"\d+\+?\s*years? on Jiji", text, re.IGNORECASE):
            return "individual"
        return None


if __name__ == "__main__":
    # Manual smoke test: `python -m scrapers.jiji_scraper`
    scraper = JijiScraper(category_path="/cars/toyota", dry_run=True)
    summary = scraper.run(max_listings=10)
    print(summary)
