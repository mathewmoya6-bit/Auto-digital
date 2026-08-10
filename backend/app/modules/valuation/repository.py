# app/modules/valuation/repository.py
"""Database access layer for AUTO-D valuation.

All Supabase calls in this repository are intentionally synchronous.
The service must NOT use ``await`` on repository methods because the
Supabase client currently returns normal Python response objects.
"""

import logging
from typing import Any, Dict, List, Optional

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class ValuationRepository:
    CRSP_LOOKUP_TABLE = "vehicle_crsp_lookup"
    CRSP_PRICES_TABLE = "vehicle_crsp_prices"

    def __init__(self, supabase=None):
        self.supabase = supabase or get_supabase()

    def get_crsp_by_id(self, crsp_id: int) -> Optional[Dict[str, Any]]:
        response = (
            self.supabase.table(self.CRSP_LOOKUP_TABLE)
            .select("*")
            .eq("crsp_id", int(crsp_id))
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def search_crsp(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        manufacture_year: Optional[int] = None,
        engine_capacity_id: Optional[int] = None,
        fuel: Optional[str] = None,
        transmission: Optional[str] = None,
        body_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query = self.supabase.table(self.CRSP_LOOKUP_TABLE).select("*")

        if make:
            query = query.ilike("make", str(make).strip())
        if model:
            query = query.ilike("model", str(model).strip())
        if manufacture_year is not None:
            query = query.eq("manufacture_year", int(manufacture_year))
        if engine_capacity_id is not None:
            query = query.eq("engine_capacity_id", int(engine_capacity_id))
        if fuel:
            query = query.ilike("fuel", str(fuel).strip())
        if transmission:
            query = query.ilike("transmission", str(transmission).strip())
        if body_type:
            query = query.ilike("body_type", str(body_type).strip())

        response = query.limit(max(1, min(int(limit), 100))).execute()
        return response.data or []

    def get_crsp_price_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        """Fallback against the physical CRSP price table when needed."""
        response = (
            self.supabase.table(self.CRSP_PRICES_TABLE)
            .select("*")
            .eq("id", int(record_id))
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def save_valuation_result(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Persist a valuation when the caller explicitly requests it.

        This is deliberately separate from calculation so an API valuation
        cannot unexpectedly create database records.
        """
        response = (
            self.supabase.table("vehicle_valuation_results")
            .insert(payload)
            .execute()
        )
        return response.data[0] if response.data else None

    def get_depreciation_rates(self) -> List[Dict[str, Any]]:
        response = (
            self.supabase.table("vehicle_depreciation_rates")
            .select("*")
            .execute()
        )
        return response.data or []


def get_valuation_repository() -> ValuationRepository:
    return ValuationRepository()
