# app/modules/valuation/baseprice_engine.py
# ================================================================
# Auto-D Kenya - KRA CRSP-based Vehicle Base Price Engine
# ================================================================
#
# Resolves a vehicle (make/model/variant/year/engine) to a base
# market value by:
#   1. Fuzzy-matching against the KRA CRSP schedule stored in
#      `vehicle_base_prices` (rapidfuzz).
#   2. Computing vehicle age from year of manufacture.
#   3. Looking up the applicable depreciation bracket from
#      `depreciation_rates` (DB-driven, NOT hardcoded — rates
#      must be verified against the official KRA gazette before
#      being entered into that table).
#   4. Applying: base_value = crsp_price * (1 - depreciation_rate)
#
# IMPORTANT: This module does NOT hardcode any depreciation
# percentages. All age-bracket rates come from `depreciation_rates`
# in the DB. If that table is empty or a bracket is missing for a
# given vehicle age, this engine returns an explicit error rather
# than guessing or defaulting to 0% depreciation — silently using
# an unverified or missing rate would produce wrong valuations.
# ================================================================

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from rapidfuzz import fuzz, process

from app.core.database import get_supabase

logger = logging.getLogger(__name__)

# Minimum fuzzy-match confidence (0-100) to accept a CRSP match
# without flagging it as low-confidence.
DEFAULT_MATCH_THRESHOLD = 72


@dataclass
class BasePriceResult:
    matched: bool
    crsp_price: Optional[int] = None
    depreciated_value: Optional[int] = None
    depreciation_rate: Optional[float] = None
    vehicle_age_years: Optional[int] = None
    match_confidence: Optional[float] = None
    matched_record: Optional[Dict[str, Any]] = None
    warning: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matched": self.matched,
            "crsp_price": self.crsp_price,
            "depreciated_value": self.depreciated_value,
            "depreciation_rate": self.depreciation_rate,
            "vehicle_age_years": self.vehicle_age_years,
            "match_confidence": self.match_confidence,
            "matched_record": self.matched_record,
            "warning": self.warning,
            "error": self.error,
        }


class BasePriceEngine:
    """
    KRA CRSP-grounded base price + age-depreciation engine.
    """

    def __init__(self, match_threshold: int = DEFAULT_MATCH_THRESHOLD):
        self.supabase = get_supabase()
        self.match_threshold = match_threshold

        # In-memory caches, refreshed lazily
        self._crsp_cache: Optional[List[Dict[str, Any]]] = None
        self._depreciation_cache: Optional[List[Dict[str, Any]]] = None

    # ============================================================
    # CACHE LOADERS
    # ============================================================

    def _load_crsp_catalog(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Load the full CRSP base price catalog into memory for fuzzy matching."""
        if self._crsp_cache is not None and not force_refresh:
            return self._crsp_cache

        try:
            result = (
                self.supabase
                .table("vehicle_base_prices")
                .select("*")
                .execute()
            )
            self._crsp_cache = result.data or []
            logger.info(f"Loaded {len(self._crsp_cache)} CRSP base price records")
        except Exception as e:
            logger.error(f"Failed to load vehicle_base_prices: {e}")
            self._crsp_cache = []

        return self._crsp_cache

    def _load_depreciation_brackets(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Load age-bracket depreciation rates into memory."""
        if self._depreciation_cache is not None and not force_refresh:
            return self._depreciation_cache

        try:
            result = (
                self.supabase
                .table("depreciation_rates")
                .select("*")
                .order("age_min_years")
                .execute()
            )
            self._depreciation_cache = result.data or []
            logger.info(f"Loaded {len(self._depreciation_cache)} depreciation brackets")
        except Exception as e:
            logger.error(f"Failed to load depreciation_rates: {e}")
            self._depreciation_cache = []

        return self._depreciation_cache

    def refresh_caches(self):
        """Force-refresh both caches (call after admin edits rates/prices)."""
        self._load_crsp_catalog(force_refresh=True)
        self._load_depreciation_brackets(force_refresh=True)

    # ============================================================
    # FUZZY MATCHING
    # ============================================================

    @staticmethod
    def _build_search_string(make: str, model: str, variant: Optional[str] = None) -> str:
        parts = [make or "", model or ""]
        if variant:
            parts.append(variant)
        return " ".join(p.strip() for p in parts if p).strip()

    @staticmethod
    def _record_search_string(record: Dict[str, Any]) -> str:
        parts = [
            record.get("make") or "",
            record.get("model") or "",
            record.get("variant") or "",
        ]
        return " ".join(p.strip() for p in parts if p).strip()

    def find_crsp_match(
        self,
        make: str,
        model: str,
        variant: Optional[str] = None,
        engine_size_cc: Optional[int] = None,
        fuel_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fuzzy-match a vehicle against the CRSP catalog.

        Strategy:
          1. Narrow candidates by make (case-insensitive exact/contains)
             where possible, to keep fuzzy matching precise and fast.
          2. Fuzzy match on "make model variant" string using rapidfuzz.
          3. If multiple close matches, prefer the one with matching
             engine_size_cc / fuel_type as tie-breakers.

        Returns the matched record with an added "_match_score" key,
        or None if no candidate clears match_threshold.
        """
        catalog = self._load_crsp_catalog()
        if not catalog:
            return None

        make_norm = (make or "").strip().lower()

        # Narrow by make first when possible (cheap pre-filter)
        candidates = [
            r for r in catalog
            if (r.get("make") or "").strip().lower() == make_norm
        ]
        if not candidates:
            # Fall back to full catalog in case of make-name variance
            candidates = catalog

        search_str = self._build_search_string(make, model, variant)
        choices = {
            idx: self._record_search_string(r)
            for idx, r in enumerate(candidates)
        }

        match = process.extractOne(
            search_str,
            choices,
            scorer=fuzz.token_sort_ratio,
        )

        if not match:
            return None

        matched_str, score, idx = match

        if score < self.match_threshold:
            return None

        best_matches = [
            (i, s) for i, (m, s, i) in
            [(i, (m, s, i)) for i, m in choices.items()
             for s in [fuzz.token_sort_ratio(search_str, m)]]
            if s >= score - 5  # near-tied candidates
        ]

        chosen_idx = idx
        if engine_size_cc and len(best_matches) > 1:
            for i, _ in best_matches:
                candidate_engine = candidates[i].get("engine_size_cc")
                if candidate_engine and abs(candidate_engine - engine_size_cc) <= 100:
                    chosen_idx = i
                    break

        record = dict(candidates[chosen_idx])
        record["_match_score"] = score
        return record

    # ============================================================
    # DEPRECIATION LOOKUP
    # ============================================================

    @staticmethod
    def calculate_age_years(year_of_manufacture: int, as_of: Optional[datetime] = None) -> int:
        """Vehicle age in whole years, matching KRA's calendar-year convention."""
        as_of = as_of or datetime.now()
        return max(0, as_of.year - year_of_manufacture)

    def get_depreciation_rate(self, age_years: int) -> Optional[Dict[str, Any]]:
        """
        Find the depreciation bracket matching this vehicle age.

        Returns the matching row (with 'depreciation_rate' as a
        decimal, e.g. 0.35) or None if no bracket covers this age —
        callers MUST treat None as "cannot value this vehicle yet",
        not as "0% depreciation".
        """
        brackets = self._load_depreciation_brackets()

        for bracket in brackets:
            age_min = bracket.get("age_min_years")
            age_max = bracket.get("age_max_years")

            if age_min is None:
                continue

            # age_max = None means "this bracket and older" (e.g. 8+ years)
            if age_max is None:
                if age_years >= age_min:
                    return bracket
            elif age_min <= age_years <= age_max:
                return bracket

        return None

    # ============================================================
    # PUBLIC API
    # ============================================================

    def get_base_price(
        self,
        make: str,
        model: str,
        year: int,
        variant: Optional[str] = None,
        engine_size_cc: Optional[int] = None,
        fuel_type: Optional[str] = None,
        as_of: Optional[datetime] = None,
    ) -> BasePriceResult:
        """
        Resolve base (post-depreciation) value for a vehicle.

        This is the single entry point other services should call.
        """
        if not make or not model or not year:
            return BasePriceResult(
                matched=False,
                error="make, model, and year are required",
            )

        record = self.find_crsp_match(
            make=make,
            model=model,
            variant=variant,
            engine_size_cc=engine_size_cc,
            fuel_type=fuel_type,
        )

        if not record:
            return BasePriceResult(
                matched=False,
                error=f"No CRSP match found for '{make} {model} {variant or ''}'".strip(),
            )

        crsp_price = record.get("crsp_price")
        if not crsp_price:
            return BasePriceResult(
                matched=True,
                match_confidence=record.get("_match_score"),
                matched_record=record,
                error="Matched CRSP record has no price value",
            )

        age_years = self.calculate_age_years(year, as_of=as_of)
        bracket = self.get_depreciation_rate(age_years)

        if not bracket:
            return BasePriceResult(
                matched=True,
                crsp_price=crsp_price,
                vehicle_age_years=age_years,
                match_confidence=record.get("_match_score"),
                matched_record=record,
                error=(
                    f"No depreciation bracket configured for age={age_years} years. "
                    f"depreciation_rates table needs a bracket covering this age — "
                    f"verify against the current KRA gazette before adding it."
                ),
            )

        depreciation_rate = bracket.get("depreciation_rate")
        if depreciation_rate is None:
            return BasePriceResult(
                matched=True,
                crsp_price=crsp_price,
                vehicle_age_years=age_years,
                match_confidence=record.get("_match_score"),
                matched_record=record,
                error="Matched depreciation bracket has no rate value",
            )

        depreciated_value = round(crsp_price * (1 - depreciation_rate))

        warning = None
        match_score = record.get("_match_score", 0)
        if match_score < 85:
            warning = (
                f"Low-confidence CRSP match ({match_score:.0f}%) — "
                f"verify '{record.get('make')} {record.get('model')} "
                f"{record.get('variant', '')}' is correct for the input vehicle."
            )

        return BasePriceResult(
            matched=True,
            crsp_price=crsp_price,
            depreciated_value=depreciated_value,
            depreciation_rate=depreciation_rate,
            vehicle_age_years=age_years,
            match_confidence=match_score,
            matched_record={
                "id": record.get("id"),
                "make": record.get("make"),
                "model": record.get("model"),
                "variant": record.get("variant"),
                "engine_size_cc": record.get("engine_size_cc"),
                "fuel_type": record.get("fuel_type"),
                "source_year": record.get("source_year"),
            },
            warning=warning,
        )
