"""
app/modules/valuation/repository.py

Database access layer for vehicle valuation.

Responsibilities:
    1. Resolve a vehicle against vehicle_crsp.
    2. Call calculate_vehicle_valuation().
    3. If the RPC does not return the persisted row, retrieve the
       newly-created result from vehicle_valuation_results.

The SQL function remains the single source of truth for calculations.
"""

from __future__ import annotations

import logging
from typing import Optional

from .models import CRSPRecord, ValuationResultRow

logger = logging.getLogger(__name__)

CRSP_TABLE = "vehicle_crsp"
RESULTS_TABLE = "vehicle_valuation_results"
VALUATION_RPC = "calculate_vehicle_valuation"


class RepositoryError(Exception):
    """Raised when a database operation required by valuation fails."""


class ValuationRepository:

    def __init__(self, supabase):
        self.supabase = supabase

    # ------------------------------------------------------------------
    # CRSP LOOKUP
    # ------------------------------------------------------------------

    def find_crsp_candidates(
        self,
        make: str,
        model: str,
    ) -> list[CRSPRecord]:

        make = (make or "").strip()
        model = (model or "").strip()

        if not make or not model:
            raise RepositoryError(
                "CRSP lookup requires both make and model"
            )

        logger.info(
            "CRSP lookup: make=%r model=%r",
            make,
            model,
        )

        try:
            response = (
                self.supabase
                .table(CRSP_TABLE)
                .select(
                    """
                    crsp_id,
                    make,
                    model,
                    trim_level,
                    manufacture_year,
                    crsp_kes
                    """
                )
                .ilike("make", make)
                .ilike("model", model)
                .execute()
            )

        except Exception as exc:
            logger.exception(
                "CRSP lookup failed: %s %s",
                make,
                model,
            )
            raise RepositoryError(
                f"CRSP lookup failed: {exc}"
            ) from exc

        rows = response.data or []

        logger.info(
            "CRSP lookup returned %d rows for %s %s",
            len(rows),
            make,
            model,
        )

        return [
            CRSPRecord.model_validate(row)
            for row in rows
        ]

    # ------------------------------------------------------------------
    # VALUATION RPC
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
        Calls calculate_vehicle_valuation().

        IMPORTANT:
        The PostgreSQL function signature is:

        calculate_vehicle_valuation(
            bigint,
            integer,
            integer,
            varchar,
            varchar,
            varchar,
            varchar,
            numeric
        )

        Therefore mileage MUST be sent as an integer.
        """

        try:
            mileage_integer = int(round(float(mileage_km)))

        except (TypeError, ValueError) as exc:
            raise RepositoryError(
                f"Invalid mileage value: {mileage_km!r}"
            ) from exc

        logger.info(
            "Calling valuation RPC: "
            "crsp_id=%s year=%s mileage=%s type=%s "
            "condition=%s accident=%s location=%s margin=%s",
            crsp_id,
            manufacture_year,
            mileage_integer,
            vehicle_type,
            condition_name,
            accident_status,
            location_name,
            profit_margin_percent,
        )

        rpc_params = {
            "p_vehicle_crsp_id": int(crsp_id),
            "p_manufacture_year": int(manufacture_year),
            "p_mileage_km": mileage_integer,
            "p_vehicle_type": vehicle_type,
            "p_condition_name": condition_name,
            "p_accident_status": accident_status,
            "p_location_name": location_name,
            "p_profit_margin_percent": float(
                profit_margin_percent
            ),
        }

        try:
            response = (
                self.supabase
                .rpc(
                    VALUATION_RPC,
                    rpc_params,
                )
                .execute()
            )

        except Exception as exc:
            logger.exception(
                "Valuation RPC failed for CRSP %s",
                crsp_id,
            )
            raise RepositoryError(
                f"Valuation RPC call failed: {exc}"
            ) from exc

        rows = response.data or []

        logger.info(
            "Valuation RPC returned %d row(s)",
            len(rows),
        )

        # --------------------------------------------------------------
        # BEST CASE:
        # RPC directly returned the valuation result.
        # --------------------------------------------------------------

        if rows:
            return ValuationResultRow.model_validate(rows[0])

        # --------------------------------------------------------------
        # FALLBACK:
        # SQL function may have inserted into
        # vehicle_valuation_results without returning a row.
        # Retrieve the latest matching result.
        # --------------------------------------------------------------

        logger.warning(
            "Valuation RPC returned no rows. "
            "Looking up persisted result in %s",
            RESULTS_TABLE,
        )

        return self._get_latest_result(
            crsp_id=crsp_id,
            manufacture_year=manufacture_year,
            mileage_km=mileage_integer,
        )

    # ------------------------------------------------------------------
    # PERSISTED RESULT LOOKUP
    # ------------------------------------------------------------------

    def _get_latest_result(
        self,
        *,
        crsp_id: int,
        manufacture_year: int,
        mileage_km: int,
    ) -> ValuationResultRow:

        try:
            response = (
                self.supabase
                .table(RESULTS_TABLE)
                .select("*")
                .eq("vehicle_crsp_id", int(crsp_id))
                .eq(
                    "manufacture_year",
                    int(manufacture_year),
                )
                .eq(
                    "mileage_km",
                    int(mileage_km),
                )
                .order(
                    "id",
                    desc=True,
                )
                .limit(1)
                .execute()
            )

        except Exception as exc:
            logger.exception(
                "Failed to retrieve persisted valuation result"
            )
            raise RepositoryError(
                f"Valuation result lookup failed: {exc}"
            ) from exc

        rows = response.data or []

        if not rows:
            raise RepositoryError(
                "No valuation data received"
            )

        logger.info(
            "Retrieved persisted valuation result id=%s",
            rows[0].get("id"),
        )

        return ValuationResultRow.model_validate(
            rows[0]
        )


__all__ = [
    "RepositoryError",
    "ValuationRepository",
]
