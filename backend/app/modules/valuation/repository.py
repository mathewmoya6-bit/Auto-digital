"""
repository.py

Data-access layer for the valuation module.

Responsibilities:
- Query vehicle_crsp for CRSP matching.
- Call calculate_vehicle_valuation().
- Convert database rows into domain models.

No HTTP/API response logic belongs here.
"""

from __future__ import annotations

import logging
from typing import Any

from .models import CRSPRecord, ValuationResultRow

logger = logging.getLogger(__name__)

CRSP_TABLE = "vehicle_crsp"
VALUATION_RPC = "calculate_vehicle_valuation"


class RepositoryError(Exception):
    """Raised when a database operation fails."""


class ValuationRepository:
    def __init__(self, supabase):
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
        Find CRSP records for a make/model.

        vehicle_crsp is the authoritative CRSP table.

        We deliberately do not query crsp_year because the tested
        vehicle_crsp structure uses manufacture_year.
        """

        make_value = (make or "").strip()
        model_value = (model or "").strip()

        if not make_value or not model_value:
            raise RepositoryError(
                "CRSP lookup requires both make and model"
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
                    crsp_kes,
                    crsp_status
                    """
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

        data = response.data or []

        logger.info(
            "CRSP lookup: make=%r model=%r returned %d rows",
            make_value,
            model_value,
            len(data),
        )

        if data:
            logger.info(
                "First CRSP row: %s",
                data[0],
            )

        records: list[CRSPRecord] = []

        for row in data:
            try:
                records.append(
                    CRSPRecord.model_validate(row)
                )
            except Exception as exc:
                logger.exception(
                    "Invalid CRSP row: %s",
                    row,
                )
                raise RepositoryError(
                    f"Invalid CRSP record returned by database: {exc}"
                ) from exc

        return records

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
        Execute calculate_vehicle_valuation().

        PostgreSQL signature:

        calculate_vehicle_valuation(
            bigint,
            integer,
            integer,
            character varying,
            character varying,
            character varying,
            character varying,
            numeric
        )

        Therefore mileage_km is intentionally converted to INTEGER.
        """

        rpc_params: dict[str, Any] = {
            "p_vehicle_crsp_id": int(crsp_id),
            "p_manufacture_year": int(manufacture_year),
            "p_mileage_km": int(round(float(mileage_km))),
            "p_vehicle_type": str(vehicle_type).upper(),
            "p_condition_name": str(condition_name).upper(),
            "p_accident_status": str(accident_status).upper(),
            "p_location_name": str(location_name).upper(),
            "p_profit_margin_percent": float(profit_margin_percent),
        }

        logger.info(
            "Calling %s with params=%s",
            VALUATION_RPC,
            rpc_params,
        )

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
                "Valuation RPC failed for crsp_id=%s",
                crsp_id,
            )
            raise RepositoryError(
                f"Valuation RPC call failed: {exc}"
            ) from exc

        data = response.data

        logger.info(
            "Valuation RPC response: type=%s data=%r",
            type(data).__name__,
            data,
        )

        if data is None:
            raise RepositoryError(
                "Valuation RPC returned no data"
            )

        # Supabase normally returns a list for a table-returning function.
        if isinstance(data, list):
            if not data:
                raise RepositoryError(
                    "Valuation RPC returned an empty result"
                )

            row = data[0]

        # Defensive support if the client/function returns one object.
        elif isinstance(data, dict):
            row = data

        else:
            raise RepositoryError(
                "Valuation RPC returned an unexpected "
                f"response type: {type(data).__name__}"
            )

        logger.info(
            "Valuation result row: %s",
            row,
        )

        try:
            return ValuationResultRow.model_validate(row)

        except Exception as exc:
            logger.exception(
                "Could not validate valuation result"
            )
            raise RepositoryError(
                f"Invalid valuation result returned by RPC: {exc}"
            ) from exc
