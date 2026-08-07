"""
Auto-D Kenya
Vehicle Master Repository

Database:
vehicle_base_prices
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi.concurrency import run_in_threadpool

from app.core.database import get_supabase


logger = logging.getLogger(__name__)


class VehicleMasterRepository:
    """
    Repository for Vehicle Master database operations.
    """

    def __init__(self):
        self.db = get_supabase()


    async def _run(self, fn):
        """
        Execute blocking Supabase operations
        inside threadpool.
        """
        return await run_in_threadpool(fn)


    # ======================================================
    # GET VEHICLE
    # ======================================================

    async def get_vehicle(
        self,
        variant_id: int
    ) -> Optional[Dict[str, Any]]:

        try:
            response = await self._run(
                lambda:
                self.db
                .table("vehicle_base_prices")
                .select("*")
                .eq("id", variant_id)
                .single()
                .execute()
            )

            return response.data

        except Exception as e:
            logger.error(
                f"Error fetching vehicle {variant_id}: {e}"
            )
            return None


    # ======================================================
    # SEARCH VEHICLES
    # ======================================================

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

        try:

            offset = (page - 1) * per_page


            query = (
                self.db
                .table("vehicle_base_prices")
                .select("*", count="exact")
                .eq(
                    "is_active",
                    True
                )
            )


            if make:
                query = query.ilike(
                    "make",
                    f"%{make}%"
                )


            if model:
                query = query.ilike(
                    "model",
                    f"%{model}%"
                )


            if fuel:
                query = query.eq(
                    "fuel",
                    fuel
                )


            if transmission:
                query = query.eq(
                    "transmission",
                    transmission
                )


            if body_type:
                query = query.eq(
                    "body_type",
                    body_type
                )


            response = await self._run(
                lambda:
                query
                .range(
                    offset,
                    offset + per_page - 1
                )
                .order(
                    "make"
                )
                .order(
                    "model"
                )
                .execute()
            )


            return {
                "total": response.count or 0,
                "page": page,
                "per_page": per_page,
                "results": response.data or [],
            }


        except Exception as e:

            logger.error(
                f"Search error: {e}"
            )

            return {
                "total":0,
                "page":page,
                "per_page":per_page,
                "results":[]
            }



    # ======================================================
    # UPDATE VEHICLE DETAILS
    # ======================================================

    async def update_variant(
        self,
        variant_id: int,
        values: Dict[str, Any]
    ) -> List[Dict[str, Any]]:

        try:

            response = await self._run(
                lambda:
                self.db
                .table(
                    "vehicle_base_prices"
                )
                .update(values)
                .eq(
                    "id",
                    variant_id
                )
                .execute()
            )


            return response.data or []


        except Exception as e:

            logger.error(
                f"Update vehicle error {variant_id}: {e}"
            )

            raise



    # ======================================================
    # UPDATE SPECIFICATIONS
    # ======================================================

    async def update_specifications(
        self,
        variant_id:int,
        values:Dict[str,Any]
    ) -> List[Dict[str,Any]]:

        allowed_fields = {

            "engine_capacity",
            "transmission",
            "fuel",
            "body_type",
            "drive_configuration",
            "gvw",
            "seating"

        }


        clean_values = {
            k:v
            for k,v in values.items()
            if k in allowed_fields
        }


        return await self.update_variant(
            variant_id,
            clean_values
        )



    # ======================================================
    # UPDATE PRICING
    # ======================================================

    async def update_base_price(
        self,
        variant_id:int,
        values:Dict[str,Any]
    ) -> List[Dict[str,Any]]:

        allowed_fields = {

            "crsp_kes",
            "market_value",
            "insurance_value",
            "forced_sale_value",
            "trade_in_value"

        }


        clean_values = {
            k:v
            for k,v in values.items()
            if k in allowed_fields
        }


        return await self.update_variant(
            variant_id,
            clean_values
        )



    # ======================================================
    # DASHBOARD STATISTICS
    # ======================================================

    async def statistics(self) -> Dict[str,Any]:

        try:

            total = await self._run(
                lambda:
                self.db
                .table(
                    "vehicle_base_prices"
                )
                .select(
                    "id",
                    count="exact"
                )
                .execute()
            )


            active = await self._run(
                lambda:
                self.db
                .table(
                    "vehicle_base_prices"
                )
                .select(
                    "id",
                    count="exact"
                )
                .eq(
                    "is_active",
                    True
                )
                .execute()
            )


            return {

                "total_vehicles":
                    total.count or 0,

                "active_variants":
                    active.count or 0,

                "total_base_prices":
                    total.count or 0,

                "last_updated":
                    None

            }


        except Exception as e:

            logger.error(
                f"Statistics error: {e}"
            )

            return {}



    # ======================================================
    # SOFT DELETE
    # ======================================================

    async def deactivate_variant(
        self,
        variant_id:int
    ) -> List[Dict[str,Any]]:

        try:

            response = await self._run(
                lambda:
                self.db
                .table(
                    "vehicle_base_prices"
                )
                .update(
                    {
                        "is_active":False,
                        "deleted_at":
                            datetime.utcnow()
                    }
                )
                .eq(
                    "id",
                    variant_id
                )
                .execute()
            )


            return response.data or []


        except Exception as e:

            logger.error(
                f"Deactivate error {variant_id}: {e}"
            )

            raise



    # ======================================================
    # BULK PRICE UPDATE
    # ======================================================

    async def bulk_update_prices(
        self,
        updates:List[Dict[str,Any]]
    )->int:


        updated = 0


        for item in updates:

            try:

                await self.update_base_price(
                    item["variant_id"],
                    {
                        "crsp_kes":
                            item["crsp_kes"]
                    }
                )

                updated += 1


            except Exception as e:

                logger.error(
                    f"Bulk update failed: {e}"
                )


        return updated
