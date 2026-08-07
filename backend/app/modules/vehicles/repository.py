# app/modules/vehicles/repository.py

# Auto-D Kenya - Vehicle Master Repository
# ================================================================
# TYPE: MODULE - Vehicle Database Operations

import logging
from typing import Optional, List, Dict, Any

from fastapi.concurrency import run_in_threadpool

from app.core.database import get_supabase
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)


class VehicleRepository:
    """Repository for Vehicle Master Database."""

    def __init__(self):
        self.supabase = get_supabase()

    async def _run(self, fn):
        """Run blocking Supabase operations in a thread."""
        return await run_in_threadpool(fn)

    # ============================================================
    # VEHICLE CATALOGUE
    # ============================================================

    async def get_categories(self) -> List[Dict[str, Any]]:
        try:
            response = await self._run(
                lambda: self.supabase.table("vehicle_categories")
                .select("*")
                .order("name")
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error loading categories: {e}")
            return []

    async def get_makes(self, category_id: Optional[int] = None):
        try:
            query = self.supabase.table("vehicle_makes").select("*")

            if category_id:
                query = query.eq("category_id", category_id)

            query = query.eq("is_active", True)

            response = await self._run(
                lambda: query.order("name").execute()
            )

            return response.data or []

        except Exception as e:
            logger.error(f"Error getting makes: {e}")
            return []

    async def get_models(self, make_id: int):
        try:
            response = await self._run(
                lambda: self.supabase.table("vehicle_models")
                .select("*")
                .eq("make_id", make_id)
                .eq("is_active", True)
                .order("name")
                .execute()
            )

            return response.data or []

        except Exception as e:
            logger.error(f"Error getting models: {e}")
            return []

    async def get_generations(self, model_id: int):
        try:
            response = await self._run(
                lambda: self.supabase.table("vehicle_generations")
                .select("*")
                .eq("model_id", model_id)
                .eq("is_active", True)
                .order("start_year", desc=True)
                .execute()
            )

            return response.data or []

        except Exception as e:
            logger.error(f"Error getting generations: {e}")
            return []

    async def get_variants(self, generation_id: int):
        try:
            response = await self._run(
                lambda: self.supabase.table("vehicle_variants")
                .select("*")
                .eq("generation_id", generation_id)
                .eq("is_active", True)
                .order("name")
                .execute()
            )

            return response.data or []

        except Exception as e:
            logger.error(f"Error getting variants: {e}")
            return []

    async def get_variant(self, variant_id: int):
        try:
            response = await self._run(
                lambda: self.supabase.table("vehicle_variants")
                .select("*")
                .eq("id", variant_id)
                .single()
                .execute()
            )

            return response.data

        except Exception as e:
            logger.error(f"Error getting variant: {e}")
            return None

    # ============================================================
    # MASTER VEHICLE DATABASE
    # ============================================================

    async def get_vehicle_master(self, variant_id: int):
        """Return one complete vehicle."""

        try:
            response = await self._run(
                lambda: self.supabase.table("vehicle_master_specs")
                .select("*")
                .eq("variant_id", variant_id)
                .single()
                .execute()
            )

            return response.data

        except Exception as e:
            logger.error(f"Vehicle master lookup failed: {e}")
            return None

    async def search_vehicle_master(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        year: Optional[int] = None,
        fuel: Optional[str] = None,
        transmission: Optional[str] = None,
    ):
        """Search the master vehicle catalogue."""

        try:

            query = self.supabase.table(
                "vehicle_master_specs"
            ).select("*")

            if make:
                query = query.ilike("make_name", f"%{make}%")

            if model:
                query = query.ilike("model_name", f"%{model}%")

            if year:
                query = (
                    query.lte("generation_start_year", year)
                         .gte("generation_end_year", year)
                )

            if fuel:
                query = query.eq("fuel_type_name", fuel)

            if transmission:
                query = query.eq(
                    "transmission_type_name",
                    transmission,
                )

            response = await self._run(
                lambda: query.execute()
            )

            return response.data or []

        except Exception as e:
            logger.error(f"Vehicle search failed: {e}")
            return []

    # ============================================================
    # BASE PRICES
    # ============================================================

    async def get_base_price(self, variant_id: int):
        try:

            response = await self._run(
                lambda: self.supabase.table("vehicle_base_prices")
                .select("*")
                .eq("variant_id", variant_id)
                .single()
                .execute()
            )

            return response.data

        except Exception as e:
            logger.error(f"Base price lookup failed: {e}")
            return None

    async def update_base_price(
        self,
        variant_id: int,
        values: Dict[str, Any],
    ):
        try:

            response = await self._run(
                lambda: self.supabase.table("vehicle_base_prices")
                .update(values)
                .eq("variant_id", variant_id)
                .execute()
            )

            return response.data

        except Exception as e:
            logger.error(f"Base price update failed: {e}")
            raise

    # ============================================================
    # ADMIN
    # ============================================================

    async def get_master_vehicle_count(self):

        response = await self._run(
            lambda: self.supabase.table("vehicle_master_specs")
            .select("variant_id", count="exact")
            .execute()
        )

        return response.count or 0
