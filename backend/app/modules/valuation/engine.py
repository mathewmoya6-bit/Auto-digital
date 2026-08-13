"""
app/modules/valuation/engine.py

Pure calculation logic — no I/O, no Supabase, fully unit-testable.
Takes a CRSP base price (if found) plus vehicle attributes and returns a
fully-adjusted valuation.

Mirrors the KRA-style age-bracket depreciation approach used in
baseprice_engine.py. The "over 7 years" bracket is a flat cap carried
over from that module and is still flagged there as requiring gazette
verification before being treated as authoritative — same caveat
applies here.

When no CRSP match exists, the engine falls back to a market-anchor
heuristic (MARKET_ANCHOR_KES_PER_CC) so the calculator never hard-fails
just because a trim isn't in the CRSP table yet — it just reports a
lower confidence score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


# ─────────────────────────────────────────────────────────────────────────
# KRA-style age-bracket depreciation
# (rate applied to CRSP/base price; TODO gazette-verify the >7yr cap)
# ─────────────────────────────────────────────────────────────────────────
AGE_DEPRECIATION_BRACKETS: list[tuple[int, int, float]] = [
    # (min_age_years, max_age_years_inclusive, rate)
    (0, 0, 0.05),
    (1, 1, 0.15),
    (2, 2, 0.23),
    (3, 3, 0.30),
    (4, 4, 0.37),
    (5, 5, 0.43),
    (6, 6, 0.49),
    (7, 999, 0.55),  # flat cap beyond 7 years — needs gazette verification
]

# Straight-line mileage adjustment: expected km/year band, +/- a capped
# fraction outside that band. Deliberately conservative vs. price swings.
EXPECTED_KM_PER_YEAR = 15_000
MILEAGE_ADJUSTMENT_PER_10K_OVER = -0.01   # -1% per 10,000km over expected
MILEAGE_ADJUSTMENT_PER_10K_UNDER = 0.006  # +0.6% per 10,000km under expected
MILEAGE_ADJUSTMENT_CAP = 0.25             # +/-25% max

CONDITION_FACTORS = {
    "excellent": 1.08,
    "very_good": 1.03,
    "good": 1.00,
    "fair": 0.90,
    "poor": 0.75,
}

ACCIDENT_FACTORS = {
    "none": 1.00,
    "minor": 0.94,
    "major": 0.82,
    "total_loss": 0.55,
}

OWNER_FACTORS = {
    0: 1.03,  # brand new / never registered to a previous owner
    1: 1.00,
    2: 0.97,
    3: 0.94,
    4: 0.91,
}
OWNER_FACTOR_FLOOR = 0.88  # 5+ owners

LOCATION_FACTORS = {
    "nairobi": 1.02,
    "mombasa": 1.00,
    "kiambu": 1.01,
    "kajiado": 1.00,
    "nakuru": 0.98,
    "kisumu": 0.97,
    "eldoret": 0.97,
    "thika": 0.99,
    "machakos": 0.98,
    "meru": 0.96,
    "nyeri": 0.97,
    "embu": 0.96,
    "malindi": 0.97,
    "nanyuki": 0.96,
    "other": 0.95,
}

FUEL_TYPE_FACTORS = {
    "diesel": 1.02,
    "petrol": 1.00,
    "lpg": 0.97,
    "electric": 1.05,
}

TRANSMISSION_FACTORS = {
    "automatic": 1.03,
    "cvt": 1.00,
    "amt": 0.98,
    "manual": 0.96,
}

# Used only when no CRSP match is found at all.
MARKET_ANCHOR_KES_PER_CC = 950.0
MARKET_ANCHOR_MIN_KES = 400_000.0


@dataclass
class ValuationInput:
    make: str
    model: str
    trim: str | None
    year: int
    mileage: float
    condition: str
    accident_history: str
    previous_owners: int
    location: str
    fuel_type: str
    transmission: str
    vehicle_type: str
    profit_margin_pct: float
    engine_capacity_cc: float | None = None
    crsp_base_price_kes: float | None = None
    photos_flagged: bool = False


@dataclass
class ValuationOutput:
    estimated_vehicle_value: float
    recommended_selling_price: float | None
    confidence_score: float
    vehicle_age: int
    depreciation_rate: float
    depreciation_amount: float
    mileage_adjustment: float
    adjustments: dict[str, float] = field(default_factory=dict)
    crsp_used: bool = False
    crsp_variance_pct: float | None = None


class ValuationEngine:
    """Stateless — safe to instantiate once and reuse (see service.py)."""

    def __init__(self, as_of: date | None = None):
        self._as_of = as_of or date.today()

    # ── public API ──────────────────────────────────────────────────

    def calculate(self, inp: ValuationInput) -> ValuationOutput:
        age = self._vehicle_age(inp.year)
        depreciation_rate = self._depreciation_rate(age)

        base_price, crsp_used = self._resolve_base_price(inp)
        after_depreciation = base_price * (1 - depreciation_rate)
        depreciation_amount = base_price - after_depreciation

        mileage_adj = self._mileage_adjustment(inp.mileage, age)
        value = after_depreciation * (1 + mileage_adj)

        adjustments = self._attribute_adjustments(inp)
        for factor in adjustments.values():
            value *= factor

        # Photo-authenticity flag doesn't move the number — it's a
        # disclosure concern, not a pricing one — but we shave a little
        # off confidence for it (handled in _confidence_score).
        confidence = self._confidence_score(
            crsp_used=crsp_used,
            has_trim=bool(inp.trim),
            photos_flagged=inp.photos_flagged,
            age=age,
        )

        value = max(value, MARKET_ANCHOR_MIN_KES)
        recommended_selling_price = None
        if inp.profit_margin_pct:
            recommended_selling_price = round(
                value * (1 + inp.profit_margin_pct / 100), -2
            )

        crsp_variance_pct = None
        if crsp_used and inp.crsp_base_price_kes:
            crsp_variance_pct = round(
                (value - inp.crsp_base_price_kes) / inp.crsp_base_price_kes * 100, 1
            )

        return ValuationOutput(
            estimated_vehicle_value=round(value, -2),  # nearest 100 KES
            recommended_selling_price=recommended_selling_price,
            confidence_score=confidence,
            vehicle_age=age,
            depreciation_rate=depreciation_rate,
            depreciation_amount=round(depreciation_amount, 2),
            mileage_adjustment=round(mileage_adj, 4),
            adjustments=adjustments,
            crsp_used=crsp_used,
            crsp_variance_pct=crsp_variance_pct,
        )

    # ── internals ───────────────────────────────────────────────────

    def _vehicle_age(self, year: int) -> int:
        return max(0, self._as_of.year - year)

    def _depreciation_rate(self, age: int) -> float:
        for lo, hi, rate in AGE_DEPRECIATION_BRACKETS:
            if lo <= age <= hi:
                return rate
        return AGE_DEPRECIATION_BRACKETS[-1][2]

    def _resolve_base_price(self, inp: ValuationInput) -> tuple[float, bool]:
        if inp.crsp_base_price_kes and inp.crsp_base_price_kes > 0:
            return inp.crsp_base_price_kes, True

        # Fallback market-anchor estimate when no CRSP line matched.
        cc = inp.engine_capacity_cc or 1500.0
        estimate = max(cc * MARKET_ANCHOR_KES_PER_CC, MARKET_ANCHOR_MIN_KES)
        return estimate, False

    def _mileage_adjustment(self, mileage: float, age: int) -> float:
        expected = EXPECTED_KM_PER_YEAR * max(age, 1)
        delta = mileage - expected
        if delta > 0:
            adj = (delta / 10_000) * MILEAGE_ADJUSTMENT_PER_10K_OVER
        else:
            adj = (abs(delta) / 10_000) * MILEAGE_ADJUSTMENT_PER_10K_UNDER
        return max(-MILEAGE_ADJUSTMENT_CAP, min(MILEAGE_ADJUSTMENT_CAP, adj))

    def _attribute_adjustments(self, inp: ValuationInput) -> dict[str, float]:
        owner_factor = OWNER_FACTORS.get(inp.previous_owners, OWNER_FACTOR_FLOOR)
        return {
            "condition": CONDITION_FACTORS.get(inp.condition, 1.0),
            "accident": ACCIDENT_FACTORS.get(inp.accident_history, 1.0),
            "previous_owners": owner_factor,
            "location": LOCATION_FACTORS.get(inp.location, 0.97),
            "fuel_type": FUEL_TYPE_FACTORS.get(inp.fuel_type, 1.0),
            "transmission": TRANSMISSION_FACTORS.get(inp.transmission, 1.0),
            "vehicle_type": 1.0,  # reserved: no body-style premium data yet
            "market": 1.0,        # reserved: live market-scrape adjustment
        }

    def _confidence_score(
        self, *, crsp_used: bool, has_trim: bool, photos_flagged: bool, age: int
    ) -> float:
        score = 60.0
        if crsp_used:
            score += 25.0
        if has_trim:
            score += 8.0
        if age <= 10:
            score += 5.0
        if photos_flagged:
            score -= 8.0
        return round(max(20.0, min(97.0, score)), 1)
