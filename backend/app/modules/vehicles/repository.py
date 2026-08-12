
# app/modules/vehicles/repository.py
# ================================================================
# Auto-D Kenya - Vehicle Repository
# ================================================================
# CRSP-driven vehicle catalogue repository.
#
# Source of truth:
#     public.vehicle_crsp_lookup
#
# Important:
#     Supabase/PostgREST may limit individual responses.
#     This repository therefore paginates large queries explicitly.
# ================================================================

import logging
from typing import Optional, List, Dict, Any, Callable

from fastapi.concurrency import run_in_threadpool

from app.core.database import get_supabase


logger = logging.getLogger(__name__)


class VehicleRepository:
    """
    CRSP vehicle catalogue repository.

    CRSP is the authoritative source for:
        - vehicle identity
        - make
        - model
        - specifications
        - CRSP price
        - vehicle power information
    """

    PAGE_SIZE = 1000

    def __init__(self):
        self.supabase = get_supabase()

    # ============================================================
    # THREADPOOL HELPER
    # ============================================================

    async def _run(self, fn: Callable):
        """
        Execute synchronous Supabase operations without blocking
        the FastAPI event loop.
        """
        return await run_in_threadpool(fn)

    # ============================================================
    # CATEGORIES
    # ============================================================

    async def get_categories(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Return the approved vehicle categories.

        Source:
            public.vehicle_category_lookup

        Categories:
            COMMERCIAL
            ELECTRIC
            LUXURY
            PICKUP
            SEDAN

        The query is paginated so it is not dependent on the
        Supabase/PostgREST default row limit.
        """

        allowed_categories = [
            "COMMERCIAL",
            "ELECTRIC",
            "LUXURY",
            "PICKUP",
            "SEDAN",
        ]

        categories: Dict[str, Dict[str, Any]] = {}

        offset = 0

        try:
            while True:

                def query(start=offset):
                    return (
                        self.supabase
                        .table("vehicle_category_lookup")
                        .select(
                            "id, body_type, vehicle_category, "
                            "category_confidence, category_source"
                        )
                        .in_(
                            "vehicle_category",
                            allowed_categories,
                        )
                        .order("vehicle_category")
                        .range(
                            start,
                            start + self.PAGE_SIZE - 1,
                        )
                        .execute()
                    )

                response = await self._run(query)

                rows = response.data or []

                if not rows:
                    break

                for row in rows:

                    category = row.get("vehicle_category")

                    if not category:
                        continue

                    category = str(category).strip().upper()

                    if category not in allowed_categories:
                        continue

                    if category not in categories:
                        categories[category] = {
                            "id": len(categories) + 1,
                            "name": category,
                            "description": None,
                            "icon": None,
                            "vehicle_count": 0,
                        }

                    categories[category]["vehicle_count"] += 1

                if len(rows) < self.PAGE_SIZE:
                    break

                offset += self.PAGE_SIZE

            result = sorted(
                categories.values(),
                key=lambda x: x["name"],
            )

            logger.info(
                "Loaded %d vehicle categories",
                len(result),
            )

            return result

        except Exception:
            logger.exception(
                "Failed to load vehicle categories"
            )
            return []

    # ============================================================
    # MAKES
    # ============================================================

    async def get_makes(
        self,
        category_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return all unique vehicle makes from CRSP.

        IMPORTANT:
        vehicle_crsp_lookup does not contain vehicle_category,
        so category filtering is not performed against that table.

        The category_id is retained in the response for API
        compatibility.

        The query is explicitly paginated because the CRSP table
        contains thousands of records.
        """

        makes: Dict[int, Dict[str, Any]] = {}

        offset = 0

        try:

            while True:

                def query(start=offset):
                    return (
                        self.supabase
                        .table("vehicle_crsp_lookup")
                        .select(
                            "make_id, make"
                        )
                        .not_.is_("make", "null")
                        .order("make_id")
                        .range(
                            start,
                            start + self.PAGE_SIZE - 1,
                        )
                        .execute()
                    )

                response = await self._run(query)

                rows = response.data or []

                if not rows:
                    break

                for row in rows:

                    make_id = row.get("make_id")
                    make = row.get("make")

                    if make_id is None or not make:
                        continue

                    try:
                        make_id = int(make_id)
                    except (
                        TypeError,
                        ValueError,
                    ):
                        continue

                    name = str(make).strip().upper()

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

                if len(rows) < self.PAGE_SIZE:
                    break

                offset += self.PAGE_SIZE

            result = sorted(
                makes.values(),
                key=lambda x: x["name"],
            )

            logger.info(
                "Loaded %d unique vehicle makes from CRSP",
                len(result),
            )

            return result

        except Exception:
            logger.exception(
                "Failed to load vehicle makes"
            )
            return []

    # ============================================================
    # MODELS
    # ============================================================

    async def get_models(
        self,
        make_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Return all unique models belonging to a make.

        Explicit pagination is used because one make may have
        many CRSP records.
        """

        models: Dict[Any, Dict[str, Any]] = {}

        offset = 0

        try:

            while True:

                def query(start=offset):
                    return (
                        self.supabase
                        .table("vehicle_crsp_lookup")
                        .select(
                            "model_id, model, make_id, make, "
                            "body_type, manufacture_year, crsp_year"
                        )
                        .eq(
                            "make_id",
                            make_id,
                        )
                        .not_.is_(
                            "model",
                            "null",
                        )
                        .order("model_id")
                        .range(
                            start,
                            start + self.PAGE_SIZE - 1,
                        )
                        .execute()
                    )

                response = await self._run(query)

                rows = response.data or []

                if not rows:
                    break

                for row in rows:

                    model_id = row.get("model_id")
                    model = row.get("model")

                    if not model:
                        continue

                    model_name = str(
                        model
                    ).strip()

                    if not model_name:
                        continue

                    # Prefer model_id as the unique identity.
                    # Fall back to normalized model name when
                    # model_id is missing.
                    key = (
                        model_id
                        if model_id is not None
                        else model_name.upper()
                    )

                    years = []

                    for value in (
                        row.get("manufacture_year"),
                        row.get("crsp_year"),
                    ):
                        if value is None:
                            continue

                        try:
                            years.append(int(value))
                        except (
                            TypeError,
                            ValueError,
                        ):
                            continue

                    if key not in models:

                        models[key] = {
                            "id": model_id,
                            "name": model_name,
                            "make_id": row.get("make_id"),
                            "make_name": row.get("make"),
                            "vehicle_count": 0,
                            "body_type": row.get("body_type"),
                            "start_year": (
                                min(years)
                                if years
                                else None
                            ),
                            "end_year": (
                                max(years)
                                if years
                                else None
                            ),
                        }

                    models[key]["vehicle_count"] += 1

                    if years:

                        minimum_year = min(years)
                        maximum_year = max(years)

                        current_start = models[key].get(
                            "start_year"
                        )

                        current_end = models[key].get(
                            "end_year"
                        )

                        if (
                            current_start is None
                            or minimum_year < current_start
                        ):
                            models[key][
                                "start_year"
                            ] = minimum_year

                        if (
                            current_end is None
                            or maximum_year > current_end
                        ):
                            models[key][
                                "end_year"
                            ] = maximum_year

                if len(rows) < self.PAGE_SIZE:
                    break

                offset += self.PAGE_SIZE

            result = sorted(
                models.values(),
                key=lambda x: str(
                    x.get("name") or ""
                ).upper(),
            )

            logger.info(
                "Loaded %d unique models for make_id=%s",
                len(result),
                make_id,
            )

            return result

        except Exception:
            logger.exception(
                "Failed to load models for make_id=%s",
                make_id,
            )
            return []

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
        """
        Search CRSP vehicles.

        Search results use normal API pagination rather than
        loading the entire CRSP table.
        """

        def query():
            q = (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "crsp_id, make, make_id, model, model_id, "
                    "trim_level, manufacture_year, crsp_year, "
                    "body_type, seating_capacity, "
                    "engine_capacity, engine_capacity_cc, "
                    "fuel, transmission, drive_config, "
                    "crsp_kes, currency, horsepower, "
                    "vehicle_power_type, "
                    "battery_capacity_kwh, "
                    "powertrain_classification, "
                    "crsp_status"
                )
            )

            if make_id is not None:
                q = q.eq(
                    "make_id",
                    make_id,
                )

            if model_id is not None:
                q = q.eq(
                    "model_id",
                    model_id,
                )

            if fuel:
                q = q.ilike(
                    "fuel",
                    f"%{fuel}%",
                )

            if transmission:
                q = q.ilike(
                    "transmission",
                    f"%{transmission}%",
                )

            if engine_capacity_cc is not None:
                q = q.eq(
                    "engine_capacity_cc",
                    engine_capacity_cc,
                )

            if year is not None:
                q = q.or_(
                    f"manufacture_year.eq.{year},"
                    f"crsp_year.eq.{year}"
                )

            if search:
                pattern = f"%{search}%"

                q = q.or_(
                    f"make.ilike.{pattern},"
                    f"model.ilike.{pattern},"
                    f"trim_level.ilike.{pattern}"
                )

            return (
                q
                .order("make")
                .order("model")
                .order("crsp_id")
                .range(
                    offset,
                    offset + limit - 1,
                )
                .execute()
            )

        try:
            response = await self._run(query)

            return response.data or []

        except Exception:
            logger.exception(
                "Failed to search CRSP vehicles"
            )
            return []

    # ============================================================
    # SINGLE VEHICLE
    # ============================================================

    async def get_vehicle(
        self,
        crsp_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single CRSP vehicle.
        """

        def query():
            return (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "crsp_id, make, make_id, model, model_id, "
                    "trim_level, manufacture_year, crsp_year, "
                    "body_type, seating_capacity, "
                    "engine_capacity, engine_capacity_cc, "
                    "fuel, transmission, drive_config, "
                    "crsp_kes, currency, horsepower, "
                    "vehicle_power_type, "
                    "battery_capacity_kwh, "
                    "powertrain_classification, "
                    "crsp_status"
                )
                .eq(
                    "crsp_id",
                    crsp_id,
                )
                .limit(1)
                .execute()
            )

        try:
            response = await self._run(query)

            rows = response.data or []

            return rows[0] if rows else None

        except Exception:
            logger.exception(
                "Failed to get CRSP vehicle %s",
                crsp_id,
            )
            return None

    # ============================================================
    # BASE PRICE
    # ============================================================

    async def get_base_price(
        self,
        crsp_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Return CRSP reference pricing for a vehicle.
        """

        vehicle = await self.get_vehicle(
            crsp_id
        )

        if not vehicle:
            return None

        try:
            price = float(
                vehicle.get("crsp_kes") or 0
            )
        except (
            TypeError,
            ValueError,
        ):
            price = 0.0

        engine_cc = vehicle.get(
            "engine_capacity_cc"
        )

        try:
            engine_cc = (
                float(engine_cc)
                if engine_cc is not None
                else None
            )
        except (
            TypeError,
            ValueError,
        ):
            engine_cc = None

        return {
            "crsp_id": vehicle.get(
                "crsp_id"
            ),
            "make": vehicle.get(
                "make"
            ),
            "model": vehicle.get(
                "model"
            ),
            "engine_capacity": vehicle.get(
                "engine_capacity"
            ),
            "engine_capacity_cc": engine_cc,
            "engine_code": None,
            "crsp_fuel": vehicle.get(
                "fuel"
            ),
            "transmission": vehicle.get(
                "transmission"
            ),
            "base_price": price,
            "crsp_price": price,
            "currency": (
                vehicle.get("currency")
                or "KES"
            ),
            "source": "CRSP",
            "last_updated": None,
            "year": (
                vehicle.get("crsp_year")
                or vehicle.get(
                    "manufacture_year"
                )
            ),
        }

    # ============================================================
    # STATISTICS
    # ============================================================

    async def get_statistics(
        self,
    ) -> Dict[str, Any]:
        """
        Return complete CRSP catalogue statistics.

        The entire catalogue is processed in pages to avoid
        Supabase response limits.
        """

        makes = set()
        models = set()
        fuels = set()
        transmissions = set()
        engines = set()

        prices: List[float] = []

        total_vehicles = 0

        offset = 0

        try:

            while True:

                def query(start=offset):
                    return (
                        self.supabase
                        .table("vehicle_crsp_lookup")
                        .select(
                            "crsp_id, make, model, fuel, "
                            "transmission, engine_capacity_cc, "
                            "crsp_kes, manufacture_year, crsp_year"
                        )
                        .order("crsp_id")
                        .range(
                            start,
                            start + self.PAGE_SIZE - 1,
                        )
                        .execute()
                    )

                response = await self._run(query)

                rows = response.data or []

                if not rows:
                    break

                total_vehicles += len(rows)

                for row in rows:

                    if row.get("make"):
                        makes.add(
                            str(
                                row["make"]
                            ).strip().upper()
                        )

                    if row.get("model"):
                        models.add(
                            str(
                                row["model"]
                            ).strip().upper()
                        )

                    if row.get("fuel"):
                        fuels.add(
                            str(
                                row["fuel"]
                            ).strip().upper()
                        )

                    if row.get("transmission"):
                        transmissions.add(
                            str(
                                row["transmission"]
                            ).strip().upper()
                        )

                    if (
                        row.get(
                            "engine_capacity_cc"
                        )
                        is not None
                    ):
                        engines.add(
                            str(
                                row[
                                    "engine_capacity_cc"
                                ]
                            )
                        )

                    try:
                        if (
                            row.get(
                                "crsp_kes"
                            )
                            is not None
                        ):
                            price = float(
                                row[
                                    "crsp_kes"
                                ]
                            )

                            if price > 0:
                                prices.append(
                                    price
                                )

                    except (
                        TypeError,
                        ValueError,
                    ):
                        continue

                if len(rows) < self.PAGE_SIZE:
                    break

                offset += self.PAGE_SIZE

            average = (
                sum(prices) / len(prices)
                if prices
                else 0
            )

            minimum = (
                min(prices)
                if prices
                else 0
            )

            maximum = (
                max(prices)
                if prices
                else 0
            )

            result = {
                "total_vehicles": total_vehicles,
                "total_makes": len(makes),
                "total_models": len(models),
                "total_engine_capacities": len(
                    engines
                ),
                "total_fuel_types": len(fuels),
                "total_transmissions": len(
                    transmissions
                ),
                "makes_by_category": {},
                "vehicles_by_year": {},
                "vehicles_by_fuel_type": {},
                "vehicles_by_transmission": {},
                "vehicles_by_engine_capacity": {},
                "average_crsp_price": average,
                "min_crsp_price": minimum,
                "max_crsp_price": maximum,
                "average_price": average,
                "min_price": minimum,
                "max_price": maximum,
                "last_updated": None,
            }

            logger.info(
                "CRSP statistics: %s vehicles, %s makes, %s models",
                total_vehicles,
                len(makes),
                len(models),
            )

            return result

        except Exception:
            logger.exception(
                "Failed to calculate CRSP statistics"
            )

            return {
                "total_vehicles": 0,
                "total_makes": 0,
                "total_models": 0,
                "total_engine_capacities": 0,
                "total_fuel_types": 0,
                "total_transmissions": 0,
                "makes_by_category": {},
                "vehicles_by_year": {},
                "vehicles_by_fuel_type": {},
                "vehicles_by_transmission": {},
                "vehicles_by_engine_capacity": {},
                "average_crsp_price": 0,
                "min_crsp_price": 0,
                "max_crsp_price": 0,
                "average_price": 0,
                "min_price": 0,
                "max_price": 0,
                "last_updated": None,
            }

    # ============================================================
    # HEALTH CHECK
    # ============================================================

    async def health_check(
        self,
    ) -> Dict[str, Any]:
        """
        Check CRSP database connectivity and record count.
        """

        def query():
            return (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "crsp_id",
                    count="exact",
                )
                .limit(1)
                .execute()
            )

        try:
            response = await self._run(
                query
            )

            return {
                "status": "healthy",
                "service": "vehicles",
                "version": "2.1",
                "database": "connected",
                "crsp_records": (
                    response.count or 0
                ),
            }

        except Exception as exc:

            logger.exception(
                "Vehicle repository health check failed"
            )

            return {
                "status": "degraded",
                "service": "vehicles",
                "version": "2.1",
                "database": "error",
                "crsp_records": 0,
                "error": str(exc),
            }


# ================================================================
# EXPORT
# ================================================================

__all__ = [
    "VehicleRepository",
]
