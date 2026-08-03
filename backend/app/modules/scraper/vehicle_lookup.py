# app/modules/scraper/vehicle_lookup.py
# ================================================================
# Auto-D Kenya - Vehicle Lookup
# ================================================================

import logging
from typing import Any, Dict, Optional

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class VehicleLookup:
    """
    Resolves vehicle make/model names to database IDs.
    """

    def __init__(self):
        self.supabase = get_supabase()

        self.make_cache: Dict[str, int] = {}
        self.model_cache: Dict[tuple[int, str], int] = {}

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _normalize(value: Optional[str]) -> Optional[str]:
        if not value:
            return None

        value = value.strip()

        return value.title() if value else None

    # ============================================================
    # MAKE
    # ============================================================

    async def get_make_id(
        self,
        make_name: Optional[str],
        create: bool = False,
    ) -> Optional[int]:

        make_name = self._normalize(make_name)

        if not make_name:
            return None

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
                    .select("id")
                    .execute()
                )

                if created.data:
                    make_id = created.data[0]["id"]
                    self.make_cache[make_name] = make_id
                    return make_id

        except Exception:
            logger.exception(
                "Failed resolving make '%s'",
                make_name,
            )

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

        model_name = self._normalize(model_name)

        if not make_id or not model_name:
            return None

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
                        "name": model_name,
                    })
                    .select("id")
                    .execute()
                )

                if created.data:
                    model_id = created.data[0]["id"]
                    self.model_cache[cache_key] = model_id
                    return model_id

        except Exception:
            logger.exception(
                "Failed resolving model '%s'",
                model_name,
            )

        return None

    # ============================================================
    # RESOLVE
    # ============================================================

    async def resolve(
        self,
        listing: Dict[str, Any],
        create_missing: bool = False,
    ) -> Dict[str, Any]:

        make = self._normalize(listing.get("make"))
        model = self._normalize(listing.get("model"))

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
