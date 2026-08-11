```python
# app/modules/vehicles/repository.py

# ================================================================
# Auto-D Kenya - Vehicle Repository
# ================================================================
#
# TYPE: MODULE - Database Access Layer
#
# SINGLE SOURCE OF TRUTH
#
# CRSP catalogue:
#     vehicle_crsp_lookup
#
# Categories:
#     vehicle_category_lookup
#
# User vehicles:
#     user_vehicles
#
# Prices:
#     vehicle_base_prices
#
# IMPORTANT:
# vehicle_crsp_lookup DOES NOT contain vehicle_category.
#
# Category relationship:
#
# vehicle_crsp_lookup.body_type
#          ↓
# vehicle_category_lookup.body_type
#          ↓
# vehicle_category_lookup.vehicle_category
#
# Approved application categories:
#     COMMERCIAL
#     ELECTRIC
#     LUXURY
#     PICKUP
#     SEDAN
#
# ================================================================

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi.concurrency import run_in_threadpool

from app.core.database import get_supabase


logger = logging.getLogger(__name__)


class VehicleRepository:
    """
    Repository for vehicle database operations.

    All Supabase access for the vehicles module belongs here.
    """

    # ============================================================
    # CONSTANTS
    # ============================================================

    VALID_CATEGORIES = (
        "COMMERCIAL",
        "ELECTRIC",
        "LUXURY",
        "PICKUP",
        "SEDAN",
    )

    # ============================================================
    # INITIALIZATION
    # ============================================================

    def __init__(self):
        self.supabase = get_supabase()

    # ============================================================
    # THREAD HELPER
    # ============================================================

    async def _run(self, fn):
        """
        Execute synchronous Supabase operations in a worker thread.
        """
        return await run_in_threadpool(fn)

    # ============================================================
    # CATEGORIES
    # ============================================================

    async def get_categories(self) -> List[Dict[str, Any]]:
        """
        Return the five approved vehicle categories.

        Categories are obtained from vehicle_category_lookup.

        No reference is made to:
            vehicle_crsp_lookup.vehicle_category
        """

        def query():
            response = (
                self.supabase
                .table("vehicle_category_lookup")
                .select(
                    "vehicle_category"
                )
                .in_(
                    "vehicle_category",
                    list(self.VALID_CATEGORIES)
                )
                .execute()
            )

            return response.data or []

        rows = await self._run(query)

        # Return unique categories.
        categories = sorted(
            {
                str(row.get("vehicle_category", "")).strip().upper()
                for row in rows
                if row.get("vehicle_category")
            }
        )

        return [
            {
                "id": index + 1,
                "name": category,
                "description": None,
                "icon": None,
                "vehicle_count": 0,
            }
            for index, category in enumerate(categories)
        ]

    # ============================================================
    # MAKES
    # ============================================================

    async def get_makes(
        self,
        category_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return unique vehicle makes from CRSP.

        If category_id is supplied, the category is resolved through
        vehicle_category_lookup.body_type.

        IMPORTANT:
        The CRSP table is NOT queried for vehicle_category.
        """

        category_name = None

        if category_id is not None:
            categories = await self.get_categories()

            for category in categories:
                if category["id"] == category_id:
                    category_name = category["name"]
                    break

            if category_name is None:
                return []

        def query():
            response = (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "crsp_id,make,body_type"
                )
                .order(
                    "make",
                    desc=False
                )
                .execute()
            )

            return response.data or []

        rows = await self._run(query)

        # --------------------------------------------------------
        # Build category body-type map
        # --------------------------------------------------------

        category_body_types = {}

        if category_name:
            def category_query():
                response = (
                    self.supabase
                    .table("vehicle_category_lookup")
                    .select(
                        "body_type,vehicle_category"
                    )
                    .eq(
                        "vehicle_category",
                        category_name
                    )
                    .execute()
                )

                return response.data or []

            mapping_rows = await self._run(category_query)

            category_body_types = {
                str(row.get("body_type", "")).strip().upper()
                for row in mapping_rows
                if row.get("body_type")
            }

        # --------------------------------------------------------
        # Aggregate makes
        # --------------------------------------------------------

        makes = {}

        for row in rows:
            make = row.get("make")

            if not make:
                continue

            make = str(make).strip().upper()

            if not make:
                continue

            # Apply category filter through body_type.
            if category_name:
                body_type = str(
                    row.get("body_type") or ""
                ).strip().upper()

                if body_type not in category_body_types:
                    continue

            if make not in makes:
                makes[make] = {
                    "id": None,
                    "name": make,
                    "country": None,
                    "logo_url": None,
                    "vehicle_count": 0,
                    "category_id": category_id,
                }

            makes[make]["vehicle_count"] += 1

        return sorted(
            makes.values(),
            key=lambda item: item["name"]
        )

    # ============================================================
    # MODELS
    # ============================================================

    async def get_models(
        self,
        make_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Return models for a make.

        make_id is treated as the position/ID returned by the API.
        The actual CRSP source is vehicle_crsp_lookup.make.
        """

        makes = await self.get_makes()

        selected_make = next(
            (
                make
                for make in makes
                if make["id"] == make_id
            ),
            None,
        )

        if not selected_make:
            return []

        make_name = selected_make["name"]

        def query():
            response = (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "crsp_id,make,model,body_type"
                )
                .eq(
                    "make",
                    make_name
                )
                .order(
                    "model",
                    desc=False
                )
                .execute()
            )

            return response.data or []

        rows = await self._run(query)

        models = {}

        for row in rows:
            model = row.get("model")

            if not model:
                continue

            model = str(model).strip()

            if not model:
                continue

            key = model.upper()

            if key not in models:
                models[key] = {
                    "id": row.get("crsp_id"),
                    "name": model,
                    "make_id": make_id,
                    "make_name": make_name,
                    "vehicle_count": 0,
                    "body_type": row.get("body_type"),
                    "start_year": None,
                    "end_year": None,
                }

            models[key]["vehicle_count"] += 1

        return sorted(
            models.values(),
            key=lambda item: item["name"].upper()
        )

    # ============================================================
    # MASTER SEARCH
    # ============================================================

    async def search_master(
        self,
        keyword: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search CRSP by make or model.
        """

        keyword = keyword.strip()

        if not keyword:
            return []

        def query():
            response = (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "crsp_id,"
                    "make,"
                    "model,"
                    "crsp_fuel,"
                    "engine_capacity,"
                    "engine_capacity_cc,"
                    "engine_code,"
                    "transmission,"
                    "body_type,"
                    "crsp_price"
                )
                .or_(
                    f"make.ilike.%{keyword}%,"
                    f"model.ilike.%{keyword}%"
                )
                .limit(limit)
                .execute()
            )

            return response.data or []

        return await self._run(query)

    # ============================================================
    # VARIANT
    # ============================================================

    async def get_variant(
        self,
        variant_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a CRSP vehicle record by CRSP ID.
        """

        def query():
            response = (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select("*")
                .eq(
                    "crsp_id",
                    variant_id
                )
                .limit(1)
                .execute()
            )

            return response.data or []

        rows = await self._run(query)

        return rows[0] if rows else None

    # ============================================================
    # BASE PRICE
    # ============================================================

    async def get_base_price(
        self,
        variant_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Get CRSP/base price for a vehicle.

        First attempts vehicle_base_prices.
        """

        def query():
            response = (
                self.supabase
                .table("vehicle_base_prices")
                .select("*")
                .eq(
                    "crsp_id",
                    variant_id
                )
                .limit(1)
                .execute()
            )

            return response.data or []

        rows = await self._run(query)

        return rows[0] if rows else None

    async def update_base_price(
        self,
        variant_id: int,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update vehicle base price.
        """

        def query():
            response = (
                self.supabase
                .table("vehicle_base_prices")
                .update(values)
                .eq(
                    "crsp_id",
                    variant_id
                )
                .execute()
            )

            return response.data or []

        rows = await self._run(query)

        return rows[0] if rows else {}

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
            response = (
                self.supabase
                .table("user_vehicles")
                .select("*")
                .eq(
                    "user_id",
                    str(user_id)
                )
                .eq(
                    "plate",
                    plate
                )
                .limit(1)
                .execute()
            )

            return response.data or []

        rows = await self._run(query)

        return rows[0] if rows else None

    async def get_user_vehicles(
        self,
        user_id: UUID,
    ) -> List[Dict[str, Any]]:
        """
        Get all vehicles belonging to a user.
        """

        def query():
            response = (
                self.supabase
                .table("user_vehicles")
                .select("*")
                .eq(
                    "user_id",
                    str(user_id)
                )
                .order(
                    "created_at",
                    desc=True
                )
                .execute()
            )

            return response.data or []

        return await self._run(query)

    async def get_vehicle(
        self,
        vehicle_id: UUID,
        user_id: UUID,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific user vehicle.
        """

        def query():
            response = (
                self.supabase
                .table("user_vehicles")
                .select("*")
                .eq(
                    "id",
                    str(vehicle_id)
                )
                .eq(
                    "user_id",
                    str(user_id)
                )
                .limit(1)
                .execute()
            )

            return response.data or []

        rows = await self._run(query)

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
            response = (
                self.supabase
                .table("user_vehicles")
                .insert(payload)
                .execute()
            )

            return response.data or []

        rows = await self._run(query)

        return rows[0] if rows else {}

    async def update_vehicle(
        self,
        vehicle_id: UUID,
        user_id: UUID,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update a user vehicle.
        """

        def query():
            response = (
                self.supabase
                .table("user_vehicles")
                .update(data)
                .eq(
                    "id",
                    str(vehicle_id)
                )
                .eq(
                    "user_id",
                    str(user_id)
                )
                .execute()
            )

            return response.data or []

        rows = await self._run(query)

        return rows[0] if rows else {}

    async def delete_vehicle(
        self,
        vehicle_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Delete a user vehicle.
        """

        def query():
            response = (
                self.supabase
                .table("user_vehicles")
                .delete()
                .eq(
                    "id",
                    str(vehicle_id)
                )
                .eq(
                    "user_id",
                    str(user_id)
                )
                .execute()
            )

            return response.data or []

        rows = await self._run(query)

        return bool(rows)

    # ============================================================
    # HEALTH
    # ============================================================

    async def health_check(self) -> Dict[str, Any]:
        """
        Check CRSP database connectivity.
        """

        def query():
            response = (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "crsp_id",
                    count="exact"
                )
                .limit(1)
                .execute()
            )

            return response.count or 0

        try:
            count = await self._run(query)

            return {
                "status": "healthy",
                "database": "connected",
                "crsp_records": count,
            }

        except Exception as exc:
            logger.exception(
                "Vehicle repository health check failed"
            )

            return {
                "status": "degraded",
                "database": "error",
                "crsp_records": None,
                "error": str(exc),
            }
```
