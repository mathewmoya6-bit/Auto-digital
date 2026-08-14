repository.py

Data-access layer for the valuation feature.

Responsibilities:
- Read CRSP candidates from the authoritative `vehicle_crsp` table.
- Normalize database column names into the valuation domain model.
- Call the deployed `calculate_vehicle_valuation` RPC.
- Never expose database-specific errors to the public API layer.

Important:
- `vehicle_crsp.crsp_year` is NOT used.
- The authoritative year column is `manufacture_year`.
- `vehicle_crsp.crsp_kes` is the CRSP monetary value.
"""

from __future__ import annotations

import logging
from typing import Any

from .models import CRSPRecord, ValuationResultRow

logger = logging.getLogger(__name__)

CRSP_TABLE = "vehicle_crsp"
VALUATION_RPC = "calculate_vehicle_valuation"


class RepositoryError(Exception):
    """Raised for valuation data-access failures."""


class ValuationRepository:
    def __init__(self, supabase: Any):
        self.supabase = supabase

    # ------------------------------------------------------------------
    # CRSP lookup
    # ------------------------------------------------------------------

    def find_crsp_candidates(
        self,
        make: str,
        model: str,
    ) -> list[CRSPRecord]:
        """
        Return all CRSP schedule rows matching make/model.

        Database -> domain normalization:
            manufacture_year -> year
            crsp_kes          -> crsp_kes

        The engine intentionally works with `CRSPRecord.year`, while
        PostgreSQL stores the field as `manufacture_year`.
        """
        make_value = (make or "").strip()
        model_value = (model or "").strip()

        if not make_value or not model_value:
            return []

        try:
            response = (
                self.supabase
                .table(CRSP_TABLE)
                .select(
                    "crsp_id, make, model, trim_level, "
                    "manufacture_year, crsp_kes"
                )
                .ilike("make", make_value)
                .ilike("model", model_value)
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "CRSP lookup failed for make=%r model=%r",
                make_value,
                model_value,
            )
            raise RepositoryError(f"CRSP lookup failed: {exc}") from exc

        candidates: list[CRSPRecord] = []

        for raw_row in response.data or []:
            row = dict(raw_row)

            # Normalize the current DB schema into the domain model.
            row["year"] = row.get("manufacture_year")

            try:
                candidates.append(CRSPRecord.model_validate(row))
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Invalid CRSP row skipped: crsp_id=%r",
                    row.get("crsp_id"),
                )
                raise RepositoryError(
                    f"Invalid CRSP record {row.get('crsp_id')}: {exc}"
                ) from exc

        return candidates

    # ------------------------------------------------------------------
    # Valuation RPC
    # ------------------------------------------------------------------

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
        """
        Call the deployed `calculate_vehicle_valuation` PostgreSQL
        function and return its first result as a domain object.
        """
        try:
            response = (
                self.supabase
                .rpc(
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
                )
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "calculate_vehicle_valuation RPC failed (crsp_id=%s)",
                crsp_id,
            )
            raise RepositoryError(
                f"Valuation RPC call failed: {exc}"
            ) from exc

        rows = response.data or []

        if not rows:
            raise RepositoryError(
                "calculate_vehicle_valuation returned no rows"
            )

        try:
            return ValuationResultRow.model_validate(rows[0])
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Invalid valuation RPC response (crsp_id=%s)",
                crsp_id,
            )
            raise RepositoryError(
                f"Invalid valuation result: {exc}"
            ) from exc
