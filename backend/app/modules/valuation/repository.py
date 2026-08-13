"""
repository.py

Data-access layer. Owns every direct Supabase/Postgres call for the
valuation feature. Nothing in here knows about HTTP status codes or
the public API response shape — it only speaks in `models.py` domain
objects, so `engine.py` can stay focused on business rules.

ASSUMPTION: matching against make/model happens on the `vehicle_crsp`
table. If your CRSP matching should instead go through the
`vehicle_crsp_lookup` view (the one the frontend queries directly for
makes/models/years/trims), just change CRSP_TABLE below.
"""

from __future__ import annotations

import logging

from .models import CRSPRecord, ValuationResultRow

logger = logging.getLogger(__name__)

CRSP_TABLE = "vehicle_crsp"
VALUATION_RPC = "calculate_vehicle_valuation"


class RepositoryError(Exception):
    """Raised for data-access failures; engine.py maps this to a
    ValuationEngineError with an appropriate status code."""


class ValuationRepository:
    def __init__(self, supabase):
        self.supabase = supabase

    def find_crsp_candidates(self, make: str, model: str) -> list[CRSPRecord]:
        """Return every CRSP schedule row for this make/model, across
        all trims and years, for the engine to pick the best match from."""
        try:
            res = (
                self.supabase.table(CRSP_TABLE)
                .select("crsp_id, make, model, trim_level, manufacture_year, crsp_year, crsp_kes")
                .ilike("make", make)
                .ilike("model", model)
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("CRSP lookup failed for %s %s", make, model)
            raise RepositoryError(f"CRSP lookup failed: {exc}") from exc

        return [CRSPRecord.model_validate(row) for row in (res.data or [])]

    def call_valuation_function(
        self,
        *,
        crsp_id: int,
        manufacture_year: int,
        mileage_km: float,
        vehicle_type: str,
        condition_name: str,
        accident_status: str,
        location_name: str,
        profit_margin_percent: float,
    ) -> ValuationResultRow:
        """Call the deployed `calculate_vehicle_valuation` SQL function
        and return the single resulting row as a domain object."""
        try:
            res = self.supabase.rpc(
                VALUATION_RPC,
                {
                    "p_vehicle_crsp_id": crsp_id,
                    "p_manufacture_year": manufacture_year,
                    "p_mileage_km": mileage_km,
                    "p_vehicle_type": vehicle_type,
                    "p_condition_name": condition_name,
                    "p_accident_status": accident_status,
                    "p_location_name": location_name,
                    "p_profit_margin_percent": profit_margin_percent,
                },
            ).execute()
        except Exception as exc:  # noqa: BLE001
            logger.exception("calculate_vehicle_valuation RPC failed (crsp_id=%s)", crsp_id)
            raise RepositoryError(f"Valuation RPC call failed: {exc}") from exc

        rows = res.data or []
        if not rows:
            raise RepositoryError("calculate_vehicle_valuation returned no rows")

        return ValuationResultRow.model_validate(rows[0])
