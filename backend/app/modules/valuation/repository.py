"""
repository.py

Data-access layer for the Auto-D Kenya valuation module.

Responsibilities:
- Look up CRSP records from vehicle_crsp.
- Call calculate_vehicle_valuation().
- Convert database rows into domain models.

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
    def __init__(self, supabase: Any):
        self.supabase = supabase

    # ------------------------------------------------------------------
    # CRSP LOOKUP
    # ------------------------------------------------------------------

    def find_crsp_candidates(
        self,
        make: str | None,
        model: str | None,
    ) -> list[CRSPRecord]:
        """
        Return CRSP rows matching make and model.

        The authoritative CRSP table is vehicle_crsp.

        Current columns used:
            crsp_id
            make
            model
            trim_level
            manufacture_year
            crsp_kes
            crsp_status
        """

        make_value = (make or "").strip()
        model_value = (model or "").strip()

        logger.info(
            "CRSP lookup: make=%r model=%r",
            make_value,
            model_value,
        )

        if not make_value or not model_value:
            raise RepositoryError(
                "CRSP lookup requires both make and model"
            )

        try:
            response = (
                self.supabase
                .table(CRSP_TABLE)
                .select(
                    "crsp_id,"
                    "make,"
                    "model,"
                    "trim_level,"
                    "manufacture_year,"
                    "crsp_kes,"
                    "crsp_status"
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

        rows = response.data or []

        logger.info(
            "CRSP lookup returned %d rows for %r %r",
            len(rows),
            make_value,
            model_value,
        )

        records: list[CRSPRecord] = []

        for row in rows:
            try:
                records.append(
                    CRSPRecord.model_validate(row)
                )

            except Exception as exc:
                logger.exception(
                    "Invalid CRSP row: %r",
                    row,
                )

                raise RepositoryError(
                    f"Invalid CRSP record: {exc}"
                ) from exc

        return records

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
        Call the PostgreSQL valuation function.

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

        Therefore p_mileage_km MUST be sent as an integer.
        """

        # PostgreSQL expects INTEGER.
        mileage_integer = int(round(float(mileage_km)))

        rpc_params = {
            "p_vehicle_crsp_id": int(crsp_id),
            "p_manufacture_year": int(manufacture_year),
            "p_mileage_km": mileage_integer,
            "p_vehicle_type": (
                str(vehicle_type)
                .strip()
                .upper()
            ),
            "p_condition_name": (
                str(condition_name)
                .strip()
                .upper()
            ),
            "p_accident_status": (
                str(accident_status)
                .strip()
                .upper()
            ),
            "p_location_name": (
                str(location_name)
                .strip()
                .upper()
            ),
            "p_profit_margin_percent": float(
                profit_margin_percent
            ),
        }

        logger.info(
            "Calling %s with params=%r",
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
            "Valuation RPC returned: %r",
            data,
        )

        if not data:
            raise RepositoryError(
                "No valuation data received"
            )

        if isinstance(data, list):
            row = data[0]

        elif isinstance(data, dict):
            row = data

        else:
            raise RepositoryError(
                "Valuation RPC returned an unexpected response type"
            )

        if not isinstance(row, dict):
            raise RepositoryError(
                "Valuation RPC returned an invalid result row"
            )

        try:
            return ValuationResultRow.model_validate(row)

        except Exception as exc:
            logger.exception(
                "Invalid valuation result: %r",
                row,
            )

            raise RepositoryError(
                f"Invalid valuation result: {exc}"
            ) from exc
