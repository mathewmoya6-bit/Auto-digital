"""
Auto-D Kenya
Vehicle Master Repository
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi.concurrency import run_in_threadpool

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class VehicleMasterRepository:
    """Repository for vehicle master database operations."""

    def __init__(self):
        self.db = get_supabase()

    async def _run(self, fn):
        """Run blocking Supabase calls in threadpool."""
        return await run_in_threadpool(fn)

    # ==========================================================
    # MASTER VIEW
    # ==========================================================

    async def get_vehicle(self, variant_id: int) -> Optional[Dict[str, Any]]:
        """Get complete vehicle from base prices table."""
        try:
            response = await self._run(
                lambda: self.db.table("vehicle_base_prices")
                .select("*")
                .eq("id", variant_id)
                .single()
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Error fetching vehicle {variant_id}: {e}")
            return None

    async def search(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        year: Optional[int] = None,
        fuel: Optional[str] = None,
        transmission: Optional[str] = None,
        body_type: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        """Search vehicles with pagination."""
        try:
            offset = (page - 1) * per_page
            
            # Build query
            query = self.db.table("vehicle_base_prices").select("*")
            
            # Only show active vehicles by default
            query = query.eq("is_active", True)
            
            if make:
                query = query.ilike("make", f"%{make}%")
            if model:
                query = query.ilike("model", f"%{model}%")
            if year:
                query = query.eq("year", year)
            if fuel:
                query = query.eq("fuel", fuel)
            if transmission:
                query = query.eq("transmission", transmission)
            if body_type:
                query = query.eq("body_type", body_type)
            
            # Get total count
            count_query = query.select("count", count="exact")
            count_response = await self._run(lambda: count_query.execute())
            total = count_response.count or 0
            
            # Get paginated results
            results_query = query.range(offset, offset + per_page - 1).order("make", "model")
            results_response = await self._run(lambda: results_query.execute())
            
            return {
                "total": total,
                "page": page,
                "per_page": per_page,
                "results": results_response.data or [],
            }
        except Exception as e:
            logger.error(f"Error searching vehicles: {e}")
            return {
                "total": 0,
                "page": 1,
                "per_page": per_page,
                "results": [],
            }

    # ==========================================================
    # UPDATE VARIANT
    # ==========================================================

    async def update_variant(
        self,
        variant_id: int,
        values: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Update vehicle variant."""
        try:
            # Only allow fields that exist in vehicle_base_prices
            allowed_fields = [
                "make", "model", "variant", "year", 
                "fuel", "transmission", "body_type",
                "seating", "gvw", "is_active"
            ]
            filtered_values = {k: v for k, v in values.items() if k in allowed_fields}
            
            response = await self._run(
                lambda: self.db.table("vehicle_base_prices")
                .update(filtered_values)
                .eq("id", variant_id)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error updating variant {variant_id}: {e}")
            raise

    # ==========================================================
    # UPDATE SPECIFICATIONS
    # ==========================================================

    async def update_specifications(
        self,
        variant_id: int,
        values: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Update vehicle specifications."""
        try:
            # Map specification fields to vehicle_base_prices columns
            field_map = {
                "engine_cc": "engine_capacity",
                "transmission_type": "transmission",
                "drive_type": "drive_configuration",
                "body_type": "body_type",
                "seats": "seating",
                "gvw": "gvw",
            }
            
            mapped_values = {}
            for k, v in values.items():
                if k in field_map:
                    mapped_values[field_map[k]] = v
            
            response = await self._run(
                lambda: self.db.table("vehicle_base_prices")
                .update(mapped_values)
                .eq("id", variant_id)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error updating specifications {variant_id}: {e}")
            raise

    # ==========================================================
    # UPDATE BASE PRICE
    # ==========================================================

    async def update_base_price(
        self,
        variant_id: int,
        values: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Update vehicle base price."""
        try:
            allowed_fields = ["base_price_kes", "currency", "effective_date", "source"]
            filtered_values = {k: v for k, v in values.items() if k in allowed_fields}
            
            response = await self._run(
                lambda: self.db.table("vehicle_base_prices")
                .update(filtered_values)
                .eq("id", variant_id)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error updating base price {variant_id}: {e}")
            raise

    # ==========================================================
    # DASHBOARD STATISTICS
    # ==========================================================

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics from vehicle_base_prices."""
        try:
            # Total vehicles
            vehicles = await self._run(
                lambda: self.db.table("vehicle_base_prices")
                .select("id", count="exact")
                .execute()
            )
            
            # Active vehicles
            active = await self._run(
                lambda: self.db.table("vehicle_base_prices")
                .select("id", count="exact")
                .eq("is_active", True)
                .execute()
            )
            
            # Unique makes
            makes_response = await self._run(
                lambda: self.db.table("vehicle_base_prices")
                .select("make")
                .eq("is_active", True)
                .execute()
            )
            makes = set()
            for row in makes_response.data or []:
                if row.get("make"):
                    makes.add(row["make"])
            
            # Unique models
            models_response = await self._run(
                lambda: self.db.table("vehicle_base_prices")
                .select("model")
                .eq("is_active", True)
                .execute()
            )
            models = set()
            for row in models_response.data or []:
                if row.get("model"):
                    models.add(row["model"])
            
            # Fuel types breakdown
            fuel_response = await self._run(
                lambda: self.db.table("vehicle_base_prices")
                .select("fuel")
                .eq("is_active", True)
                .execute()
            )
            fuel_counts = {}
            for row in fuel_response.data or []:
                fuel = row.get("fuel", "Unknown")
                fuel_counts[fuel] = fuel_counts.get(fuel, 0) + 1
            
            return {
                "total_vehicles": vehicles.count or 0,
                "active_variants": active.count or 0,
                "total_makes": len(makes),
                "total_models": len(models),
                "total_variants": vehicles.count or 0,
                "total_base_prices": vehicles.count or 0,
                "fuel_breakdown": fuel_counts,
                "last_updated": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error getting dashboard statistics: {e}")
            return {
                "total_vehicles": 0,
                "active_variants": 0,
                "total_makes": 0,
                "total_models": 0,
                "total_variants": 0,
                "total_base_prices": 0,
                "fuel_breakdown": {},
                "last_updated": datetime.utcnow().isoformat(),
            }

    # ==========================================================
    # DELETE
    # ==========================================================

    async def deactivate_variant(self, variant_id: int) -> List[Dict[str, Any]]:
        """Soft-delete vehicle variant."""
        try:
            response = await self._run(
                lambda: self.db.table("vehicle_base_prices")
                .update({
                    "is_active": False,
                    "deleted_at": datetime.utcnow().isoformat()
                })
                .eq("id", variant_id)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error deactivating variant {variant_id}: {e}")
            raise

    # ==========================================================
    # BULK OPERATIONS
    # ==========================================================

    async def bulk_update_prices(self, updates: List[Dict[str, Any]]) -> int:
        """Bulk update base prices."""
        updated = 0
        for update in updates:
            try:
                variant_id = update.get("variant_id")
                price = update.get("base_price_kes") or update.get("crsp_kes")
                
                if variant_id and price:
                    await self.update_base_price(
                        variant_id,
                        {"base_price_kes": price}
                    )
                    updated += 1
            except Exception as e:
                logger.error(f"Error updating price for variant {update.get('variant_id')}: {e}")
        return updated

    # ==========================================================
    # GET VEHICLE BY MAKE/MODEL
    # ==========================================================

    async def get_vehicle_by_make_model(
        self,
        make: str,
        model: str,
        variant: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get vehicle by make, model, and optional variant."""
        try:
            query = self.db.table("vehicle_base_prices").select("*")
            query = query.ilike("make", make)
            query = query.ilike("model", model)
            
            if variant:
                query = query.ilike("variant", variant)
            
            response = await self._run(
                lambda: query.limit(1).execute()
            )
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching vehicle by make/model: {e}")
            return None
