"""
app/modules/valuation/repository.py

Database access layer for Auto-D Kenya valuation.

Authoritative sources:
    vehicle_crsp
    calculate_vehicle_valuation(...)

The repository converts Supabase/PostgREST responses into
internal Pydantic domain models.
"""

from __future__ import annotations

import logging
from typing import Any

from .models import CRSPRecord, ValuationResultRow

logger = logging.getLogger(__name__)

CRSP_TABLE = "vehicle_crsp"
VALUATION_RPC = "calculate_vehicle_valuation"


class RepositoryError(Exception):
    """Database/repository failure."""


class ValuationRepository:

    def __init__(self, supabase):
        self.supabase = supabase

    # =================================================================
    # CRSP: MAKE + MODEL
    # =================================================================

    def find_crsp_candidates(
        self,
        make: str | None,
        model: str | None,
    ) -> list[CRSPRecord]:

        make = (make or "").strip()
        model = (model or "").strip()

        if not make or not model:
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
                .ilike("make", make)
                .ilike("model", model)
                .execute()
            )

        except Exception as exc:
            logger.exception(
                "CRSP make/model lookup failed: %s %s",
                make,
                model,
            )
            raise RepositoryError(
                f"CRSP lookup failed: {exc}"
            ) from exc

        rows = response.data or []

        logger.info(
            "CRSP make/model lookup: make=%r model=%r rows=%d",
            make,
            model,
            len(rows),
        )

        return [
            CRSPRecord.model_validate(row)
            for row in rows
        ]

    # =================================================================
    # CRSP: MODEL ONLY
    # =================================================================

    def find_crsp_by_model(
        self,
        model: str | None,
    ) -> list[CRSPRecord]:

        model = (model or "").strip()

        if not model:
            raise RepositoryError(
                "CRSP model is required"
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
                .ilike("model", model)
                .execute()
            )

        except Exception as exc:
            logger.exception(
                "CRSP model-only lookup failed: %r",
                model,
            )
            raise RepositoryError(
                f"CRSP model lookup failed: {exc}"
            ) from exc

        rows = response.data or []

        logger.info(
            "CRSP model-only lookup: model=%r rows=%d",
            model,
            len(rows),
        )

        return [
            CRSPRecord.model_validate(row)
            for row in rows
        ]

    # =================================================================
    # VALUATION RPC
    # =================================================================

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

        # -------------------------------------------------------------
        # PostgreSQL function signature:
        #
        # calculate_vehicle_valuation(
        #     bigint,
        #     integer,
        #     integer,
        #     varchar,
        #     varchar,
        #     varchar,
        #     varchar,
        #     numeric
        # )
        #
        # Therefore mileage MUST be INTEGER.
        # -------------------------------------------------------------

        try:
            mileage_integer = int(round(float(mileage_km)))
        except (TypeError, ValueError) as exc:
            raise RepositoryError(
                f"Invalid mileage: {mileage_km}"
            ) from exc

        rpc_params = {
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
                "Valuation RPC failed: %s",
                exc,
            )
            raise RepositoryError(
                f"Valuation RPC call failed: {exc}"
            ) from exc

        # -------------------------------------------------------------
        # IMPORTANT:
        # Supabase normally returns:
        #
        # response.data = [
        #     {...}
        # ]
        #
        # But depending on the function declaration/PostgREST
        # configuration, we may receive a dictionary or another
        # structure.
        # -------------------------------------------------------------

        raw_data: Any = getattr(
            response,
            "data",
            None,
        )

        logger.info(
            "Valuation RPC raw response type=%s",
            type(raw_data).__name__,
        )

        logger.info(
            "Valuation RPC raw response=%r",
            raw_data,
        )

        if raw_data is None:
            raise RepositoryError(
                "No valuation data received"
            )

        # -------------------------------------------------------------
        # Normal PostgREST table-returning function:
        #
        # [{"valuation_id": 39, ...}]
        # -------------------------------------------------------------

        if isinstance(raw_data, list):

            if not raw_data:
                raise RepositoryError(
                    "No valuation data received"
                )

            first_row = raw_data[0]

        # -------------------------------------------------------------
        # Some RPC configurations return a single object:
        #
        # {"valuation_id": 39, ...}
        # -------------------------------------------------------------

        elif isinstance(raw_data, dict):

            # Sometimes the RPC result can be wrapped.
            if "data" in raw_data and isinstance(
                raw_data["data"],
                list,
            ):
                if not raw_data["data"]:
                    raise RepositoryError(
                        "No valuation data received"
                    )

                first_row = raw_data["data"][0]

            else:
                first_row = raw_data

        else:
            raise RepositoryError(
                "Unexpected valuation RPC response format"
            )

        if not isinstance(first_row, dict):
            raise RepositoryError(
                "Valuation RPC returned an invalid row"
            )

        logger.info(
            "Valuation RPC parsed row=%r",
            first_row,
        )

        # -------------------------------------------------------------
        # Validate the database row against models.py
        # -------------------------------------------------------------

        try:
            return ValuationResultRow.model_validate(
                first_row
            )

        except Exception as exc:
            logger.exception(
                "Unable to parse valuation RPC row"
            )

            raise RepositoryError(
                f"Invalid valuation result: {exc}"
            ) from exc
