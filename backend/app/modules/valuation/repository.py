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

    # ------------------------------------------------------------------
    # CRSP lookup
    # ------------------------------------------------------------------

    def find_crsp_candidates(
        self,
        make: str,
        model: str,
    ) -> list[CRSPRecord]:
        """
        Find CRSP rows for a vehicle.

        The authoritative table is public.vehicle_crsp.

        Current database fields used:
            crsp_id
            make
            model
            trim_level
            manufacture_year
            crsp_kes

        Domain normalization:
            manufacture_year -> year

        IMPORTANT:
            vehicle_crsp.crsp_year does not exist and must never be
            queried here.

        The lookup also handles the frontend case where make is blank
        and the model contains the complete CRSP model name, e.g.:

            make  = ""
            model = "CHRYSLER 300"

        In that case the repository searches the model directly.
        """

        make_value = (make or "").strip()
        model_value = (model or "").strip()

        if not model_value:
            return []

        select_columns = (
            "crsp_id,make,model,trim_level,"
            "manufacture_year,crsp_kes"
        )

        try:
            if make_value:
                # Normal path: make + model.
                response = (
                    self.supabase
                    .table(CRSP_TABLE)
                    .select(select_columns)
                    .ilike("make", make_value)
                    .ilike("model", model_value)
                    .execute()
                )
            else:
                # Frontend fallback: model contains the complete name.
                # Example: model = "CHRYSLER 300"
                response = (
                    self.supabase
                    .table(CRSP_TABLE)
                    .select(select_columns)
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

        # If make was supplied but the exact make/model combination did
        # not match, try the model alone. This protects against frontend
        # make/model normalization differences while still requiring an
        # actual model match in the authoritative CRSP table.
        if not rows and make_value:
            try:
                fallback_response = (
                    self.supabase
                    .table(CRSP_TABLE)
                    .select(select_columns)
                    .ilike("model", model_value)
                    .execute()
                )
                rows = fallback_response.data or []
            except Exception as exc:
                logger.exception(
                    "CRSP model fallback lookup failed for model=%r",
                    model_value,
                )
                raise RepositoryError(
                    f"CRSP lookup failed: {exc}"
                ) from exc

        candidates: list[CRSPRecord] = []

        for database_row in rows:
            row = dict(database_row)

            # Normalize current DB schema into the domain model.
            row["year"] = row.get("manufacture_year")

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

        logger.info(
            "CRSP lookup: make=%r model=%r -> %d candidate(s)",
            make_value,
            model_value,
            len(candidates),
        )

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
        Call the deployed calculate_vehicle_valuation PostgreSQL
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
        except Exception as exc:
            logger.exception(
                "Valuation RPC failed for crsp_id=%s",
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
        except Exception as exc:
            logger.exception(
                "Invalid valuation RPC response for crsp_id=%s",
                crsp_id,
            )
            raise RepositoryError(
                f"Invalid valuation result: {exc}"
            ) from exc
