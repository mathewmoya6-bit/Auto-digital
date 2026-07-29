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

Uses the shared Supabase client instance from `app.core.database`, matching
main.py's own `from app.core.database import supabase` pattern.

Usage:
    from services.vehicle_matcher import VehicleMatcher, MatchResult

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
from dataclasses import dataclass, field
from difflib import get_close_matches, SequenceMatcher
from typing import Any, Optional, Dict, List, Tuple
from datetime import datetime, timezone
from functools import lru_cache

from app.core.database import supabase
from app.core.config import settings

try:
    from services.scraper_logger import get_logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
else:
    logger = get_logger(__name__)

# ─── Constants ──────────────────────────────────────────────────────

# Below this similarity ratio, we don't trust a fuzzy match at all.
MIN_MATCH_CONFIDENCE = 0.72

# High confidence threshold for auto-accept without manual review
HIGH_CONFIDENCE_THRESHOLD = 0.85

# Maximum number of matches to consider in fuzzy matching
MAX_FUZZY_MATCHES = 1


# ─── Helpers ──────────────────────────────────────────────────────

def _normalize(text: Optional[str]) -> str:
    """
    Lowercase, strip punctuation/extra whitespace for comparison.
    Handles common vehicle naming variations.
    """
    if not text:
        return ""
    
    text = str(text).lower().strip()
    
    # Remove common suffixes that cause mismatches
    suffixes_to_remove = [
        r"\b(?:ltd|limited|sport|turbo|hybrid|ev|electric|diesel|petrol|auto|manual|awd|fwd|rwd)\b"
    ]
    for suffix in suffixes_to_remove:
        text = re.sub(suffix, "", text)
    
    # Replace common abbreviations
    replacements = {
        r"\b(?:4x4|4wd)\b": "four wheel drive",
        r"\b(?:2wd)\b": "two wheel drive",
        r"\b(?:v6|v-6)\b": "v6",
        r"\b(?:v8|v-8)\b": "v8",
        r"\b(?:i4|i-4)\b": "i4",
        r"\b(?:mt)\b": "manual",
        r"\b(?:at)\b": "automatic",
        r"\b(?:amg)\b": "amg",
        r"\b(?:m-sport|msport)\b": "m sport",
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)
    
    # Remove punctuation and extra spaces
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    
    return text.strip()


def _extract_year(text: Optional[str]) -> Optional[int]:
    """Extract year from text if present."""
    if not text:
        return None
    
    match = re.search(r"\b(19|20)\d{2}\b", str(text))
    if match:
        return int(match.group(0))
    return None


def _normalize_variant_name(name: str) -> str:
    """
    Normalize variant name by removing year, engine size, and common patterns.
    This helps match variants that have slightly different formatting.
    """
    if not name:
        return ""
    
    text = str(name).lower().strip()
    
    # Remove year patterns
    text = re.sub(r"\b(19|20)\d{2}\b", "", text)
    
    # Remove engine size patterns
    text = re.sub(r"\b\d+\.?\d*\s*(?:l|cc|liter|litre)\b", "", text)
    
    # Remove common separator patterns
    text = re.sub(r"[\(\)\[\]\{\}\-\_]", " ", text)
    
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    
    return text.strip()


# ─── Models ──────────────────────────────────────────────────────

@dataclass
class MatchResult:
    """Result of a vehicle matching attempt."""
    
    ok: bool
    type_id: Optional[str] = None
    make_id: Optional[str] = None
    model_id: Optional[str] = None
    variant_id: Optional[str] = None
    matched_on: Optional[str] = None  # "variant" | "model" | "make" | "year" | None
    confidence: float = 0.0
    reason: Optional[str] = None  # populated when ok is False
    
    # Additional metadata
    matched_make: Optional[str] = None
    matched_model: Optional[str] = None
    matched_variant: Optional[str] = None
    match_metadata: Dict[str, Any] = field(default_factory=dict)
    matched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "ok": self.ok,
            "type_id": self.type_id,
            "make_id": self.make_id,
            "model_id": self.model_id,
            "variant_id": self.variant_id,
            "matched_on": self.matched_on,
            "confidence": self.confidence,
            "reason": self.reason,
            "matched_make": self.matched_make,
            "matched_model": self.matched_model,
            "matched_variant": self.matched_variant,
            "match_metadata": self.match_metadata,
            "matched_at": self.matched_at,
        }
    
    def is_high_confidence(self) -> bool:
        """Check if match has high confidence."""
        return self.ok and self.confidence >= HIGH_CONFIDENCE_THRESHOLD
    
    def needs_review(self) -> bool:
        """Check if match needs manual review."""
        return self.ok and self.confidence < HIGH_CONFIDENCE_THRESHOLD


# ─── VehicleMatcher Class ──────────────────────────────────────

class VehicleMatcher:
    """
    Matches scraped vehicle listings to catalog IDs.
    
    Thread-safe and uses caching for performance.
    """
    
    _instance = None
    _lock = None  # Will be initialized lazily
    
    def __new__(cls):
        """Singleton pattern to avoid reloading catalog on every instance."""
        if cls._instance is None:
            import threading
            cls._lock = threading.Lock()
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize the matcher. Only runs once due to singleton."""
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.supabase = supabase
        self._makes: List[Dict] = []
        self._models: List[Dict] = []
        self._variants: List[Dict] = []
        
        # Normalized-name -> row lookup, built by refresh()
        self._make_index: Dict[str, Dict] = {}
        self._models_by_make: Dict[str, List[Dict]] = {}
        self._variants_by_model: Dict[str, List[Dict]] = {}
        self._variants_by_name: Dict[str, List[Dict]] = {}
        
        # Cache for frequent lookups
        self._cache: Dict[str, MatchResult] = {}
        self._cache_ttl = 300  # 5 minutes
        self._cache_hits = 0
        self._cache_misses = 0
        
        self._initialized = True
        self.refresh()
    
    def _get_cache_key(self, make: str, model: str, variant: str, year: int) -> str:
        """Generate cache key for a match request."""
        return f"{make}|{model}|{variant}|{year}".lower()
    
    def _get_cached(self, key: str) -> Optional[MatchResult]:
        """Get cached match result if valid."""
        if key in self._cache:
            entry = self._cache[key]
            if (datetime.now(timezone.utc) - entry["timestamp"]).total_seconds() < self._cache_ttl:
                self._cache_hits += 1
                return entry["result"]
            else:
                del self._cache[key]
        self._cache_misses += 1
        return None
    
    def _set_cache(self, key: str, result: MatchResult):
        """Cache a match result."""
        self._cache[key] = {
            "result": result,
            "timestamp": datetime.now(timezone.utc)
        }
        # Limit cache size
        if len(self._cache) > 1000:
            # Remove oldest entries
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k]["timestamp"]
            )
            for key_to_remove in sorted_keys[:100]:
                del self._cache[key_to_remove]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._cache_hits + self._cache_misses
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": (self._cache_hits / total * 100) if total > 0 else 0,
            "cached_items": len(self._cache)
        }

    def refresh(self) -> None:
        """(Re)load the full catalog from Supabase. Call this if the
        catalog changes mid-process; otherwise it only runs once at init."""
        try:
            self._makes = self.supabase.table("vehicle_makes").select("*").execute().data or []
            self._models = self.supabase.table("vehicle_models").select("*").execute().data or []
            self._variants = self.supabase.table("vehicle_variants").select("*").execute().data or []

            # Build indexes
            self._make_index = {_normalize(m["name"]): m for m in self._makes}

            self._models_by_make = {}
            for model in self._models:
                self._models_by_make.setdefault(model["make_id"], []).append(model)

            self._variants_by_model = {}
            self._variants_by_name = {}
            for variant in self._variants:
                self._variants_by_model.setdefault(variant["model_id"], []).append(variant)
                variant_name = _normalize_variant_name(variant.get("name", ""))
                if variant_name:
                    self._variants_by_name.setdefault(variant_name, []).append(variant)

            # Clear cache on refresh
            self._cache.clear()

            logger.info(
                "Vehicle catalog loaded: %d makes, %d models, %d variants",
                len(self._makes), len(self._models), len(self._variants),
            )

        except Exception as e:
            logger.error(f"Failed to refresh vehicle catalog: {e}")
            raise

    @staticmethod
    def _best_match(
        target: str,
        candidates: Dict[str, Any],
        cutoff: float = MIN_MATCH_CONFIDENCE
    ) -> Optional[Tuple[Any, float]]:
        """
        Find the best fuzzy match for `target` among normalized-name keys
        in `candidates`. Returns (row, confidence) or None.
        """
        if not target or not candidates:
            return None

        # Exact match
        if target in candidates:
            return candidates[target], 1.0

        # Try partial matching (e.g., "corolla" matches "corolla 1.8")
        for key, value in candidates.items():
            if target in key or key in target:
                return value, 0.85

        # Fuzzy match with get_close_matches
        close = get_close_matches(target, candidates.keys(), n=MAX_FUZZY_MATCHES, cutoff=cutoff)
        if not close:
            return None

        best_key = close[0]
        ratio = SequenceMatcher(None, target, best_key).ratio()
        
        # Boost if the match is a prefix
        if best_key.startswith(target) or target.startswith(best_key):
            ratio = max(ratio, 0.85)
        
        return candidates[best_key], ratio

    def match_listing(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        variant: Optional[str] = None,
        year: Optional[int] = None,
        use_cache: bool = True
    ) -> MatchResult:
        """
        Match a vehicle listing to catalog IDs.
        
        Args:
            make: Vehicle make (e.g., "Toyota")
            model: Vehicle model (e.g., "Corolla")
            variant: Vehicle variant/trim (e.g., "1.8 GLi")
            year: Vehicle year
            use_cache: Whether to use cached results
            
        Returns:
            MatchResult with matched IDs and confidence
        """
        # Generate cache key
        cache_key = self._get_cache_key(
            make or "", model or "", variant or "", year or 0
        )
        
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached:
                return cached

        make_norm = _normalize(make)
        model_norm = _normalize(model)
        variant_norm = _normalize(variant)

        # ─── Step 1: Match Make ──────────────────────────────────────
        make_match = self._best_match(make_norm, self._make_index)
        if not make_match:
            result = MatchResult(
                ok=False,
                reason=f"No catalog match for make='{make}'",
                confidence=0.0
            )
            if use_cache:
                self._set_cache(cache_key, result)
            return result
        
        make_row, make_conf = make_match
        matched_make = make_row.get("name")

        # ─── Step 2: Match Model ──────────────────────────────────────
        candidate_models = self._models_by_make.get(make_row["id"], [])
        model_index = {_normalize(m["name"]): m for m in candidate_models}
        model_match = self._best_match(model_norm, model_index)
        
        if not model_match:
            result = MatchResult(
                ok=False,
                type_id=make_row.get("type_id"),
                make_id=make_row["id"],
                matched_make=matched_make,
                matched_on="make",
                confidence=make_conf,
                reason=f"Make '{make}' matched but no model match for '{model}'",
            )
            if use_cache:
                self._set_cache(cache_key, result)
            return result
        
        model_row, model_conf = model_match
        matched_model = model_row.get("name")

        result = MatchResult(
            ok=True,
            type_id=make_row.get("type_id"),
            make_id=make_row["id"],
            model_id=model_row["id"],
            matched_make=matched_make,
            matched_model=matched_model,
            matched_on="model",
            confidence=min(make_conf, model_conf),
        )

        # ─── Step 3: Match Variant (if provided) ──────────────────────
        if variant:
            candidate_variants = self._variants_by_model.get(model_row["id"], [])
            
            # Build variant index with multiple strategies
            variant_index = {}
            for v in candidate_variants:
                # Primary: normalized name
                v_name = _normalize(v.get("name", ""))
                if v_name:
                    variant_index[v_name] = v
                
                # Secondary: normalized variant name (without year/engine)
                v_name_clean = _normalize_variant_name(v.get("name", ""))
                if v_name_clean and v_name_clean != v_name:
                    variant_index[v_name_clean] = v

            variant_match = self._best_match(variant_norm, variant_index)
            
            if variant_match:
                variant_row, variant_conf = variant_match
                matched_variant = variant_row.get("name")
                
                # Check year agreement
                if year and "year" in variant_row and variant_row.get("year"):
                    if variant_row["year"] != year:
                        variant_conf *= 0.85  # Reduce confidence for year mismatch
                        logger.debug(
                            f"Year mismatch for {matched_variant}: catalog {variant_row['year']} vs listing {year}"
                        )
                
                result.variant_id = variant_row["id"]
                result.matched_variant = matched_variant
                result.matched_on = "variant"
                result.confidence = min(result.confidence, variant_conf)
            else:
                # Model-level fallback
                result.reason = f"Model matched but no variant match for '{variant}'"

        # ─── Step 4: Year validation (if year provided) ──────────────
        if year and result.ok:
            # Check if year is within reasonable range for the model
            model_years = []
            for v in self._variants_by_model.get(model_row["id"], []):
                if v.get("year"):
                    model_years.append(v["year"])
            
            if model_years:
                min_year = min(model_years)
                max_year = max(model_years)
                if year < min_year - 2 or year > max_year + 2:
                    result.confidence *= 0.8
                    logger.debug(
                        f"Year {year} outside range for {matched_model}: {min_year}-{max_year}"
                    )

        # ─── Step 5: Log and cache ────────────────────────────────────
        if use_cache:
            self._set_cache(cache_key, result)
        
        logger.debug(
            f"Match result: {result.matched_on} ({result.confidence:.2f}) "
            f"for {make} {model} {variant} {year}"
        )
        
        return result

    def match_scraped(self, listing: Dict[str, Any]) -> MatchResult:
        """
        Convenience wrapper matching the raw dict shape scrapers emit.
        Adjust the key names here if your scraper classes use different
        field names (e.g. 'trim' vs 'variant').
        """
        # Extract year from listing
        year = listing.get("year")
        if not year:
            # Try to extract year from text fields
            year = _extract_year(listing.get("year_text") or listing.get("description") or "")
        
        return self.match_listing(
            make=listing.get("make"),
            model=listing.get("model"),
            variant=listing.get("variant") or listing.get("trim"),
            year=year,
        )

    def batch_match(
        self,
        listings: List[Dict[str, Any]],
        use_cache: bool = True
    ) -> List[MatchResult]:
        """
        Match multiple listings in batch.
        
        Args:
            listings: List of listing dictionaries
            use_cache: Whether to use cached results
            
        Returns:
            List of MatchResult objects
        """
        results = []
        for listing in listings:
            result = self.match_scraped(listing, use_cache)
            results.append(result)
        return results

    def get_match_summary(self, results: List[MatchResult]) -> Dict[str, Any]:
        """
        Get summary statistics for a batch of match results.
        """
        if not results:
            return {"total": 0, "ok": 0, "variant_matches": 0, "model_matches": 0}
        
        total = len(results)
        ok = sum(1 for r in results if r.ok)
        variant_matches = sum(1 for r in results if r.matched_on == "variant")
        model_matches = sum(1 for r in results if r.matched_on == "model")
        high_confidence = sum(1 for r in results if r.is_high_confidence())
        needs_review = sum(1 for r in results if r.needs_review())
        
        avg_confidence = sum(r.confidence for r in results if r.ok) / ok if ok > 0 else 0
        
        return {
            "total": total,
            "ok": ok,
            "variant_matches": variant_matches,
            "model_matches": model_matches,
            "high_confidence": high_confidence,
            "needs_review": needs_review,
            "avg_confidence": round(avg_confidence, 2),
            "cache_stats": self.get_cache_stats()
        }


# ─── Singleton ─────────────────────────────────────────────────────

_vehicle_matcher: Optional[VehicleMatcher] = None


def get_vehicle_matcher() -> VehicleMatcher:
    """Get or create VehicleMatcher singleton."""
    global _vehicle_matcher
    if _vehicle_matcher is None:
        _vehicle_matcher = VehicleMatcher()
    return _vehicle_matcher


# ─── Export ─────────────────────────────────────────────────────

__all__ = [
    "VehicleMatcher",
    "MatchResult",
    "get_vehicle_matcher",
    "MIN_MATCH_CONFIDENCE",
    "HIGH_CONFIDENCE_THRESHOLD",
]
