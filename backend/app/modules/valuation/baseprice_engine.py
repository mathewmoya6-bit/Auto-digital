# app/modules/valuation/baseprice_engine.py
# ================================================================
# Auto-D Kenya - Vehicle Base Price Engine
# ================================================================
#
# `vehicle_base_prices` stores market-derived base prices PER
# MAKE/MODEL/TRIM/YEAR (built from scraped market_listings, with
# sample_size/confidence indicating data quality for that row).
#
# Resolution strategy:
#   1. Fuzzy-match make/model/trim (rapidfuzz) to find the right
#      vehicle family, using vehicle_makes/vehicle_models for
#      canonical IDs where possible.
#   2. If a row exists for the EXACT requested year with acceptable
#      sample_size/confidence -> return it directly. Real scraped
#      market data for that year already reflects true depreciation;
#      no further math needed.
#   3. If no reliable row exists for that year, find the nearest
#      reliable anchor year for the same make/model/trim and
#      EXTRAPOLATE forward or backward using depreciation_rates
#      (joined via vehicle_models.category_id).
#
# ================================================================
# ASSUMPTION FLAGGED FOR VERIFICATION:
# depreciation_rates.year_1..year_6_plus are treated as DECLINING
# BALANCE rates -- each year's percentage is lost from the value
# REMAINING after the prior year, not from the original price.
#   e.g. category with year_1=0.25, year_2=0.20:
#     value_after_y1 = price * (1 - 0.25)
#     value_after_y2 = value_after_y1 * (1 - 0.20)
# This matches the standard shape of real vehicle depreciation
# curves (steep first year, tapering off). If your actual intent
# was straight-line-off-original instead, change
# `_apply_depreciation_curve()` below -- it's isolated in one place.
# Tables were empty when this was written, so this could not be
# verified against existing data or other code. VERIFY BEFORE
# TRUSTING PRODUCTION OUTPUT.
# ================================================================

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz, process

from app.core.database import get_supabase

logger = logging.getLogger(__name__)

DEFAULT_MATCH_THRESHOLD = 72
MIN_RELIABLE_SAMPLE_SIZE = 3
MIN_RELIABLE_CONFIDENCE = 0.5


@dataclass
class BasePriceResult:
    matched: bool
    base_price: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    method: Optional[str] = None  # "exact_year" | "extrapolated"
    anchor_year: Optional[int] = None
    depreciation_applied: Optional[float] = None
    match_confidence: Optional[float] = None
    matched_vehicle: Optional[Dict[str, Any]] = None
    warning: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matched": self.matched,
            "base_price": self.base_price,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "method": self.method,
            "anchor_year": self.anchor_year,
            "depreciation_applied": self.depreciation_applied,
            "match_confidence": self.match_confidence,
            "matched_vehicle": self.matched_vehicle,
            "warning": self.warning,
            "error": self.error,
        }


class BasePriceEngine:

    def __init__(self, match_threshold: int = DEFAULT_MATCH_THRESHOLD):
        self.supabase = get_supabase()
        self.match_threshold = match_threshold

        self._price_rows_cache: Optional[List[Dict[str, Any]]] = None
        self._depreciation_cache: Optional[Dict[int, Dict[str, float]]] = None
        self._model_category_cache: Optional[Dict[int, int]] = None

    # ============================================================
    # CACHE LOADERS
    # ============================================================

    def refresh_caches(self):
        self._load_price_rows(force_refresh=True)
        self._load_depreciation_rates(force_refresh=True)
        self._load_model_categories(force_refresh=True)

    def _load_price_rows(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        if self._price_rows_cache is not None and not force_refresh:
            return self._price_rows_cache
        try:
            result = self.supabase.table("vehicle_base_prices").select("*").execute()
            self._price_rows_cache = result.data or []
            logger.info(f"Loaded {len(self._price_rows_cache)} vehicle_base_prices rows")
        except Exception as e:
            logger.error(f"Failed to load vehicle_base_prices: {e}")
            self._price_rows_cache = []
        return self._price_rows_cache

    def _load_depreciation_rates(self, force_refresh: bool = False) -> Dict[int, Dict[str, float]]:
        """Returns {category_id: {"year_1": 0.25, "year_2": 0.20, ...}}"""
        if self._depreciation_cache is not None and not force_refresh:
            return self._depreciation_cache
        try:
            result = self.supabase.table("depreciation_rates").select("*").execute()
            rows = result.data or []
            self._depreciation_cache = {
                row["category_id"]: {
                    "year_1": row.get("year_1"),
                    "year_2": row.get("year_2"),
                    "year_3": row.get("year_3"),
                    "year_4": row.get("year_4"),
                    "year_5": row.get("year_5"),
                    "year_6_plus": row.get("year_6_plus"),
                }
                for row in rows
                if row.get("category_id") is not None
            }
            logger.info(f"Loaded depreciation rates for {len(self._depreciation_cache)} categories")
        except Exception as e:
            logger.error(f"Failed to load depreciation_rates: {e}")
            self._depreciation_cache = {}
        return self._depreciation_cache

    def _load_model_categories(self, force_refresh: bool = False) -> Dict[int, int]:
        """Returns {model_id: category_id} from vehicle_models."""
        if self._model_category_cache is not None and not force_refresh:
            return self._model_category_cache
        try:
            result = (
                self.supabase
                .table("vehicle_models")
                .select("id, category_id")
                .execute()
            )
            self._model_category_cache = {
                row["id"]: row["category_id"]
                for row in (result.data or [])
                if row.get("category_id") is not None
            }
        except Exception as e:
            logger.error(f"Failed to load vehicle_models categories: {e}")
            self._model_category_cache = {}
        return self._model_category_cache

    # ============================================================
    # FUZZY MATCHING (vehicle family, not year-specific)
    # ============================================================

    @staticmethod
    def _search_string(make: str, model: str, trim: Optional[str] = None) -> str:
        parts = [make or "", model or ""]
        if trim:
            parts.append(trim)
        return " ".join(p.strip() for p in parts if p).strip()

    def _find_family_rows(
        self,
        make: str,
        model: str,
        trim: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Fuzzy-match make/model/trim and return ALL price rows belonging
        to that matched vehicle family (across all years), plus the
        match confidence score.
        """
        rows = self._load_price_rows()
        if not rows:
            return [], 0.0

        make_norm = (make or "").strip().lower()

        # Group rows by (make, model, trim) family so we score each
        # family once, not each individual year-row.
        families: Dict[tuple, List[Dict[str, Any]]] = {}
        for row in rows:
            key = (
                (row.get("make") or "").strip().lower(),
                (row.get("model") or "").strip().lower(),
                (row.get("trim") or "").strip().lower(),
            )
            families.setdefault(key, []).append(row)

        # Prefer exact make match as a pre-filter when possible
        candidate_keys = [k for k in families if k[0] == make_norm] or list(families.keys())

        search_str = self._search_string(make, model, trim)
        choices = {
            key: self._search_string(key[0], key[1], key[2])
            for key in candidate_keys
        }

        match = process.extractOne(search_str, choices, scorer=fuzz.token_sort_ratio)
        if not match:
            return [], 0.0

        _, score, matched_key = match
        if score < self.match_threshold:
            return [], score

        return families[matched_key], score

    # ============================================================
    # DEPRECIATION CURVE
    # ============================================================

    def _get_category_id_for_row(self, row: Dict[str, Any]) -> Optional[int]:
        model_id = row.get("model_id")
        if not model_id:
            return None
        return self._load_model_categories().get(model_id)

    def _apply_depreciation_curve(
        self,
        anchor_price: float,
        category_id: Optional[int],
        years_forward: int,
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Extrapolate anchor_price forward by `years_forward` full years
        using declining-balance depreciation for the given category.

        Returns (extrapolated_price, cumulative_depreciation_fraction),
        or (None, None) if rates aren't available for this category.

        years_forward can be negative to APPRECIATE toward a newer
        anchor year (inverse of the curve) -- used when the only
        reliable anchor is OLDER than the requested year.
        """
        if category_id is None:
            return None, None

        rates = self._load_depreciation_rates().get(category_id)
        if not rates:
            return None, None

        year_keys = ["year_1", "year_2", "year_3", "year_4", "year_5", "year_6_plus"]

        def rate_for_year_index(n: int) -> Optional[float]:
            # n is 1-indexed year of age
            idx = min(n, 6) - 1
            key = year_keys[idx]
            return rates.get(key)

        value = anchor_price
        steps = abs(years_forward)
        direction = 1 if years_forward > 0 else -1

        for step in range(1, steps + 1):
            rate = rate_for_year_index(step)
            if rate is None:
                return None, None
            if direction > 0:
                # Aging forward: value loses `rate` fraction
                value = value * (1 - rate)
            else:
                # Aging backward toward a newer year: invert the loss
                # to recover the pre-depreciation value.
                if rate >= 1:
                    return None, None
                value = value / (1 - rate)

        cumulative_depreciation = 1 - (value / anchor_price) if anchor_price else None
        return round(value), cumulative_depreciation

    # ============================================================
    # PUBLIC API
    # ============================================================

    def get_base_price(
        self,
        make: str,
        model: str,
        year: int,
        trim: Optional[str] = None,
        engine_size: Optional[float] = None,
        fuel_type: Optional[str] = None,
    ) -> BasePriceResult:
        if not make or not model or not year:
            return BasePriceResult(matched=False, error="make, model, and year are required")

        family_rows, match_score = self._find_family_rows(make, model, trim)

        if not family_rows:
            return BasePriceResult(
                matched=False,
                match_confidence=match_score,
                error=f"No base price data found for '{make} {model} {trim or ''}'".strip(),
            )

        # Optional narrowing by engine_size/fuel_type when multiple trims matched
        if engine_size:
            engine_filtered = [
                r for r in family_rows
                if r.get("engine_size") and abs(float(r["engine_size"]) - engine_size) <= 0.2
            ]
            if engine_filtered:
                family_rows = engine_filtered

        if fuel_type:
            fuel_filtered = [
                r for r in family_rows
                if (r.get("fuel_type") or "").strip().lower() == fuel_type.strip().lower()
            ]
            if fuel_filtered:
                family_rows = fuel_filtered

        # 1. Exact year match with reliable data
        exact_rows = [r for r in family_rows if r.get("year") == year]
        reliable_exact = [
            r for r in exact_rows
            if (r.get("sample_size") or 0) >= MIN_RELIABLE_SAMPLE_SIZE
            and (r.get("confidence") or 0) >= MIN_RELIABLE_CONFIDENCE
        ]

        if reliable_exact:
            row = max(reliable_exact, key=lambda r: r.get("confidence") or 0)
            return BasePriceResult(
                matched=True,
                base_price=row.get("base_price"),
                min_price=row.get("min_price"),
                max_price=row.get("max_price"),
                method="exact_year",
                anchor_year=year,
                match_confidence=match_score,
                matched_vehicle=self._summarize_row(row),
            )

        # 2. No reliable exact-year row -> find nearest reliable anchor year
        reliable_rows = [
            r for r in family_rows
            if r.get("year") and r.get("base_price")
            and (r.get("sample_size") or 0) >= MIN_RELIABLE_SAMPLE_SIZE
            and (r.get("confidence") or 0) >= MIN_RELIABLE_CONFIDENCE
        ]

        if not reliable_rows:
            # Fall back to ANY row with a price, even low-confidence,
            # rather than returning nothing -- but flag it clearly.
            any_rows = [r for r in family_rows if r.get("year") and r.get("base_price")]
            if not any_rows:
                return BasePriceResult(
                    matched=True,
                    match_confidence=match_score,
                    error="Matched vehicle family but no priced rows exist for it yet",
                )
            anchor = min(any_rows, key=lambda r: abs(r["year"] - year))
            warning = (
                f"No reliably-sampled data for this vehicle at all — using low-confidence "
                f"anchor year {anchor['year']} (sample_size={anchor.get('sample_size')}, "
                f"confidence={anchor.get('confidence')}). Treat this valuation with caution."
            )
        else:
            anchor = min(reliable_rows, key=lambda r: abs(r["year"] - year))
            warning = None

        years_diff = year - anchor["year"]

        if years_diff == 0:
            return BasePriceResult(
                matched=True,
                base_price=anchor.get("base_price"),
                min_price=anchor.get("min_price"),
                max_price=anchor.get("max_price"),
                method="exact_year",
                anchor_year=anchor["year"],
                match_confidence=match_score,
                matched_vehicle=self._summarize_row(anchor),
                warning=warning or "Low-confidence source data for this exact year.",
            )

        category_id = self._get_category_id_for_row(anchor)
        extrapolated_price, cumulative_dep = self._apply_depreciation_curve(
            anchor_price=float(anchor["base_price"]),
            category_id=category_id,
            years_forward=years_diff,
        )

        if extrapolated_price is None:
            return BasePriceResult(
                matched=True,
                base_price=anchor.get("base_price"),
                anchor_year=anchor["year"],
                match_confidence=match_score,
                matched_vehicle=self._summarize_row(anchor),
                error=(
                    f"No depreciation rates configured for this vehicle's category "
                    f"(category_id={category_id}) — cannot extrapolate from anchor year "
                    f"{anchor['year']} to requested year {year}."
                ),
            )

        return BasePriceResult(
            matched=True,
            base_price=extrapolated_price,
            method="extrapolated",
            anchor_year=anchor["year"],
            depreciation_applied=cumulative_dep,
            match_confidence=match_score,
            matched_vehicle=self._summarize_row(anchor),
            warning=warning or (
                f"Extrapolated from {anchor['year']} data — no direct market data for {year}."
            ),
        )

    @staticmethod
    def _summarize_row(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": row.get("id"),
            "make": row.get("make"),
            "model": row.get("model"),
            "trim": row.get("trim"),
            "year": row.get("year"),
            "engine_size": row.get("engine_size"),
            "fuel_type": row.get("fuel_type"),
            "sample_size": row.get("sample_size"),
            "confidence": row.get("confidence"),
            "source": row.get("source"),
        }
