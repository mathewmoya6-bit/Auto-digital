# app/modules/scraper/vehicle_lookup.py
# ================================================================
# Auto-D Kenya - Vehicle Lookup
# ================================================================


import logging

from app.core.database import get_supabase


logger = logging.getLogger(__name__)


class VehicleLookup:


    def __init__(self):

        self.supabase = get_supabase()



    async def get_make_id(
        self,
        make_name
    ):


        if not make_name:

            return None


        try:

            response = (
                self.supabase
                .table("vehicle_makes")
                .select("id")
                .ilike(
                    "name",
                    make_name.strip()
                )
                .limit(1)
                .execute()
            )


            if response.data:

                return response.data[0]["id"]


        except Exception as e:

            logger.error(
                f"Make lookup error: {e}"
            )


        return None





    async def get_model_id(
        self,
        make_id,
        model_name
    ):


        if not make_id or not model_name:

            return None


        try:

            response = (
                self.supabase
                .table("vehicle_models")
                .select("id")
                .eq(
                    "make_id",
                    make_id
                )
                .ilike(
                    "name",
                    model_name.strip()
                )
                .limit(1)
                .execute()
            )


            if response.data:

                return response.data[0]["id"]


        except Exception as e:

            logger.error(
                f"Model lookup error: {e}"
            )


        return None





    async def resolve(
        self,
        listing
    ):


        make_id = await self.get_make_id(
            listing.get("make")
        )


        model_id = await self.get_model_id(
            make_id,
            listing.get("model")
        )


        return {

            "make_id":
                make_id,

            "model_id":
                model_id

        }
