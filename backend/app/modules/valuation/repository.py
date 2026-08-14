"""
repository.py

Data access layer for Auto-D Kenya valuation.

Responsibilities:
- Find CRSP records by make + model.
- Find CRSP records by model when make is missing.
- Call calculate_vehicle_valuation().
"""

from __future__ import annotations

import logging
from typing import Any

from .models import CRSPRecord, ValuationResultRow

logger = logging.getLogger(__name__)

CRSP_TABLE = "vehicle_crsp"
VALUATION_RPC = "calculate_vehicle_valuation"


class RepositoryError(Exception):
    """Database/data-access error for valuation."""


class ValuationRepository:

    def __init__(self, supabase: Any):
        self.supabase = supabase

    # ================================================================
    # FIND BY MAKE + MODEL
    # ================================================================

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
                "CRSP lookup failed: make=%r model=%r",
                make,
                model,
            )

            raise RepositoryError(
                f"CRSP lookup failed: {exc}"
            ) from exc

        rows = response.data or []

        logger.info(
            "CRSP lookup returned %d rows for %r %r",
            len(rows),
            make,
            model,
        )

        return [
            CRSPRecord.model_validate(row)
            for row in rows
        ]

    # ================================================================
    # FIND BY MODEL ONLY
    # ================================================================

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
                "CRSP model lookup failed: model=%r",
                model,
            )

            raise RepositoryError(
                f"CRSP model lookup failed: {exc}"
            ) from exc

        rows = response.data or []

        logger.info(
            "CRSP model-only lookup returned %d rows for %r",
            len(rows),
            model,
        )

        return [
            CRSPRecord.model_validate(row)
            for row in rows
        ]

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

        # PostgreSQL function expects INTEGER mileage.
        mileage_integer = int(round(float(mileage_km)))

        params = {
            "p_vehicle_crsp_id": int(crsp_id),
            "p_manufacture_year": int(manufacture_year),
            "p_mileage_km": mileage_integer,
            "p_vehicle_type": str(
                vehicle_type
            ).strip().upper(),
            "p_condition_name": str(
                condition_name
            ).strip().upper(),
            "p_accident_status": str(
                accident_status
            ).strip().upper(),
            "p_location_name": str(
                location_name
            ).strip().upper(),
            "p_profit_margin_percent": float(
                profit_margin_percent
            ),
        }

        logger.info(
            "Calling %s: %s",
            VALUATION_RPC,
            params,
        )

        try:
            response = (
                self.supabase
                .rpc(
                    VALUATION_RPC,
                    params,
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

        data = response.data or []

        logger.info(
            "Valuation RPC returned %r",
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
                "Invalid valuation RPC response"
            )

        try:
            return ValuationResultRow.model_validate(
                row
            )

        except Exception as exc:
            logger.exception(
                "Invalid valuation result row: %r",
                row,
            )

            raise RepositoryError(
                f"Invalid valuation result: {exc}"
            ) from exc
