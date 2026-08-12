# ================================================================
# Auto-D Kenya - Vehicle Repository
# ================================================================
# CRSP-driven vehicle catalogue repository.
#
# SINGLE SOURCE OF TRUTH
# ----------------------
# Vehicle identity:
#   public.vehicle_crsp_lookup
#
# Category:
#   public.vehicle_category_lookup
#   public.vehicle_body_type_mapping
#
# IMPORTANT:
#   vehicle_crsp_lookup.vehicle_category does NOT exist.
# ================================================================

import logging
from typing import Optional, List, Dict, Any

from fastapi.concurrency import run_in_threadpool

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class VehicleRepository:
    """
    Repository for CRSP vehicle catalogue operations.

    CRSP is the authoritative source for vehicle identity,
    make, model and CRSP pricing.
    """

    def __init__(self):
        self.supabase = get_supabase()

    # ============================================================
    # THREAD EXECUTOR
    # ============================================================

    async def _run(self, fn):
        """Execute synchronous Supabase operations in a worker thread."""
        return await run_in_threadpool(fn)

    # ============================================================
    # CATEGORIES
    # ============================================================

    async def get_categories(self) -> List[Dict[str, Any]]:
        """
        Return the approved application vehicle categories.
        """

        def query():
            return (
                self.supabase
                .table("vehicle_category_lookup")
                .select(
                    "id, body_type, vehicle_category, "
                    "category_confidence, category_source"
                )
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
                .order("vehicle_category")
                .execute()
            )

        response = await self._run(query)
        rows = response.data or []

        categories = {}

        for row in rows:
            category = row.get("vehicle_category")

            if not category:
                continue

            category = category.strip().upper()

            if category not in categories:
                categories[category] = {
                    "id": len(categories) + 1,
                    "name": category,
                    "description": None,
                    "icon": None,
                    "vehicle_count": 0,
                }

            categories[category]["vehicle_count"] += 1

        return list(categories.values())

    # ============================================================
    # MAKES
    # ============================================================

    async def get_makes(
        self,
        category_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return ALL unique vehicle makes from CRSP.

        CRSP is the authoritative source for make identity.

        IMPORTANT:
        - No pagination.
        - No hardcoded make list.
        - No vehicle_crsp_lookup.vehicle_category reference.
        - Deduplication is based on make_id.
        """

        def query():
            return (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select("make, make_id")
                .not_.is_("make", "null")
                .not_.is_("make_id", "null")
                .eq("is_duplicate", False)
                .order("make")
                .execute()
            )

        response = await self._run(query)
        rows = response.data or []

        makes: Dict[int, Dict[str, Any]] = {}

        for row in rows:
            make_id = row.get("make_id")
            make_name = row.get("make")

            if make_id is None or not make_name:
                continue

            name = str(make_name).strip().upper()

            if not name:
                continue

            if make_id not in makes:
                makes[make_id] = {
                    "id": make_id,
                    "name": name,
                    "country": None,
                    "logo_url": None,
                    "vehicle_count": 0,
                    "category_id": category_id,
                }

            makes[make_id]["vehicle_count"] += 1

        result = sorted(
            makes.values(),
            key=lambda item: item["name"],
        )

        logger.info(
            "Vehicle makes loaded: %s unique makes",
            len(result),
        )

        return result

    # ============================================================
    # MODELS
    # ============================================================

    async def get_models(
        self,
        make_id: int,
    ) -> List[Dict[str, Any]]:
        """Return unique models belonging to a CRSP make."""

        def query():
            return (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "model_id, model, make_id, make, body_type"
                )
                .eq("make_id", make_id)
                .eq("is_duplicate", False)
                .not_.is_("model", "null")
                .order("model")
                .execute()
            )

        response = await self._run(query)
        rows = response.data or []

        models: Dict[Any, Dict[str, Any]] = {}

        for row in rows:
            model_id = row.get("model_id")
            model_name = row.get("model")

            if not model_name:
                continue

            model_name = str(model_name).strip()

            if not model_name:
                continue

            key = model_id if model_id is not None else model_name.upper()

            if key not in models:
                models[key] = {
                    "id": model_id,
                    "name": model_name,
                    "make_id": row.get("make_id"),
                    "make_name": row.get("make"),
                    "vehicle_count": 0,
                    "body_type": row.get("body_type"),
                    "start_year": None,
                    "end_year": None,
                }

            models[key]["vehicle_count"] += 1

        return sorted(
            models.values(),
            key=lambda item: item["name"].upper(),
        )

    # ============================================================
    # VEHICLE SEARCH
    # ============================================================

    async def search_vehicles(
        self,
        search: Optional[str] = None,
        make_id: Optional[int] = None,
        model_id: Optional[int] = None,
        fuel: Optional[str] = None,
        transmission: Optional[str] = None,
        engine_capacity_cc: Optional[int] = None,
        year: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Search the CRSP vehicle catalogue."""

        def query():
            q = (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "crsp_id, "
                    "make, "
                    "make_id, "
                    "model, "
                    "normalized_model, "
                    "model_id, "
                    "master_model_id, "
                    "master_model_name, "
                    "generation_id, "
                    "engine_capacity_id, "
                    "engine_capacity, "
                    "fuel, "
                    "transmission, "
                    "drive_configuration, "
                    "body_type, "
                    "manufacture_year, "
                    "crsp_year, "
                    "crsp_kes, "
                    "currency, "
                    "source"
                )
                .eq("is_duplicate", False)
            )

            if make_id is not None:
                q = q.eq("make_id", make_id)

            if model_id is not None:
                q = q.eq("model_id", model_id)

            if fuel:
                q = q.ilike("fuel", f"%{fuel}%")

            if transmission:
                q = q.ilike(
                    "transmission",
                    f"%{transmission}%",
                )

            if engine_capacity_cc is not None:
                logger.warning(
                    "engine_capacity_cc filter requested, "
                    "but vehicle_crsp_lookup does not contain "
                    "engine_capacity_cc. Filter ignored."
                )

            if year is not None:
                q = q.eq("crsp_year", year)

            if search:
                pattern = f"%{search}%"

                q = q.or_(
                    f"make.ilike.{pattern},"
                    f"model.ilike.{pattern},"
                    f"normalized_model.ilike.{pattern},"
                    f"master_model_name.ilike.{pattern}"
                )

            return (
                q
                .order("make")
                .order("model")
                .range(
                    offset,
                    offset + limit - 1,
                )
                .execute()
            )

        response = await self._run(query)

        return response.data or []

    # ============================================================
    # SINGLE VEHICLE
    # ============================================================

    async def get_vehicle(
        self,
        crsp_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Return one CRSP vehicle by authoritative CRSP ID."""

        def query():
            return (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "crsp_id, "
                    "make, "
                    "make_id, "
                    "model, "
                    "normalized_model, "
                    "model_id, "
                    "master_model_id, "
                    "master_model_name, "
                    "generation_id, "
                    "engine_capacity_id, "
                    "engine_capacity, "
                    "fuel, "
                    "transmission, "
                    "drive_configuration, "
                    "body_type, "
                    "manufacture_year, "
                    "crsp_year, "
                    "crsp_kes, "
                    "currency, "
                    "source, "
                    "effective_date"
                )
                .eq("crsp_id", crsp_id)
                .eq("is_duplicate", False)
                .limit(1)
                .execute()
            )

        response = await self._run(query)
        rows = response.data or []

        return rows[0] if rows else None

    # ============================================================
    # BASE PRICE
    # ============================================================

    async def get_base_price(
        self,
        crsp_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Return CRSP price information."""

        vehicle = await self.get_vehicle(crsp_id)

        if not vehicle:
            return None

        price = vehicle.get("crsp_kes")

        return {
            "crsp_id": vehicle.get("crsp_id"),
            "make": vehicle.get("make"),
            "model": vehicle.get("model"),
            "engine_capacity": vehicle.get("engine_capacity"),
            "engine_capacity_cc": None,
            "engine_code": None,
            "crsp_fuel": vehicle.get("fuel"),
            "transmission": vehicle.get("transmission"),
            "base_price": float(price or 0),
            "crsp_price": float(price or 0),
            "currency": vehicle.get("currency") or "KES",
            "source": vehicle.get("source") or "CRSP",
            "last_updated": vehicle.get("effective_date"),
            "year": (
                vehicle.get("crsp_year")
                or vehicle.get("manufacture_year")
            ),
        }

    # ============================================================
    # STATISTICS
    # ============================================================

    async def get_statistics(self) -> Dict[str, Any]:
        """Return basic CRSP catalogue statistics."""

        def query():
            return (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "crsp_id, make, model, fuel, "
                    "transmission, crsp_kes"
                )
                .eq("is_duplicate", False)
                .execute()
            )

        response = await self._run(query)
        rows = response.data or []

        makes = set()
        models = set()
        fuels = set()
        transmissions = set()
        prices = []

        for row in rows:
            if row.get("make"):
                makes.add(str(row["make"]).strip().upper())

            if row.get("model"):
                models.add(str(row["model"]).strip().upper())

            if row.get("fuel"):
                fuels.add(str(row["fuel"]).strip().upper())

            if row.get("transmission"):
                transmissions.add(
                    str(row["transmission"]).strip().upper()
                )

            price = row.get("crsp_kes")

            if price is not None:
                try:
                    prices.append(float(price))
                except (TypeError, ValueError):
                    pass

        average_price = (
            sum(prices) / len(prices)
            if prices
            else 0
        )

        return {
            "total_vehicles": len(rows),
            "total_makes": len(makes),
            "total_models": len(models),
            "total_engine_capacities": 0,
            "total_fuel_types": len(fuels),
            "total_transmissions": len(transmissions),
            "makes_by_category": {},
            "vehicles_by_year": {},
            "vehicles_by_fuel_type": {},
            "vehicles_by_transmission": {},
            "vehicles_by_engine_capacity": {},
            "average_crsp_price": average_price,
            "min_crsp_price": min(prices) if prices else 0,
            "max_crsp_price": max(prices) if prices else 0,
            "average_price": average_price,
            "min_price": min(prices) if prices else 0,
            "max_price": max(prices) if prices else 0,
            "last_updated": None,
        }

    # ============================================================
    # HEALTH
    # ============================================================

    async def health_check(self) -> Dict[str, Any]:
        """Verify that the CRSP catalogue is accessible."""

        def query():
            return (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select("crsp_id", count="exact")
                .limit(1)
                .execute()
            )

        try:
            response = await self._run(query)

            return {
                "status": "healthy",
                "service": "vehicles",
                "version": "2.0",
                "database": "connected",
                "crsp_records": response.count or 0,
            }

        except Exception as exc:
            logger.exception(
                "Vehicle repository health check failed"
            )

            return {
                "status": "degraded",
                "service": "vehicles",
                "version": "2.0",
                "database": "error",
                "crsp_records": 0,
                "error": str(exc),
            }
