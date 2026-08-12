# ================================================================
# Auto-D Kenya - Vehicle Repository
# ================================================================
# CRSP-driven vehicle catalogue repository.
#
# SOURCE OF TRUTH:
#     public.vehicle_crsp_lookup
#
# IMPORTANT:
# This repository only references columns that actually exist
# in vehicle_crsp_lookup.
# ================================================================

import logging
from typing import Optional, List, Dict, Any

from fastapi.concurrency import run_in_threadpool

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class VehicleRepository:
    """
    Repository for CRSP vehicle catalogue operations.

    Database source:
        public.vehicle_crsp_lookup
    """

    def __init__(self):
        self.supabase = get_supabase()

    # ============================================================
    # THREAD EXECUTOR
    # ============================================================

    async def _run(self, fn):
        """Run synchronous Supabase operation in worker thread."""
        return await run_in_threadpool(fn)

    # ============================================================
    # CATEGORIES
    # ============================================================

    async def get_categories(self) -> List[Dict[str, Any]]:
        """
        Return approved application vehicle categories.

        Category data is maintained separately from CRSP identity.
        """

        categories = [
            {
                "id": 1,
                "name": "COMMERCIAL",
                "description": "Commercial vehicles",
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
                "description": "Passenger sedan vehicles",
                "icon": None,
                "vehicle_count": 0,
            },
        ]

        return categories

    # ============================================================
    # MAKES
    # ============================================================

    async def get_makes(
        self,
        category_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return unique makes directly from CRSP.

        category_id is currently not applied because vehicle
        category is not a column in vehicle_crsp_lookup.
        """

        def query():
            return (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select("make_id, make")
                .not_.is_("make", "null")
                .execute()
            )

        response = await self._run(query)

        rows = response.data or []

        makes: Dict[str, Dict[str, Any]] = {}

        for row in rows:
            make = row.get("make")

            if not make:
                continue

            make = str(make).strip().upper()

            if not make:
                continue

            if make not in makes:
                makes[make] = {
                    "id": row.get("make_id"),
                    "name": make,
                    "country": None,
                    "logo_url": None,
                    "vehicle_count": 0,
                    "category_id": category_id,
                }

            makes[make]["vehicle_count"] += 1

        return sorted(
            makes.values(),
            key=lambda x: x["name"],
        )

    # ============================================================
    # MODELS
    # ============================================================

    async def get_models(
        self,
        make_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Return unique models for a CRSP make.
        """

        def query():
            return (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "model_id, model, make_id, make, body_type"
                )
                .eq("make_id", make_id)
                .not_.is_("model", "null")
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
            key=lambda x: x["name"].upper(),
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
        """
        Search the CRSP catalogue.

        Only real vehicle_crsp_lookup columns are used.
        """

        def query():
            q = (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "crsp_id,"
                    "make_id,"
                    "make,"
                    "model_id,"
                    "model,"
                    "trim_level,"
                    "manufacture_year,"
                    "crsp_year,"
                    "body_type,"
                    "seating_capacity,"
                    "engine_capacity,"
                    "engine_capacity_cc,"
                    "fuel,"
                    "transmission,"
                    "drive_config,"
                    "crsp_kes,"
                    "currency,"
                    "horsepower,"
                    "vehicle_power_type,"
                    "battery_capacity_kwh,"
                    "powertrain_classification,"
                    "crsp_status"
                )
            )

            if make_id is not None:
                q = q.eq("make_id", make_id)

            if model_id is not None:
                q = q.eq("model_id", model_id)

            if fuel:
                q = q.ilike(
                    "fuel",
                    f"%{fuel.strip()}%"
                )

            if transmission:
                q = q.ilike(
                    "transmission",
                    f"%{transmission.strip()}%"
                )

            if engine_capacity_cc is not None:
                q = q.eq(
                    "engine_capacity_cc",
                    engine_capacity_cc
                )

            if year is not None:
                q = q.or_(
                    f"crsp_year.eq.{year},"
                    f"manufacture_year.eq.{year}"
                )

            if search:
                pattern = f"%{search.strip()}%"

                q = q.or_(
                    f"make.ilike.{pattern},"
                    f"model.ilike.{pattern},"
                    f"trim_level.ilike.{pattern},"
                    f"body_type.ilike.{pattern},"
                    f"fuel.ilike.{pattern}"
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
        """
        Return one CRSP vehicle.
        """

        def query():
            return (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "crsp_id,"
                    "make_id,"
                    "make,"
                    "model_id,"
                    "model,"
                    "trim_level,"
                    "manufacture_year,"
                    "crsp_year,"
                    "body_type,"
                    "seating_capacity,"
                    "engine_capacity,"
                    "engine_capacity_cc,"
                    "fuel,"
                    "transmission,"
                    "drive_config,"
                    "crsp_kes,"
                    "currency,"
                    "horsepower,"
                    "vehicle_power_type,"
                    "battery_capacity_kwh,"
                    "powertrain_classification,"
                    "crsp_status"
                )
                .eq("crsp_id", crsp_id)
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
        """
        Return CRSP price directly from crsp_kes.
        """

        vehicle = await self.get_vehicle(crsp_id)

        if not vehicle:
            return None

        price = vehicle.get("crsp_kes")

        return {
            "crsp_id": vehicle.get("crsp_id"),
            "make": vehicle.get("make"),
            "model": vehicle.get("model"),
            "engine_capacity": vehicle.get("engine_capacity"),
            "engine_capacity_cc": vehicle.get("engine_capacity_cc"),
            "engine_code": None,
            "crsp_fuel": vehicle.get("fuel"),
            "transmission": vehicle.get("transmission"),
            "base_price": float(price or 0),
            "crsp_price": float(price or 0),
            "currency": vehicle.get("currency") or "KES",
            "source": "CRSP",
            "last_updated": None,
            "year": (
                vehicle.get("crsp_year")
                or vehicle.get("manufacture_year")
            ),
        }

    # ============================================================
    # STATISTICS
    # ============================================================

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Return statistics from the actual CRSP table.
        """

        def query():
            return (
                self.supabase
                .table("vehicle_crsp_lookup")
                .select(
                    "crsp_id,"
                    "make_id,"
                    "make,"
                    "model_id,"
                    "model,"
                    "engine_capacity,"
                    "engine_capacity_cc,"
                    "fuel,"
                    "transmission,"
                    "crsp_kes,"
                    "manufacture_year,"
                    "crsp_year,"
                    "body_type"
                )
                .execute()
            )

        response = await self._run(query)

        rows = response.data or []

        makes = set()
        models = set()
        fuels = set()
        transmissions = set()
        engine_capacities = set()

        vehicles_by_year: Dict[str, int] = {}
        vehicles_by_fuel: Dict[str, int] = {}
        vehicles_by_transmission: Dict[str, int] = {}
        vehicles_by_engine: Dict[str, int] = {}

        prices = []

        for row in rows:

            if row.get("make"):
                makes.add(str(row["make"]).strip().upper())

            if row.get("model"):
                models.add(
                    (
                        row.get("model_id"),
                        str(row["model"]).strip().upper(),
                    )
                )

            if row.get("fuel"):
                fuel = str(row["fuel"]).strip().upper()
                fuels.add(fuel)
                vehicles_by_fuel[fuel] = (
                    vehicles_by_fuel.get(fuel, 0) + 1
                )

            if row.get("transmission"):
                transmission = str(
                    row["transmission"]
                ).strip().upper()

                transmissions.add(transmission)

                vehicles_by_transmission[
                    transmission
                ] = (
                    vehicles_by_transmission.get(
                        transmission,
                        0,
                    )
                    + 1
                )

            engine = row.get("engine_capacity_cc")

            if engine is not None:
                engine_key = str(engine)
                engine_capacities.add(engine_key)

                vehicles_by_engine[engine_key] = (
                    vehicles_by_engine.get(
                        engine_key,
                        0,
                    )
                    + 1
                )

            year = (
                row.get("crsp_year")
                or row.get("manufacture_year")
            )

            if year is not None:
                year_key = str(year)

                vehicles_by_year[year_key] = (
                    vehicles_by_year.get(
                        year_key,
                        0,
                    )
                    + 1
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
            "total_engine_capacities": len(
                engine_capacities
            ),
            "total_fuel_types": len(fuels),
            "total_transmissions": len(
                transmissions
            ),
            "makes_by_category": {},
            "vehicles_by_year": vehicles_by_year,
            "vehicles_by_fuel_type": vehicles_by_fuel,
            "vehicles_by_transmission": (
                vehicles_by_transmission
            ),
            "vehicles_by_engine_capacity": (
                vehicles_by_engine
            ),
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
        """
        Verify CRSP table connectivity.
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
