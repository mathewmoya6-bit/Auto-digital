"""
app/modules/valuation/repository.py

Data-access layer for vehicle valuation.

Responsibilities:
- CRSP lookup
- Calling calculate_vehicle_valuation()
- Converting Supabase responses into domain models

Business logic belongs in engine.py.
HTTP logic belongs in router.py.
"""

from __future__ import annotations

import logging
from typing import Any

from .models import CRSPRecord, ValuationResultRow

logger = logging.getLogger(__name__)

CRSP_TABLE = "vehicle_crsp"
VALUATION_RPC = "calculate_vehicle_valuation"


class RepositoryError(Exception):
    """Database/Supabase error raised by the valuation repository."""


class ValuationRepository:

    def __init__(self, supabase):
        if supabase is None:
            raise RepositoryError("Supabase client is not configured")

        self.supabase = supabase

    # ================================================================
    # CRSP LOOKUP
    # ================================================================

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

        try:
            logger.info(
                "CRSP lookup: make=%r model=%r",
                make,
                model,
            )

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
                "CRSP lookup failed: make=%s model=%s",
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

        records: list[CRSPRecord] = []

        for row in rows:
            try:
                records.append(
                    CRSPRecord.model_validate(row)
                )
            except Exception as exc:
                logger.warning(
                    "Ignoring invalid CRSP row: %s",
                    exc,
                )

        return records

    # ================================================================
    # VALUATION RPC
    # ================================================================

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

        # PostgreSQL function signature expects:
        #
        # bigint,
        # integer,
        # integer,
        # varchar,
        # varchar,
        # varchar,
        # varchar,
        # numeric

        try:
            mileage_integer = int(round(float(mileage_km)))

        except (TypeError, ValueError) as exc:
            raise RepositoryError(
                f"Invalid mileage: {mileage_km}"
            ) from exc

        try:
            logger.info(
                "Calling valuation RPC: "
                "crsp_id=%s year=%s mileage=%s "
                "type=%s condition=%s accident=%s "
                "location=%s margin=%s",
                crsp_id,
                manufacture_year,
                mileage_integer,
                vehicle_type,
                condition_name,
                accident_status,
                location_name,
                profit_margin_percent,
            )

            response = self.supabase.rpc(
                VALUATION_RPC,
                {
                    "p_vehicle_crsp_id": int(crsp_id),
                    "p_manufacture_year": int(manufacture_year),
                    "p_mileage_km": mileage_integer,
                    "p_vehicle_type": str(vehicle_type),
                    "p_condition_name": str(condition_name),
                    "p_accident_status": str(accident_status),
                    "p_location_name": str(location_name),
                    "p_profit_margin_percent": float(
                        profit_margin_percent
                    ),
                },
            ).execute()

        except Exception as exc:
            logger.exception(
                "calculate_vehicle_valuation RPC failed"
            )

            raise RepositoryError(
                f"Valuation RPC call failed: {exc}"
            ) from exc

        rows: Any = response.data

        logger.info(
            "Valuation RPC raw response type=%s",
            type(rows).__name__,
        )

        logger.info(
            "Valuation RPC returned: %r",
            rows,
        )

        if rows is None:
            raise RepositoryError(
                "No valuation data received"
            )

        # Supabase normally returns a list for a table-returning
        # PostgreSQL function.
        if isinstance(rows, list):

            if not rows:
                raise RepositoryError(
                    "No valuation data received"
                )

            row = rows[0]

        # Defensive support for a single dictionary response.
        elif isinstance(rows, dict):

            row = rows

        else:
            raise RepositoryError(
                "Unexpected valuation RPC response format"
            )

        if not isinstance(row, dict):
            raise RepositoryError(
                "Invalid valuation data returned by database"
            )

        try:
            result = ValuationResultRow.model_validate(row)

        except Exception as exc:
            logger.exception(
                "Unable to parse valuation result: %r",
                row,
            )

            raise RepositoryError(
                f"Invalid valuation result: {exc}"
            ) from exc

        logger.info(
            "Valuation successful: "
            "reference=%s final_market_value=%s",
            result.valuation_reference,
            result.final_market_value,
        )

        return result
