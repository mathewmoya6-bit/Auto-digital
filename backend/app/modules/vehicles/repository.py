# app/modules/vehicles/repository.py

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi.concurrency import run_in_threadpool

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class VehicleRepository:
    """
    Auto-D Kenya Vehicle Repository.

    SINGLE SOURCE OF TRUTH
    ----------------------
    Master vehicle data:
        public.vehicle_crsp_lookup

    User vehicles:
        public.user_vehicles

    CRSP prices:
        public.vehicle_crsp_prices / vehicle_crsp_lookup.crsp_kes

    IMPORTANT:
    vehicle_crsp_lookup does NOT contain vehicle_category.
    """

    def __init__(self):
        self.supabase = get_supabase()

    async def _run(self, fn):
        return await run_in_threadpool(fn)

    # ============================================================
    # CATEGORIES
    # ============================================================

    async def get_categories(self) -> List[Dict[str, Any]]:
        """
        Return the application's five approved vehicle categories.

        Categories are NOT read from vehicle_crsp_lookup because
        that view has no vehicle_category column.
        """

        return [
            {
                "id": 1,
                "name": "COMMERCIAL",
                "description": "Commercial and heavy-use vehicles",
                "icon": None,
                "vehicle_count": 0,
            },
            {
                "id": 2,
                "name": "ELECTRIC",
                "description": "Electric vehicles",
                "icon": None,
                "vehicle_count": 0,
            },
            {
                "id": 3,
                "name": "LUXURY",
                "description": "Luxury vehicles",
                "icon": None,
                "vehicle_count": 0,
            },
            {
                "id": 4,
                "name": "PICKUP",
                "description": "Pickup vehicles",
                "icon": None,
                "vehicle_count": 0,
            },
            {
                "id": 5,
                "name": "SEDAN",
                "description": "Passenger and sedan-class vehicles",
                "icon": None,
                "vehicle_count": 0,
            },
        ]

    # ============================================================
    # MAKES
    # ============================================================

    async def get_makes(
        self,
        category_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:

        def query():
            result = (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select("make,make_id")
                .not_.is_("make", "null")
                .order("make")
                .execute()
            )
            return result.data or []

        rows = await self._run(query)

        # Aggregate unique makes
        makes = {}

        for row in rows:
            name = (row.get("make") or "").strip()

            if not name:
                continue

            make_id = row.get("make_id")

            key = name.upper()

            if key not in makes:
                makes[key] = {
                    "id": make_id,
                    "name": name,
                    "country": None,
                    "logo_url": None,
                    "vehicle_count": 0,
                    "category_id": None,
                }

            makes[key]["vehicle_count"] += 1

            if makes[key]["id"] is None and make_id is not None:
                makes[key]["id"] = make_id

        return sorted(
            makes.values(),
            key=lambda x: x["name"].upper()
        )

    # ============================================================
    # MODELS
    # ============================================================

    async def get_models(
        self,
        make_id: int,
    ) -> List[Dict[str, Any]]:

        def query():
            return (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "model,model_id,make,make_id,body_type,"
                    "manufacture_year"
                )
                .eq("make_id", make_id)
                .not_.is_("model", "null")
                .order("model")
                .execute()
            ).data or []

        rows = await self._run(query)

        models = {}

        for row in rows:
            model = (row.get("model") or "").strip()

            if not model:
                continue

            model_id = row.get("model_id")
            key = model.upper()

            if key not in models:
                models[key] = {
                    "id": model_id,
                    "name": model,
                    "make_id": row.get("make_id"),
                    "make_name": row.get("make"),
                    "vehicle_count": 0,
                    "body_type": row.get("body_type"),
                    "start_year": row.get("manufacture_year"),
                    "end_year": row.get("manufacture_year"),
                }

            models[key]["vehicle_count"] += 1

            year = row.get("manufacture_year")

            if year:
                if not models[key]["start_year"]:
                    models[key]["start_year"] = year

                if not models[key]["end_year"]:
                    models[key]["end_year"] = year

                models[key]["start_year"] = min(
                    models[key]["start_year"],
                    year
                )

                models[key]["end_year"] = max(
                    models[key]["end_year"],
                    year
                )

        return sorted(
            models.values(),
            key=lambda x: x["name"].upper()
        )

    # ============================================================
    # GENERATIONS
    # ============================================================

    async def get_generations(
        self,
        model_id: int,
    ) -> List[Dict[str, Any]]:

        def query():
            return (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "generation_id,model_id,model,"
                    "manufacture_year,crsp_year"
                )
                .eq("model_id", model_id)
                .not_.is_("generation_id", "null")
                .order("generation_id")
                .execute()
            ).data or []

        rows = await self._run(query)

        generations = {}

        for row in rows:
            generation_id = row.get("generation_id")

            if generation_id is None:
                continue

            if generation_id not in generations:
                generations[generation_id] = {
                    "id": generation_id,
                    "code": str(generation_id),
                    "start_year": None,
                    "end_year": None,
                    "model_id": model_id,
                    "model_name": row.get("model"),
                    "variant_count": 0,
                }

            generations[generation_id]["variant_count"] += 1

            year = row.get("manufacture_year") or row.get("crsp_year")

            if year:
                current_start = generations[generation_id]["start_year"]
                current_end = generations[generation_id]["end_year"]

                generations[generation_id]["start_year"] = (
                    year
                    if current_start is None
                    else min(current_start, year)
                )

                generations[generation_id]["end_year"] = (
                    year
                    if current_end is None
                    else max(current_end, year)
                )

        return list(generations.values())

    # ============================================================
    # VARIANTS
    # ============================================================

    async def get_variants(
        self,
        generation_id: int,
    ) -> List[Dict[str, Any]]:

        def query():
            return (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select("*")
                .eq("generation_id", generation_id)
                .order("crsp_id")
                .execute()
            ).data or []

        rows = await self._run(query)

        variants = []

        for row in rows:
            variants.append({
                "crsp_id": row.get("crsp_id"),
                "variant_id": row.get("crsp_id"),
                "variant_name": row.get("model"),
                "trim_level": None,
                "engine_size_cc": None,
                "engine_code": None,
                "fuel_type_name": row.get("fuel"),
                "transmission_type_name": row.get("transmission"),
                "body_type_name": row.get("body_type"),
                "make_name": row.get("make"),
                "model_name": row.get("model"),
                "generation_id": row.get("generation_id"),
                "crsp_kes": row.get("crsp_kes"),
                "estimated_value": None,
                "market_value": None,
                "base_price": row.get("crsp_kes"),
                "dealer_price": None,
            })

        return variants

    # ============================================================
    # SINGLE VARIANT
    # ============================================================

    async def get_variant(
        self,
        variant_id: int,
    ) -> Optional[Dict[str, Any]]:

        def query():
            result = (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select("*")
                .eq("crsp_id", variant_id)
                .limit(1)
                .execute()
            )

            return result.data[0] if result.data else None

        row = await self._run(query)

        if not row:
            return None

        return {
            "crsp_id": row.get("crsp_id"),
            "variant_id": row.get("crsp_id"),
            "variant_name": row.get("model"),
            "trim_level": None,
            "engine_size_cc": row.get("engine_capacity_id"),
            "engine_code": None,
            "fuel_type_name": row.get("fuel"),
            "transmission_type_name": row.get("transmission"),
            "body_type_name": row.get("body_type"),
            "make_name": row.get("make"),
            "model_name": row.get("model"),
            "generation_id": row.get("generation_id"),
            "crsp_kes": row.get("crsp_kes"),
            "estimated_value": None,
            "market_value": None,
            "base_price": row.get("crsp_kes"),
            "dealer_price": None,
        }

    # ============================================================
    # VEHICLE MASTER
    # ============================================================

    async def get_vehicle_master(
        self,
        variant_id: int,
    ) -> Optional[Dict[str, Any]]:

        return await self.get_variant(variant_id)

    # ============================================================
    # SEARCH
    # ============================================================

    async def search_master(
        self,
        keyword: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:

        keyword = keyword.strip()

        if not keyword:
            return []

        def query():
            return (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "crsp_id,make,model,fuel,engine_capacity,"
                    "transmission,crsp_kes,body_type"
                )
                .or_(
                    f"make.ilike.%{keyword}%,"
                    f"model.ilike.%{keyword}%"
                )
                .order("make")
                .limit(limit)
                .execute()
            ).data or []

        rows = await self._run(query)

        return [
            {
                "crsp_id": row.get("crsp_id"),
                "make": row.get("make"),
                "model": row.get("model"),
                "crsp_fuel": row.get("fuel"),
                "engine_capacity": row.get("engine_capacity"),
                "engine_capacity_cc": None,
                "engine_code": None,
                "transmission": row.get("transmission"),
                "crsp_price": row.get("crsp_kes"),
                "similarity_score": None,
            }
            for row in rows
        ]

    # ============================================================
    # BASE PRICE
    # ============================================================

    async def get_base_price(
        self,
        variant_id: int,
    ) -> Optional[Dict[str, Any]]:

        def query():
            result = (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "crsp_id,make,model,engine_capacity,"
                    "fuel,transmission,crsp_kes,currency,"
                    "effective_date,crsp_year"
                )
                .eq("crsp_id", variant_id)
                .limit(1)
                .execute()
            )

            return result.data[0] if result.data else None

        row = await self._run(query)

        if not row:
            return None

        return {
            "crsp_id": row.get("crsp_id"),
            "make": row.get("make"),
            "model": row.get("model"),
            "engine_capacity": row.get("engine_capacity"),
            "engine_capacity_cc": None,
            "engine_code": None,
            "crsp_fuel": row.get("fuel"),
            "transmission": row.get("transmission"),
            "base_price": float(row.get("crsp_kes") or 0),
            "crsp_price": float(row.get("crsp_kes") or 0),
            "currency": row.get("currency") or "KES",
            "source": "CRSP",
            "last_updated": None,
            "year": row.get("crsp_year"),
        }

    # ============================================================
    # USER VEHICLES
    # ============================================================

    async def get_vehicle_by_plate(
        self,
        user_id: UUID,
        plate: str,
    ):
        def query():
            result = (
                self.supabase
                .table("user_vehicles")
                .select("*")
                .eq("user_id", str(user_id))
                .eq("plate", plate)
                .limit(1)
                .execute()
            )

            return result.data[0] if result.data else None

        return await self._run(query)

    async def get_user_vehicles(
        self,
        user_id: UUID,
    ):

        def query():
            return (
                self.supabase
                .table("user_vehicles")
                .select("*")
                .eq("user_id", str(user_id))
                .order("created_at", desc=True)
                .execute()
            ).data or []

        return await self._run(query)

    async def get_vehicle(
        self,
        vehicle_id: UUID,
        user_id: UUID,
    ):

        def query():
            result = (
                self.supabase
                .table("user_vehicles")
                .select("*")
                .eq("id", str(vehicle_id))
                .eq("user_id", str(user_id))
                .limit(1)
                .execute()
            )

            return result.data[0] if result.data else None

        return await self._run(query)

    async def create_vehicle(
        self,
        user_id: UUID,
        data: Dict[str, Any],
    ):

        payload = dict(data)
        payload["user_id"] = str(user_id)

        def query():
            result = (
                self.supabase
                .table("user_vehicles")
                .insert(payload)
                .execute()
            )

            return result.data[0] if result.data else None

        return await self._run(query)

    async def update_vehicle(
        self,
        vehicle_id: UUID,
        user_id: UUID,
        data: Dict[str, Any],
    ):

        def query():
            result = (
                self.supabase
                .table("user_vehicles")
                .update(data)
                .eq("id", str(vehicle_id))
                .eq("user_id", str(user_id))
                .execute()
            )

            return result.data[0] if result.data else None

        return await self._run(query)

    async def delete_vehicle(
        self,
        vehicle_id: UUID,
        user_id: UUID,
    ) -> bool:

        def query():
            result = (
                self.supabase
                .table("user_vehicles")
                .delete()
                .eq("id", str(vehicle_id))
                .eq("user_id", str(user_id))
                .execute()
            )

            return bool(result.data)

        return await self._run(query)

    # ============================================================
    # STATISTICS
    # ============================================================

    async def get_statistics(self):

        def query():
            return (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "crsp_id,make,model,fuel,transmission,"
                    "engine_capacity,crsp_kes,crsp_year"
                )
                .execute()
            ).data or []

        rows = await self._run(query)

        makes = {
            str(r.get("make")).strip().upper()
            for r in rows
            if r.get("make")
        }

        models = {
            (
                str(r.get("make")).strip().upper(),
                str(r.get("model")).strip().upper()
            )
            for r in rows
            if r.get("make") and r.get("model")
        }

        fuels = {
            str(r.get("fuel")).strip().upper()
            for r in rows
            if r.get("fuel")
        }

        transmissions = {
            str(r.get("transmission")).strip().upper()
            for r in rows
            if r.get("transmission")
        }

        capacities = {
            str(r.get("engine_capacity")).strip()
            for r in rows
            if r.get("engine_capacity")
        }

        prices = [
            float(r["crsp_kes"])
            for r in rows
            if r.get("crsp_kes") is not None
        ]

        return {
            "total_vehicles": len(rows),
            "total_makes": len(makes),
            "total_models": len(models),
            "total_engine_capacities": len(capacities),
            "total_fuel_types": len(fuels),
            "total_transmissions": len(transmissions),
            "makes_by_category": {},
            "vehicles_by_year": {},
            "vehicles_by_fuel_type": {},
            "vehicles_by_transmission": {},
            "vehicles_by_engine_capacity": {},
            "average_crsp_price": (
                sum(prices) / len(prices) if prices else 0
            ),
            "min_crsp_price": min(prices) if prices else 0,
            "max_crsp_price": max(prices) if prices else 0,
            "average_price": (
                sum(prices) / len(prices) if prices else 0
            ),
            "min_price": min(prices) if prices else 0,
            "max_price": max(prices) if prices else 0,
            "last_updated": None,
        }

    # ============================================================
    # HEALTH
    # ============================================================

    async def health_check(self):

        def query():
            result = (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select("crsp_id")
                .limit(1)
                .execute()
            )

            return bool(result.data)

        try:
            healthy = await self._run(query)

            return {
                "status": "healthy" if healthy else "degraded",
                "database": "connected",
                "crsp_records": None,
            }

        except Exception as exc:
            logger.exception("Vehicle health check failed")

            return {
                "status": "degraded",
                "database": "error",
                "crsp_records": None,
                "error": str(exc),
            }
