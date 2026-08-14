"""
repository.py

Data-access layer for the Auto-D Kenya valuation module.

Responsibilities:
- Query the authoritative vehicle_crsp table.
- Resolve CRSP records by make/model.
- Call calculate_vehicle_valuation().
- Convert database results into domain models.

No HTTP or frontend response logic belongs here.
"""

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
    """Repository for CRSP lookup and valuation RPC operations."""

    def __init__(self, supabase):
        self.supabase = supabase

    # ------------------------------------------------------------------
    # CRSP lookup
    # ------------------------------------------------------------------

    def find_crsp_candidates(
        self,
        make: str | None,
        model: str | None,
    ) -> list[CRSPRecord]:
        """
        Find CRSP rows matching make and model.

        The authoritative table is vehicle_crsp.

        manufacture_year is the year column used by the current
        vehicle_crsp schema. The CRSPRecord model exposes it through
        its .year property.
        """

        make_value = (make or "").strip()
        model_value = (model or "").strip()

        logger.info(
            "CRSP lookup request: make=%r model=%r",
            make_value,
            model_value,
        )

        # Do not silently perform an unfiltered full-table lookup.
        # An empty make/model means the API request is malformed.
        if not make_value or not model_value:
            raise RepositoryError(
                "CRSP lookup requires both make and model"
            )

        try:
            query = (
                self.supabase
                .table(CRSP_TABLE)
                .select(
                    "crsp_id,make,model,trim_level,"
                    "manufacture_year,crsp_kes,crsp_status"
                )
                .ilike("make", make_value)
                .ilike("model", model_value)
            )

            response = query.execute()

        except Exception as exc:
            logger.exception(
                "CRSP lookup failed: make=%r model=%r",
                make_value,
                model_value,
            )
            raise RepositoryError(
                f"CRSP lookup failed: {exc}"
            ) from exc

        data = response.data or []

        logger.info(
            "CRSP lookup returned %d rows for make=%r model=%r",
            len(data),
            make_value,
            model_value,
        )

        if data:
            logger.info(
                "First CRSP result: %r",
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
                    "Invalid CRSP database row: %r",
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

        Current PostgreSQL signature:

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

        Therefore mileage_km is explicitly converted to integer before
        being sent to PostgreSQL.
        """

        mileage_integer = int(round(float(mileage_km)))

        rpc_params: dict[str, Any] = {
            "p_vehicle_crsp_id": int(crsp_id),
            "p_manufacture_year": int(manufacture_year),
            "p_mileage_km": mileage_integer,
            "p_vehicle_type": str(vehicle_type).strip().upper(),
            "p_condition_name": str(condition_name).strip().upper(),
            "p_accident_status": str(accident_status).strip().upper(),
            "p_location_name": str(location_name).strip().upper(),
            "p_profit_margin_percent": float(profit_margin_percent),
        }

        logger.info(
            "Valuation RPC request: function=%s params=%r",
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
                "Valuation RPC failed: crsp_id=%s",
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

        if isinstance(data, list):
            if not data:
                raise RepositoryError(
                    "Valuation RPC returned an empty result"
                )
            row = data[0]

        elif isinstance(data, dict):
            row = data

        else:
            raise RepositoryError(
                "Valuation RPC returned an unexpected "
                f"response type: {type(data).__name__}"
            )

        if not isinstance(row, dict):
            raise RepositoryError(
                "Valuation RPC returned an invalid result row"
            )

        logger.info(
            "Valuation result row: %r",
            row,
        )

        try:
            result = ValuationResultRow.model_validate(row)

        except Exception as exc:
            logger.exception(
                "Valuation result validation failed: %r",
                row,
            )
            raise RepositoryError(
                f"Invalid valuation result returned by RPC: {exc}"
            ) from exc

        logger.info(
            "Valuation successful: valuation_id=%r "
            "crsp_id=%r final_market_value=%r "
            "recommended_selling_price=%r confidence_score=%r "
            "reference=%r",
            result.valuation_id,
            result.vehicle_crsp_id,
            result.final_market_value,
            result.recommended_selling_price,
            result.confidence_score,
            result.valuation_reference,
        )

        return result
