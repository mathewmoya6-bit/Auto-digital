from __future__ import annotations

import logging
from typing import Any

from .models import CRSPRecord, ValuationResultRow

logger = logging.getLogger(__name__)

CRSP_TABLE = "vehicle_crsp"
VALUATION_RPC = "calculate_vehicle_valuation"


class RepositoryError(Exception):
    """Raised when a valuation database operation fails."""


class ValuationRepository:
    """Supabase/Postgres repository for vehicle valuation."""

    def __init__(self, supabase: Any):
        self.supabase = supabase

    def find_crsp_candidates(
        self,
        make: str,
        model: str,
    ) -> list[CRSPRecord]:
        """
        Find all CRSP rows for a make/model.

        Current vehicle_crsp schema:
        - crsp_id
        - make
        - model
        - trim_level
        - manufacture_year
        - crsp_kes

        The database field manufacture_year is normalized to the
        domain-model field year expected by engine.py.

        IMPORTANT: crsp_year is intentionally not queried.
        """
        make_value = (make or "").strip()
        model_value = (model or "").strip()

        if not make_value or not model_value:
            return []

        try:
            result = (
                self.supabase
                .table(CRSP_TABLE)
                .select(
                    "crsp_id,make,model,trim_level,"
                    "manufacture_year,crsp_kes"
                )
                .ilike("make", make_value)
                .ilike("model", model_value)
                .execute()
            )
        except Exception as exc:
            logger.exception(
                "CRSP lookup failed for make=%r model=%r",
                make_value,
                model_value,
            )
            raise RepositoryError(
                f"CRSP lookup failed: {exc}"
            ) from exc

        candidates: list[CRSPRecord] = []

        for database_row in result.data or []:
            row = dict(database_row)

            # Database -> domain model normalization.
            row["year"] = row.get("manufacture_year")

            # Keep crsp_kes available for models that use that field.
            row["crsp_kes"] = row.get("crsp_kes")

            try:
                candidate = CRSPRecord.model_validate(row)
            except Exception as exc:
                logger.exception(
                    "Invalid CRSP record: crsp_id=%r",
                    row.get("crsp_id"),
                )
                raise RepositoryError(
                    f"Invalid CRSP record "
                    f"{row.get('crsp_id')}: {exc}"
                ) from exc

            candidates.append(candidate)

        return candidates

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
        Call the calculate_vehicle_valuation PostgreSQL function.
        """
        try:
            result = (
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
        except Exception as exc:
            logger.exception(
                "Valuation RPC failed for crsp_id=%s",
                crsp_id,
            )
            raise RepositoryError(
                f"Valuation RPC call failed: {exc}"
            ) from exc

        rows = result.data or []

        if not rows:
            raise RepositoryError(
                "calculate_vehicle_valuation returned no rows"
            )

        try:
            return ValuationResultRow.model_validate(rows[0])
        except Exception as exc:
            logger.exception(
                "Invalid valuation RPC response for crsp_id=%s",
                crsp_id,
            )
            raise RepositoryError(
                f"Invalid valuation result: {exc}"
            ) from exc
