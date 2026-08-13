"""
services/valuation_service.py

Business logic for vehicle valuation. Wraps the existing Postgres
function `calculate_vehicle_valuation` (already deployed in Supabase,
confirmed working against real data) and reshapes its flat result row
into the nested JSON structure the "Instant Value Check" frontend
expects from POST /api/v1/valuation/calculate:

    {
      "success": true,
      "data": {
        "vehicle": {
          "make": ..., "model": ..., "trim": ..., "year": ...,
          "mileage": ..., "location": ..., "condition": ...,
          "fuel_type": ..., "transmission": ..., "engine_capacity": ...
        },
        "valuation": {
          "estimated_vehicle_value": ...,
          "recommended_selling_price": ...,
          "confidence_score": ...
        },
        "analysis": {
          "adjustments": {
            "mileage": ..., "condition": ..., "accident": ...,
            "location": ..., "market": ...
          },
          "depreciation_rate": ...,
          "depreciation_amount": ...,
          "mileage_adjustment": ...,
          "vehicle_age": ...
        },
        "report": { "report_number": "..." }
      }
    }

ASSUMPTIONS — adjust to match your actual project if different:
  1. A Supabase client is reachable via `get_supabase()` (see the
     import below). Swap this for however your project actually
     wires up the Supabase / DB client.
  2. `vehicle_crsp` (or the `vehicle_crsp_lookup` view your frontend
     already queries) can be filtered by make / model / trim_level /
     manufacture_year to resolve a single `crsp_id`, since the SQL
     function takes `p_vehicle_crsp_id` rather than make/model/trim
     strings directly.
  3. The SQL function's `p_condition_name` / `p_accident_status` /
     `p_location_name` args are UPPERCASE enum-like strings (matches
     your tested example: 'GOOD', 'NONE', 'NAIROBI').
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

# TODO: point this at wherever your project actually creates its
# Supabase client (service-role client, since this runs server-side).
from app.db import get_supabase  # noqa: F401  (placeholder import)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# Request / response models
# ─────────────────────────────────────────────────────────────────

class ValuationRequest(BaseModel):
    """Matches the `formData` payload built by the frontend's
    App.calculateValuation()."""

    make: str
    model: str
    trim: str
    year: int
    mileage: float = Field(ge=0)
    condition: str = "good"
    accident_history: str = "none"
    previous_owners: int = 1
    location: str = "nairobi"
    fuel_type: str = "petrol"
    transmission: str = "automatic"
    vehicle_type: str = "sedan"
    profit_margin: float = Field(default=0, ge=0, le=100)
    engine_capacity: Optional[str] = None
    crsp_kes: Optional[float] = None  # informational only; not sent to the SQL fn

    @field_validator("make", "model", "trim", "location", "condition", "accident_history")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


CONDITION_MAP = {
    "excellent": "EXCELLENT",
    "very_good": "VERY_GOOD",
    "good": "GOOD",
    "fair": "FAIR",
    "poor": "POOR",
}

ACCIDENT_MAP = {
    "none": "NONE",
    "minor": "MINOR",
    "major": "MAJOR",
    "total_loss": "TOTAL_LOSS",
}


class ValuationError(Exception):
    """Raised for any failure in the valuation pipeline; the router
    turns this into an appropriate HTTP response."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ─────────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────────

class ValuationService:
    def __init__(self, supabase):
        self.supabase = supabase

    # ---- crsp lookup -------------------------------------------------

    async def _resolve_crsp_id(self, req: ValuationRequest) -> tuple[int, dict[str, Any]]:
        """Find the vehicle_crsp row matching make/model/trim/year.

        Falls back through progressively looser filters (drop trim,
        then pick the closest year) since real-world trim strings and
        CRSP schedule years don't always line up exactly.
        """
        query = (
            self.supabase.table("vehicle_crsp")
            .select("crsp_id, make, model, trim_level, manufacture_year, crsp_year, crsp_kes")
            .ilike("make", req.make)
            .ilike("model", req.model)
        )
        res = query.execute()
        rows = res.data or []

        if not rows:
            raise ValuationError(
                f"No CRSP schedule found for {req.make} {req.model}", status_code=404
            )

        # Prefer an exact trim + year match
        exact = [
            r for r in rows
            if (r.get("trim_level") or "").strip().lower() == req.trim.strip().lower()
            and int(r.get("manufacture_year") or r.get("crsp_year") or -1) == req.year
        ]
        if exact:
            return exact[0]["crsp_id"], exact[0]

        # Next: exact trim, closest year
        by_trim = [
            r for r in rows
            if (r.get("trim_level") or "").strip().lower() == req.trim.strip().lower()
        ]
        candidates = by_trim or rows
        best = min(
            candidates,
            key=lambda r: abs(int(r.get("manufacture_year") or r.get("crsp_year") or 0) - req.year),
        )
        return best["crsp_id"], best

    # ---- main entrypoint ----------------------------------------------

    async def calculate(self, req: ValuationRequest) -> dict[str, Any]:
        crsp_id, crsp_row = await self._resolve_crsp_id(req)

        condition_name = CONDITION_MAP.get(req.condition, req.condition.upper())
        accident_status = ACCIDENT_MAP.get(req.accident_history, req.accident_history.upper())
        location_name = req.location.strip().upper()

        try:
            rpc_res = self.supabase.rpc(
                "calculate_vehicle_valuation",
                {
                    "p_vehicle_crsp_id": crsp_id,
                    "p_manufacture_year": req.year,
                    "p_mileage_km": req.mileage,
                    "p_vehicle_type": req.vehicle_type.upper(),
                    "p_condition_name": condition_name,
                    "p_accident_status": accident_status,
                    "p_location_name": location_name,
                    "p_profit_margin_percent": req.profit_margin,
                },
            ).execute()
        except Exception as exc:  # noqa: BLE001
            logger.exception("calculate_vehicle_valuation RPC failed")
            raise ValuationError(f"Valuation calculation failed: {exc}", status_code=502) from exc

        rows = rpc_res.data or []
        if not rows:
            raise ValuationError("Valuation function returned no rows", status_code=502)

        row = rows[0]
        return self._to_api_shape(row, req, crsp_row)

    # ---- response shaping ----------------------------------------------

    @staticmethod
    def _to_api_shape(
        row: dict[str, Any], req: ValuationRequest, crsp_row: dict[str, Any]
    ) -> dict[str, Any]:
        depreciation_rate = row.get("depreciation_rate")
        depreciation_rate_frac = (
            float(depreciation_rate) / 100.0 if depreciation_rate is not None else None
        )

        def pct_of_base(amount: Optional[float]) -> float:
            base = row.get("value_after_depreciation") or row.get("crsp_value")
            if amount is None or not base:
                return 0.0
            return float(amount) / float(base)

        adjustments = {
            "mileage": pct_of_base(row.get("mileage_adjustment")),
            "condition": pct_of_base(row.get("condition_adjustment")),
            "accident": pct_of_base(row.get("accident_adjustment")),
            "location": pct_of_base(row.get("location_adjustment")),
            "market": pct_of_base(row.get("market_adjustment")),
        }

        report_number = row.get("valuation_reference") or f"AUTO-V-{uuid.uuid4().hex[:8].upper()}"

        return {
            "success": True,
            "data": {
                "vehicle": {
                    "make": row.get("make", req.make),
                    "model": row.get("model", req.model),
                    "trim": req.trim,
                    "year": row.get("manufacture_year", req.year),
                    "mileage": req.mileage,
                    "location": req.location,
                    "condition": req.condition,
                    "fuel_type": req.fuel_type,
                    "transmission": req.transmission,
                    "engine_capacity": req.engine_capacity,
                },
                "valuation": {
                    "estimated_vehicle_value": row.get("final_market_value"),
                    "recommended_selling_price": row.get("recommended_selling_price"),
                    "confidence_score": row.get("confidence_score"),
                },
                "analysis": {
                    "adjustments": adjustments,
                    "depreciation_rate": depreciation_rate_frac,
                    "depreciation_amount": row.get("depreciation_value"),
                    "mileage_adjustment": pct_of_base(row.get("mileage_adjustment")),
                    "vehicle_age": row.get("vehicle_age"),
                },
                "report": {"report_number": report_number},
                "crsp": {
                    "crsp_id": crsp_row.get("crsp_id"),
                    "crsp_value": row.get("crsp_value"),
                    "trim_level": crsp_row.get("trim_level"),
                },
            },
        }
