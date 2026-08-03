# app/modules/scraper/vehicle_lookup.py
# ================================================================
# Auto-D Kenya - Vehicle Lookup
# ================================================================

import logging
from typing import Optional

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class VehicleLookup:

    def __init__(self):
        self.supabase = get_supabase()

        # In-memory cache
        self.make_cache = {}
        self.model_cache = {}

    # ============================================================
    # MAKE
    # ============================================================

    async def get_make_id(
        self,
        make_name: Optional[str],
        create: bool = False,
    ) -> Optional[int]:

        if not make_name:
            return None

        make_name = make_name.strip()

        if make_name in self.make_cache:
            return self.make_cache[make_name]

        try:

            response = (
                self.supabase
                .table("vehicle_makes")
                .select("id")
                .ilike("name", make_name)
                .maybe_single()
                .execute()
            )

            if response.data:
                make_id = response.data["id"]
                self.make_cache[make_name] = make_id
                return make_id

            if create:

                created = (
                    self.supabase
                    .table("vehicle_makes")
                    .insert({
                        "name": make_name
                    })
                    .execute()
                )

                if created.data:
                    make_id = created.data[0]["id"]
                    self.make_cache[make_name] = make_id
                    return make_id

        except Exception:
            logger.exception("Make lookup failed")

        return None

    # ============================================================
    # MODEL
    # ============================================================

    async def get_model_id(
        self,
        make_id: Optional[int],
        model_name: Optional[str],
        create: bool = False,
    ) -> Optional[int]:

        if not make_id or not model_name:
            return None

        model_name = model_name.strip()

        cache_key = (make_id, model_name)

        if cache_key in self.model_cache:
            return self.model_cache[cache_key]

        try:

            response = (
                self.supabase
                .table("vehicle_models")
                .select("id")
                .eq("make_id", make_id)
                .ilike("name", model_name)
                .maybe_single()
                .execute()
            )

            if response.data:
                model_id = response.data["id"]
                self.model_cache[cache_key] = model_id
                return model_id

            if create:

                created = (
                    self.supabase
                    .table("vehicle_models")
                    .insert({
                        "make_id": make_id,
                        "name": model_name
                    })
                    .execute()
                )

                if created.data:
                    model_id = created.data[0]["id"]
                    self.model_cache[cache_key] = model_id
                    return model_id

        except Exception:
            logger.exception("Model lookup failed")

        return None

    # ============================================================
    # RESOLVE
    # ============================================================

    async def resolve(
        self,
        listing: dict,
        create_missing: bool = False,
    ) -> dict:

        make = listing.get("make")
        model = listing.get("model")

        make_id = await self.get_make_id(
            make,
            create=create_missing,
        )

        model_id = await self.get_model_id(
            make_id,
            model,
            create=create_missing,
        )

        return {
            "make": make,
            "model": model,
            "make_id": make_id,
            "model_id": model_id,
        }
