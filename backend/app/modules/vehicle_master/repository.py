"""
Auto-D Kenya
Vehicle Master Repository
"""

import logging
from typing import Any, Dict, List, Optional

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
        """Get complete vehicle from master view."""
        try:
            response = await self._run(
                lambda: self.db.table("vehicle_master_specs")
                .select("*")
                .eq("variant_id", variant_id)
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
            query = self.db.table("vehicle_master_specs").select("*")
            
            if make:
                query = query.ilike("make_name", f"%{make}%")
            if model:
                query = query.ilike("model_name", f"%{model}%")
            if year:
                query = query.lte("generation_start_year", year).gte("generation_end_year", year)
            if fuel:
                query = query.eq("fuel_type_name", fuel)
            if transmission:
                query = query.eq("transmission_type_name", transmission)
            if body_type:
                query = query.eq("body_type_name", body_type)
            
            # Get total count
            count_query = query.select("count", count="exact")
            count_response = await self._run(lambda: count_query.execute())
            total = count_response.count or 0
            
            # Get paginated results
            results_query = query.range(offset, offset + per_page - 1).order("make_name", "model_name")
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
            response = await self._run(
                lambda: self.db.table("vehicle_variants")
                .update(values)
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
            response = await self._run(
                lambda: self.db.table("vehicle_specifications")
                .update(values)
                .eq("variant_id", variant_id)
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
            response = await self._run(
                lambda: self.db.table("vehicle_base_prices")
                .update(values)
                .eq("variant_id", variant_id)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error updating base price {variant_id}: {e}")
            raise

    # ==========================================================
    # DASHBOARD
    # ==========================================================

    async def statistics(self) -> Dict[str, Any]:
        """Get dashboard statistics."""
        try:
            vehicles = await self._run(
                lambda: self.db.table("vehicle_variants")
                .select("id", count="exact")
                .execute()
            )
            
            active_vehicles = await self._run(
                lambda: self.db.table("vehicle_variants")
                .select("id", count="exact")
                .eq("is_active", True)
                .execute()
            )
            
            makes = await self._run(
                lambda: self.db.table("vehicle_makes")
                .select("id", count="exact")
                .execute()
            )
            
            models = await self._run(
                lambda: self.db.table("vehicle_models")
                .select("id", count="exact")
                .execute()
            )
            
            generations = await self._run(
                lambda: self.db.table("vehicle_generations")
                .select("id", count="exact")
                .execute()
            )
            
            prices = await self._run(
                lambda: self.db.table("vehicle_base_prices")
                .select("id", count="exact")
                .execute()
            )
            
            return {
                "total_vehicles": vehicles.count or 0,
                "active_variants": active_vehicles.count or 0,
                "total_makes": makes.count or 0,
                "total_models": models.count or 0,
                "total_generations": generations.count or 0,
                "total_variants": vehicles.count or 0,
                "total_base_prices": prices.count or 0,
                "last_updated": None,  # Will be populated by service
            }
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                "total_vehicles": 0,
                "active_variants": 0,
                "total_makes": 0,
                "total_models": 0,
                "total_generations": 0,
                "total_variants": 0,
                "total_base_prices": 0,
                "last_updated": None,
            }

    # ==========================================================
    # DELETE
    # ==========================================================

    async def deactivate_variant(self, variant_id: int) -> List[Dict[str, Any]]:
        """Soft-delete vehicle variant."""
        try:
            response = await self._run(
                lambda: self.db.table("vehicle_variants")
                .update({"is_active": False})
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
                await self.update_base_price(
                    update["variant_id"],
                    {"crsp_kes": update["crsp_kes"]}
                )
                updated += 1
            except Exception as e:
                logger.error(f"Error updating price for variant {update.get('variant_id')}: {e}")
        return updated
