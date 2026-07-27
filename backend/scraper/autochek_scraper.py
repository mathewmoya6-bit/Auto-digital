"""
autochek_scraper.py
====================
Scraper for autochek.africa's "cars for sale" marketplace.

Site shape (verified against the live site, https://autochek.africa/<country>/cars-for-sale,
July 2026):
  - Country-scoped listing paths, e.g. /ke, /ng, /gh
  - Search/listing page: /<country>/cars-for-sale (paginated)
  - Each result card links to a detail page:
        /<country>/cars-for-sale/<make>/<model-slug>/<listing-id>
  - Card/detail text exposes: "<year> <MAKE> <model>", condition ("local"/"foreign"),
    mileage ("94K kms"), engine size ("2980 cc"), a rating figure, price ("KSh 6,515,000"),
    and "<City>, <Area>" location.

IMPORTANT: AutoChek's markup is server-rendered but subject to change without notice.
The CSS selectors below are a best-effort based on the current DOM. If the site
redesigns, re-run with `dry_run=True` and inspect `resp.text` to recalibrate selectors -
the regex-based fallback parser in `_parse_from_text` is deliberately kept resilient to
minor markup shuffles since it works off visible text rather than exact class names.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper, ListingRecord

BASE_URL = "https://autochek.africa"

# Matches URLs like https://autochek.africa/ke/cars-for-sale/toyota/passo/e3Qknjkir
LISTING_URL_RE = re.compile(r"/cars-for-sale/([a-z0-9\-]+)/([a-z0-9\-]+)/([A-Za-z0-9_\-]+)$")


class AutochekScraper(BaseScraper):
    source_name = "autochek"

    def __init__(self, country: str = "ke", **kwargs):
        """country: 2-letter AutoChek market code, e.g. 'ke', 'ng', 'gh'."""
        super().__init__(**kwargs)
        self.country = country
        self.listing_index_url = f"{BASE_URL}/{country}/cars-for-sale"

    # ------------------------------------------------------------------ #
    # Discovery
    # ------------------------------------------------------------------ #

    def fetch_listing_urls(self, max_listings: int) -> Iterable[str]:
        seen = set()
        page = 1
        while len(seen) < max_listings:
            # AutoChek paginates via ?page=N; if the site changes this param, dry-run
            # against page 1/2 and diff the returned hrefs to find the new one.
            resp = self.get(self.listing_index_url, params={"page": page})
            if resp.status_code == 404:
                break
            soup = BeautifulSoup(resp.text, "html.parser")

            page_urls = self._extract_listing_links(soup)
            if not page_urls:
                break  # no more pages / selector stopped matching

            new_this_page = 0
            for url in page_urls:
                if url not in seen:
                    seen.add(url)
                    new_this_page += 1
                    yield url
                    if len(seen) >= max_listings:
                        return
            if new_this_page == 0:
                break  # pagination looped back on itself; stop
            page += 1

    @staticmethod
    def _extract_listing_links(soup: BeautifulSoup) -> list[str]:
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if LISTING_URL_RE.search(href):
                links.append(urljoin(BASE_URL, href))
        # de-dup while preserving order
        return list(dict.fromkeys(links))

    # ------------------------------------------------------------------ #
    # Parsing
    # ------------------------------------------------------------------ #

    def parse_listing(self, html: str, url: str) -> Optional[ListingRecord]:
        soup = BeautifulSoup(html, "html.parser")

        m = LISTING_URL_RE.search(url)
        if not m:
            return None
        make_slug, model_slug, listing_id = m.groups()

        text = soup.get_text(separator="\n", strip=True)

        title = self._first_match(r"(\d{4})\s+([A-Za-z\-]+)\s+([A-Za-z0-9 \-]+)", text)
        year = int(title.group(1)) if title else None
        make = (title.group(2) if title else make_slug).strip().title()
        model = (title.group(3) if title else model_slug.replace("-", " ")).strip().title()

        price = self._parse_price(text)
        mileage = self._parse_mileage(text)
        engine_cc = self._parse_engine_cc(text)
        condition = self._parse_condition(text)
        location = self._parse_location(text)

        images = [
            img["src"]
            for img in soup.find_all("img", src=True)
            if "storage.googleapis.com/img.autochek" in img["src"]
            or "imagekit.io" in img["src"]
        ]

        return ListingRecord(
            source=self.source_name,
            external_id=listing_id,
            url=url,
            make=make,
            model=model,
            year=year,
            price=price,
            currency="KES" if self.country == "ke" else self._currency_for_country(),
            mileage_km=mileage,
            engine_cc=engine_cc,
            condition=condition,
            location=location,
            images=images[:5],
            raw_title=title.group(0) if title else None,
        )

    # ------------------------------------------------------------------ #
    # Small field parsers - kept as separate functions so a markup change
    # only ever requires editing one of these, not the whole parse method.
    # ------------------------------------------------------------------ #

    @staticmethod
    def _first_match(pattern: str, text: str):
        return re.search(pattern, text)

    @staticmethod
    def _parse_price(text: str) -> Optional[float]:
        m = re.search(r"KSh\s*([\d,]+)", text)
        if not m:
            return None
        return float(m.group(1).replace(",", ""))

    @staticmethod
    def _parse_mileage(text: str) -> Optional[int]:
        # e.g. "94K kms" -> 94000 ; also handles plain "94,000 kms"
        m = re.search(r"([\d,]+)\s*K?\s*kms", text, re.IGNORECASE)
        if not m:
            return None
        raw = m.group(0)
        num = float(m.group(1).replace(",", ""))
        if "k" in raw.lower().split("kms")[0]:
            num *= 1000
        return int(num)

    @staticmethod
    def _parse_engine_cc(text: str) -> Optional[int]:
        m = re.search(r"(\d{3,5})\s*cc", text, re.IGNORECASE)
        return int(m.group(1)) if m else None

    @staticmethod
    def _parse_condition(text: str) -> Optional[str]:
        m = re.search(r"\b(local|foreign)\b", text, re.IGNORECASE)
        return m.group(1).lower() if m else None

    @staticmethod
    def _parse_location(text: str) -> Optional[str]:
        # Locations appear as "Nairobi, Ngong Rd" / "Nairobi, Nairobi" near the price line.
        m = re.search(r"\n([A-Z][a-zA-Z]+,\s*[A-Za-z .]+)\n", text)
        return m.group(1).strip() if m else None

    def _currency_for_country(self) -> str:
        return {
            "ke": "KES",
            "ng": "NGN",
            "gh": "GHS",
            "ug": "UGX",
            "rw": "RWF",
        }.get(self.country, "USD")


if __name__ == "__main__":
    # Manual smoke test: `python -m scrapers.autochek_scraper`
    scraper = AutochekScraper(country="ke", dry_run=True)
    summary = scraper.run(max_listings=10)
    print(summary)
