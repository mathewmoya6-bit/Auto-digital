# app/modules/vehicles/repository.py
import logging
from typing import Optional, List, Dict, Any
from fastapi.concurrency import run_in_threadpool
from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class VehicleRepository:
    """CRSP vehicle catalogue repository.

    Source of truth: public.vehicle_crsp_lookup.
    Aligned with the confirmed database schema.
    """

    def __init__(self):
        self.supabase = get_supabase()

    async def _run(self, fn):
        return await run_in_threadpool(fn)

    async def get_categories(self) -> List[Dict[str, Any]]:
        def query():
            return (
                self.supabase.table("vehicle_category_lookup")
                .select("id, body_type, vehicle_category, category_confidence, category_source")
                .in_("vehicle_category", ["COMMERCIAL", "ELECTRIC", "LUXURY", "PICKUP", "SEDAN"])
                .order("vehicle_category")
                .execute()
            )

        try:
            response = await self._run(query)
        except Exception:
            logger.exception("Failed to load vehicle categories")
            return []

        categories = {}
        for row in response.data or []:
            category = row.get("vehicle_category")
            if not category:
                continue
            category = str(category).strip().upper()
            if category not in categories:
                categories[category] = {
                    "id": len(categories) + 1,
                    "name": category,
                    "description": None,
                    "icon": None,
                    "vehicle_count": 0,
                }
            categories[category]["vehicle_count"] += 1

        return sorted(categories.values(), key=lambda x: x["name"])

    async def get_makes(self, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return all unique makes from vehicle_crsp_lookup.

        IMPORTANT: this table has no is_duplicate column and no
        vehicle_category column, so neither is referenced here.
        """
        def query():
            return (
                self.supabase.table("vehicle_crsp_lookup")
                .select("make_id, make")
                .not_.is_("make", "null")
                .order("make")
                .execute()
            )

        response = await self._run(query)
        makes = {}

        for row in response.data or []:
            make_id = row.get("make_id")
            make = row.get("make")
            if make_id is None or not make:
                continue

            name = str(make).strip().upper()
            if not name:
                continue

            if make_id not in makes:
                makes[make_id] = {
                    "id": int(make_id),
                    "name": name,
                    "country": None,
                    "logo_url": None,
                    "vehicle_count": 0,
                    "category_id": category_id,
                }

            makes[make_id]["vehicle_count"] += 1

        return sorted(makes.values(), key=lambda x: x["name"])

    async def get_models(self, make_id: int) -> List[Dict[str, Any]]:
        def query():
            return (
                self.supabase.table("vehicle_crsp_lookup")
                .select("model_id, model, make_id, make, body_type, manufacture_year, crsp_year")
                .eq("make_id", make_id)
                .not_.is_("model", "null")
                .order("model")
                .execute()
            )

        response = await self._run(query)
        models = {}

        for row in response.data or []:
            model_id = row.get("model_id")
            model = row.get("model")
            if not model:
                continue

            key = model_id if model_id is not None else str(model).strip().upper()
            years = [
                int(y) for y in (row.get("manufacture_year"), row.get("crsp_year"))
                if y is not None
            ]

            if key not in models:
                models[key] = {
                    "id": model_id,
                    "name": str(model).strip(),
                    "make_id": row.get("make_id"),
                    "make_name": row.get("make"),
                    "vehicle_count": 0,
                    "body_type": row.get("body_type"),
                    "start_year": min(years) if years else None,
                    "end_year": max(years) if years else None,
                }

            models[key]["vehicle_count"] += 1
            if years:
                models[key]["start_year"] = (
                    min(models[key]["start_year"], min(years))
                    if models[key]["start_year"] is not None else min(years)
                )
                models[key]["end_year"] = (
                    max(models[key]["end_year"], max(years))
                    if models[key]["end_year"] is not None else max(years)
                )

        return sorted(models.values(), key=lambda x: x["name"].upper())

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

        def query():
            q = (
                self.supabase.table("vehicle_crsp_lookup")
                .select(
                    "crsp_id, make, make_id, model, model_id, trim_level, "
                    "manufacture_year, crsp_year, body_type, seating_capacity, "
                    "engine_capacity, engine_capacity_cc, fuel, transmission, "
                    "drive_config, crsp_kes, currency, horsepower, "
                    "vehicle_power_type, battery_capacity_kwh, "
                    "powertrain_classification, crsp_status"
                )
            )

            if make_id is not None:
                q = q.eq("make_id", make_id)
            if model_id is not None:
                q = q.eq("model_id", model_id)
            if fuel:
                q = q.ilike("fuel", f"%{fuel}%")
            if transmission:
                q = q.ilike("transmission", f"%{transmission}%")
            if engine_capacity_cc is not None:
                q = q.eq("engine_capacity_cc", engine_capacity_cc)
            if year is not None:
                q = q.or_(f"manufacture_year.eq.{year},crsp_year.eq.{year}")
            if search:
                pattern = f"%{search}%"
                q = q.or_(
                    f"make.ilike.{pattern},"
                    f"model.ilike.{pattern},"
                    f"trim_level.ilike.{pattern}"
                )

            return (
                q.order("make")
                .order("model")
                .range(offset, offset + limit - 1)
                .execute()
            )

        response = await self._run(query)
        return response.data or []

    async def get_vehicle(self, crsp_id: int) -> Optional[Dict[str, Any]]:
        def query():
            return (
                self.supabase.table("vehicle_crsp_lookup")
                .select(
                    "crsp_id, make, make_id, model, model_id, trim_level, "
                    "manufacture_year, crsp_year, body_type, seating_capacity, "
                    "engine_capacity, engine_capacity_cc, fuel, transmission, "
                    "drive_config, crsp_kes, currency, horsepower, "
                    "vehicle_power_type, battery_capacity_kwh, "
                    "powertrain_classification, crsp_status"
                )
                .eq("crsp_id", crsp_id)
                .limit(1)
                .execute()
            )

        response = await self._run(query)
        rows = response.data or []
        return rows[0] if rows else None

    async def get_base_price(self, crsp_id: int) -> Optional[Dict[str, Any]]:
        vehicle = await self.get_vehicle(crsp_id)
        if not vehicle:
            return None

        try:
            price = float(vehicle.get("crsp_kes") or 0)
        except (TypeError, ValueError):
            price = 0.0

        engine_cc = vehicle.get("engine_capacity_cc")
        try:
            engine_cc = float(engine_cc) if engine_cc is not None else None
        except (TypeError, ValueError):
            engine_cc = None

        return {
            "crsp_id": vehicle.get("crsp_id"),
            "make": vehicle.get("make"),
            "model": vehicle.get("model"),
            "engine_capacity": vehicle.get("engine_capacity"),
            "engine_capacity_cc": engine_cc,
            "engine_code": None,
            "crsp_fuel": vehicle.get("fuel"),
            "transmission": vehicle.get("transmission"),
            "base_price": price,
            "crsp_price": price,
            "currency": vehicle.get("currency") or "KES",
            "source": "CRSP",
            "last_updated": None,
            "year": vehicle.get("crsp_year") or vehicle.get("manufacture_year"),
        }

    async def get_statistics(self) -> Dict[str, Any]:
        def query():
            return (
                self.supabase.table("vehicle_crsp_lookup")
                .select(
                    "crsp_id, make, model, fuel, transmission, "
                    "engine_capacity_cc, crsp_kes, manufacture_year, crsp_year"
                )
                .execute()
            )

        response = await self._run(query)
        rows = response.data or []

        makes, models, fuels, transmissions, engines = set(), set(), set(), set(), set()
        prices = []

        for row in rows:
            if row.get("make"):
                makes.add(str(row["make"]).strip().upper())
            if row.get("model"):
                models.add(str(row["model"]).strip().upper())
            if row.get("fuel"):
                fuels.add(str(row["fuel"]).strip().upper())
            if row.get("transmission"):
                transmissions.add(str(row["transmission"]).strip().upper())
            if row.get("engine_capacity_cc") is not None:
                engines.add(str(row["engine_capacity_cc"]))
            try:
                if row.get("crsp_kes") is not None:
                    prices.append(float(row["crsp_kes"]))
            except (TypeError, ValueError):
                pass

        average = sum(prices) / len(prices) if prices else 0
        minimum = min(prices) if prices else 0
        maximum = max(prices) if prices else 0

        return {
            "total_vehicles": len(rows),
            "total_makes": len(makes),
            "total_models": len(models),
            "total_engine_capacities": len(engines),
            "total_fuel_types": len(fuels),
            "total_transmissions": len(transmissions),
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

    async def health_check(self) -> Dict[str, Any]:
        def query():
            return (
                self.supabase.table("vehicle_crsp_lookup")
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
            logger.exception("Vehicle repository health check failed")
            return {
                "status": "degraded",
                "service": "vehicles",
                "version": "2.0",
                "database": "error",
                "crsp_records": 0,
                "error": str(exc),
            }
