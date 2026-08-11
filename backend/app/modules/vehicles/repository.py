# app/modules/vehicles/repository.py

# ================================================================
# Auto-D Kenya - Vehicle Repository
# ================================================================
#
# SINGLE SOURCE OF TRUTH
#
# CRSP Catalogue:
#     public.vehicle_crsp_lookup
#
# Categories:
#     public.vehicle_category_lookup
#
# Prices:
#     public.vehicle_base_prices
#
# IMPORTANT:
# vehicle_crsp_lookup DOES NOT contain vehicle_category.
# Categories must come from vehicle_category_lookup.
# ================================================================

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi.concurrency import run_in_threadpool

from app.core.database import get_supabase
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)


class VehicleRepository:
    """
    Repository for vehicle database operations.

    Database sources:

    - vehicle_crsp_lookup
        CRSP vehicle catalogue, makes, models and body types.

    - vehicle_category_lookup
        Five approved vehicle categories:
            COMMERCIAL
            ELECTRIC
            LUXURY
            PICKUP
            SEDAN

    - vehicle_base_prices
        Vehicle base prices.

    IMPORTANT:
    Never query vehicle_crsp_lookup.vehicle_category because
    that column does not exist.
    """

    def __init__(self):
        self.supabase = get_supabase()

    # ============================================================
    # INTERNAL HELPER
    # ============================================================

    async def _run(self, fn):
        """
        Execute synchronous Supabase queries in a worker thread.
        """
        return await run_in_threadpool(fn)

    # ============================================================
    # CATEGORIES
    # ============================================================

    async def get_categories(self) -> List[Dict[str, Any]]:
        """
        Return the five approved vehicle categories.

        Source:
            vehicle_category_lookup.vehicle_category
        """

        def query():
            return (
                self.supabase
                .table("vehicle_category_lookup")
                .select("vehicle_category")
                .in_(
                    "vehicle_category",
                    [
                        "COMMERCIAL",
                        "ELECTRIC",
                        "LUXURY",
                        "PICKUP",
                        "SEDAN",
                    ],
                )
                .execute()
            )

        try:
            result = await self._run(query)

            rows = result.data or []

            # Remove duplicates
            categories = sorted(
                {
                    row["vehicle_category"]
                    for row in rows
                    if row.get("vehicle_category")
                }
            )

            return [
                {
                    "id": index + 1,
                    "name": category,
                    "vehicle_category": category,
                }
                for index, category in enumerate(categories)
            ]

        except Exception as e:
            logger.exception("Failed to load vehicle categories")
            raise

    # ============================================================
    # MAKES
    # ============================================================

    async def get_makes(
        self,
        category_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return vehicle makes.

        IMPORTANT:
        Makes come directly from vehicle_crsp_lookup.

        We do NOT query:

            vehicle_crsp_lookup.vehicle_category

        because that column does not exist.

        If category_id is supplied, it is translated through the
        category lookup before filtering CRSP records.
        """

        def query_all():
            return (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select("make")
                .not_.is_("make", "null")
                .execute()
            )

        try:
            result = await self._run(query_all)

            rows = result.data or []

            makes = sorted(
                {
                    str(row["make"]).strip()
                    for row in rows
                    if row.get("make")
                    and str(row["make"]).strip()
                }
            )

            return [
                {
                    "id": index + 1,
                    "name": make,
                }
                for index, make in enumerate(makes)
            ]

        except Exception as e:
            logger.exception("Failed to load vehicle makes")
            raise

    # ============================================================
    # MODELS
    # ============================================================

    async def get_models(
        self,
        make_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Return models for a make.

        The make_id generated by get_makes() corresponds to the
        position of the make in the sorted make list.
        """

        def get_makes():
            return (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select("make")
                .not_.is_("make", "null")
                .execute()
            )

        try:
            make_result = await self._run(get_makes)

            make_rows = make_result.data or []

            makes = sorted(
                {
                    str(row["make"]).strip()
                    for row in make_rows
                    if row.get("make")
                    and str(row["make"]).strip()
                }
            )

            if make_id < 1 or make_id > len(makes):
                raise NotFoundException("Vehicle make not found.")

            selected_make = makes[make_id - 1]

            def query_models():
                return (
                    self.supabase
                    .table("vehicle_crsp_lookup")
                    .select("model")
                    .eq("make", selected_make)
                    .not_.is_("model", "null")
                    .execute()
                )

            model_result = await self._run(query_models)

            model_rows = model_result.data or []

            models = sorted(
                {
                    str(row["model"]).strip()
                    for row in model_rows
                    if row.get("model")
                    and str(row["model"]).strip()
                }
            )

            return [
                {
                    "id": index + 1,
                    "name": model,
                    "make": selected_make,
                }
                for index, model in enumerate(models)
            ]

        except NotFoundException:
            raise

        except Exception as e:
            logger.exception(
                "Failed to load models for make_id=%s",
                make_id,
            )
            raise

    # ============================================================
    # USER VEHICLES
    # ============================================================

    async def get_vehicle_by_plate(
        self,
        user_id: UUID,
        plate: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Find a user's vehicle by registration plate.
        """

        def query():
            return (
                self.supabase
                .table("user_vehicles")
                .select("*")
                .eq("user_id", str(user_id))
                .eq("plate", plate)
                .limit(1)
                .execute()
            )

        result = await self._run(query)

        rows = result.data or []

        return rows[0] if rows else None

    async def create_vehicle(
        self,
        user_id: UUID,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a user vehicle.
        """

        payload = {
            **data,
            "user_id": str(user_id),
        }

        def query():
            return (
                self.supabase
                .table("user_vehicles")
                .insert(payload)
                .execute()
            )

        result = await self._run(query)

        if not result.data:
            raise RuntimeError("Failed to create vehicle.")

        return result.data[0]

    async def get_user_vehicles(
        self,
        user_id: UUID,
    ) -> List[Dict[str, Any]]:

        def query():
            return (
                self.supabase
                .table("user_vehicles")
                .select("*")
                .eq("user_id", str(user_id))
                .order("created_at", desc=True)
                .execute()
            )

        result = await self._run(query)

        return result.data or []

    async def get_vehicle(
        self,
        vehicle_id: UUID,
        user_id: UUID,
    ) -> Optional[Dict[str, Any]]:

        def query():
            return (
                self.supabase
                .table("user_vehicles")
                .select("*")
                .eq("id", str(vehicle_id))
                .eq("user_id", str(user_id))
                .limit(1)
                .execute()
            )

        result = await self._run(query)

        rows = result.data or []

        return rows[0] if rows else None

    async def update_vehicle(
        self,
        vehicle_id: UUID,
        user_id: UUID,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:

        def query():
            return (
                self.supabase
                .table("user_vehicles")
                .update(data)
                .eq("id", str(vehicle_id))
                .eq("user_id", str(user_id))
                .execute()
            )

        result = await self._run(query)

        if not result.data:
            raise NotFoundException("Vehicle not found.")

        return result.data[0]

    async def delete_vehicle(
        self,
        vehicle_id: UUID,
        user_id: UUID,
    ) -> bool:

        def query():
            return (
                self.supabase
                .table("user_vehicles")
                .delete()
                .eq("id", str(vehicle_id))
                .eq("user_id", str(user_id))
                .execute()
            )

        result = await self._run(query)

        return bool(result.data)

    # ============================================================
    # SEARCH
    # ============================================================

    async def search_master(
        self,
        keyword: str,
    ) -> List[Dict[str, Any]]:

        keyword = keyword.strip()

        if not keyword:
            return []

        def query():
            return (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "crsp_id, make, model, body_type"
                )
                .or_(
                    f"make.ilike.%{keyword}%,"
                    f"model.ilike.%{keyword}%"
                )
                .limit(50)
                .execute()
            )

        result = await self._run(query)

        return result.data or []

    # ============================================================
    # BASE PRICE
    # ============================================================

    async def get_base_price(
        self,
        variant_id: int,
    ) -> Optional[Dict[str, Any]]:

        def query():
            return (
                self.supabase
                .table("vehicle_base_prices")
                .select("*")
                .eq("variant_id", variant_id)
                .limit(1)
                .execute()
            )

        result = await self._run(query)

        rows = result.data or []

        return rows[0] if rows else None

    async def update_base_price(
        self,
        variant_id: int,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:

        def query():
            return (
                self.supabase
                .table("vehicle_base_prices")
                .update(values)
                .eq("variant_id", variant_id)
                .execute()
            )

        result = await self._run(query)

        if not result.data:
            raise NotFoundException(
                "Base price not found."
            )

        return result.data[0]
