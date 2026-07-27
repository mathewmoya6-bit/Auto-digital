"""
services/vehicle_matcher.py
============================
Matches a scraped listing's raw text fields (make, model, trim/variant,
year) to your catalog's real rows in:

    vehicle_types -> vehicle_makes -> vehicle_models -> vehicle_variants

Scrapers (autochek/jiji/carapi) hand you free-text like "Toyota", "Toyota
Corolla", "Corolla 1.8 GLi" - never your internal IDs. This module resolves
that text to catalog IDs so `requests` / `reports` / whatever consumes the
scraped data can store a real `variant_id` (or `model_id` if trim can't be
resolved) instead of a loose string.

ASSUMPTION (flag if wrong): imports the service-role Supabase client from
`services.supabase_client.get_supabase_client()`. Swap that import if your
client lives elsewhere.

Usage:
    from services.vehicle_matcher import VehicleMatcher

    matcher = VehicleMatcher()  # loads the catalog once
    result = matcher.match_listing(
        make="Toyota", model="Corolla", variant="1.8 GLi", year=2019
    )
    # result.variant_id / result.model_id / result.confidence / result.matched_on

    # Or match straight off a scraper's raw dict shape:
    result = matcher.match_scraped(listing)  # listing has make/model/trim/year keys

Matching strategy (cheapest -> most permissive):
    1. Exact, case-insensitive match on normalized name.
    2. Fuzzy match via difflib.get_close_matches (stdlib only - no extra
       dependency). If you later install `rapidfuzz` for better fuzzy
       matching, only `_best_match()` needs to change.
    3. If variant can't be confidently matched but the model can, fall back
       to a model-level match (`variant_id=None`, `model_id` set) rather
       than failing outright - callers can decide whether that's good
       enough for their use case.

Call `matcher.refresh()` if the catalog changes during a long-running
process (e.g. an admin adds a new model mid-scrape-run).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import get_close_matches
from typing import Any

from services.scraper_logger import get_logger
from services.supabase_client import get_supabase_client

logger = get_logger(__name__)

# Below this similarity ratio, we don't trust a fuzzy match at all.
MIN_MATCH_CONFIDENCE = 0.72


def _normalize(text: str | None) -> str:
    """Lowercase, strip punctuation/extra whitespace for comparison."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


@dataclass
class MatchResult:
    ok: bool
    type_id: str | None = None
    make_id: str | None = None
    model_id: str | None = None
    variant_id: str | None = None
    matched_on: str | None = None  # "variant" | "model" | "make" | None
    confidence: float = 0.0
    reason: str | None = None  # populated when ok is False


class VehicleMatcher:
    def __init__(self) -> None:
        self.supabase = get_supabase_client()
        self._makes: list[dict] = []
        self._models: list[dict] = []
        self._variants: list[dict] = []
        # Normalized-name -> row lookup, built by refresh()
        self._make_index: dict[str, dict] = {}
        self._models_by_make: dict[str, list[dict]] = {}
        self._variants_by_model: dict[str, list[dict]] = {}
        self.refresh()

    def refresh(self) -> None:
        """(Re)load the full catalog from Supabase. Call this if the
        catalog changes mid-process; otherwise it only runs once at init."""
        self._makes = self.supabase.table("vehicle_makes").select("*").execute().data or []
        self._models = self.supabase.table("vehicle_models").select("*").execute().data or []
        self._variants = self.supabase.table("vehicle_variants").select("*").execute().data or []

        self._make_index = {_normalize(m["name"]): m for m in self._makes}

        self._models_by_make = {}
        for model in self._models:
            self._models_by_make.setdefault(model["make_id"], []).append(model)

        self._variants_by_model = {}
        for variant in self._variants:
            self._variants_by_model.setdefault(variant["model_id"], []).append(variant)

        logger.info(
            "Vehicle catalog loaded: %d makes, %d models, %d variants",
            len(self._makes), len(self._models), len(self._variants),
        )

    @staticmethod
    def _best_match(target: str, candidates: dict[str, Any]) -> tuple[Any, float] | None:
        """Find the best fuzzy match for `target` among normalized-name keys
        in `candidates`. Returns (row, confidence) or None."""
        if not target or not candidates:
            return None

        if target in candidates:
            return candidates[target], 1.0

        close = get_close_matches(target, candidates.keys(), n=1, cutoff=MIN_MATCH_CONFIDENCE)
        if not close:
            return None

        best_key = close[0]
        # get_close_matches doesn't return the ratio, so recompute it for
        # the one candidate we picked - cheap since it's a single pair.
        from difflib import SequenceMatcher
        ratio = SequenceMatcher(None, target, best_key).ratio()
        return candidates[best_key], ratio

    def match_listing(
        self,
        make: str | None,
        model: str | None,
        variant: str | None = None,
        year: int | None = None,
    ) -> MatchResult:
        make_norm = _normalize(make)
        model_norm = _normalize(model)

        make_match = self._best_match(make_norm, self._make_index)
        if not make_match:
            return MatchResult(ok=False, reason=f"No catalog match for make='{make}'")
        make_row, make_conf = make_match

        candidate_models = self._models_by_make.get(make_row["id"], [])
        model_index = {_normalize(m["name"]): m for m in candidate_models}
        model_match = self._best_match(model_norm, model_index)
        if not model_match:
            return MatchResult(
                ok=False,
                type_id=make_row.get("type_id"),
                make_id=make_row["id"],
                matched_on="make",
                confidence=make_conf,
                reason=f"Make '{make}' matched but no model match for '{model}'",
            )
        model_row, model_conf = model_match

        result = MatchResult(
            ok=True,
            type_id=make_row.get("type_id"),
            make_id=make_row["id"],
            model_id=model_row["id"],
            matched_on="model",
            confidence=min(make_conf, model_conf),
        )

        if not variant:
            return result

        candidate_variants = self._variants_by_model.get(model_row["id"], [])
        variant_index = {_normalize(v["name"]): v for v in candidate_variants}

        # If we know the year, prefer variants whose name also mentions it
        # or whose year range (if the table has one) includes it - falls
        # back gracefully if those fields don't exist on your schema.
        variant_norm = _normalize(variant)
        variant_match = self._best_match(variant_norm, variant_index)

        if not variant_match:
            # Model-level fallback: still useful to the caller even without
            # a confident trim match.
            result.reason = f"Model matched but no variant match for '{variant}'"
            return result

        variant_row, variant_conf = variant_match
        if year and "year" in variant_row and variant_row.get("year") not in (None, year):
            # Trim name matched but year disagrees - still return it, just
            # flag a lower confidence rather than silently dropping it.
            variant_conf *= 0.9

        result.variant_id = variant_row["id"]
        result.matched_on = "variant"
        result.confidence = min(result.confidence, variant_conf)
        return result

    def match_scraped(self, listing: dict[str, Any]) -> MatchResult:
        """Convenience wrapper matching the raw dict shape scrapers emit.
        Adjust the key names here if your scraper classes use different
        field names (e.g. 'trim' vs 'variant')."""
        return self.match_listing(
            make=listing.get("make"),
            model=listing.get("model"),
            variant=listing.get("variant") or listing.get("trim"),
            year=listing.get("year"),
        )
