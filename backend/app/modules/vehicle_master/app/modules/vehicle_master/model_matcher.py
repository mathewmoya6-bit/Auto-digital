"""
Auto-D Kenya
Vehicle Model Matching Engine

Matches imported price models
to standard vehicle catalogue models.
"""

import logging
from typing import Optional, Dict, Any, List

from rapidfuzz import fuzz

from app.core.database import get_supabase


logger = logging.getLogger(__name__)


class VehicleModelMatcher:
    """
    Intelligent vehicle model matching service.
    """

    def __init__(self):
        self.db = get_supabase()


    # ======================================================
    # NORMALIZE
    # ======================================================

    def normalize(self, value: str) -> str:
        """
        Normalize vehicle names.
        """

        if not value:
            return ""

        value = value.lower()

        replacements = {
            "-": " ",
            "_": " ",
            "/": " ",
            ".": " "
        }

        for a,b in replacements.items():
            value = value.replace(a,b)

        return " ".join(value.split())


    # ======================================================
    # EXACT MATCH
    # ======================================================

    async def exact_match(
        self,
        make:str,
        model:str
    ) -> Optional[Dict[str,Any]]:

        response = (
            self.db
            .table("vehicle_models")
            .select(
                """
                id,
                name,
                vehicle_makes!inner(name)
                """
            )
            .eq("vehicle_makes.name",make)
            .ilike("name",model)
            .execute()
        )


        if response.data:

            return {
                "model_id":response.data[0]["id"],
                "model":response.data[0]["name"],
                "score":1,
                "method":"exact"
            }


        return None



    # ======================================================
    # ALIAS MATCH
    # ======================================================

    async def alias_match(
        self,
        make:str,
        model:str
    ):

        normalized=self.normalize(model)


        result = (
            self.db
            .table("vehicle_model_aliases")
            .select(
                """
                standard_model_id,
                vehicle_models(name)
                """
            )
            .eq("normalized_alias",normalized)
            .execute()
        )


        if result.data:

            item=result.data[0]


            return {

                "model_id":
                item["standard_model_id"],

                "model":
                item["vehicle_models"]["name"],

                "score":0.95,

                "method":"alias"

            }


        return None



    # ======================================================
    # FUZZY MATCH
    # ======================================================

    async def fuzzy_match(
        self,
        make:str,
        model:str
    ):


        catalog = (

            self.db
            .table("vehicle_models")
            .select(
                """
                id,
                name,
                vehicle_makes!inner(name)
                """
            )
            .eq("vehicle_makes.name",make)
            .execute()

        )


        if not catalog.data:
            return None



        best=None
        best_score=0


        search=self.normalize(model)



        for item in catalog.data:


            score=fuzz.ratio(
                search,
                self.normalize(item["name"])
            )


            if score>best_score:

                best_score=score
                best=item



        if best_score >=75:


            return {

                "model_id":best["id"],

                "model":best["name"],

                "score":
                round(best_score/100,2),

                "method":"fuzzy"

            }


        return None



    # ======================================================
    # MASTER MATCH FUNCTION
    # ======================================================


    async def match_vehicle(
        self,
        make:str,
        model:str
    ):


        # 1 Exact

        result=await self.exact_match(
            make,
            model
        )

        if result:
            return result



        # 2 Alias

        result=await self.alias_match(
            make,
            model
        )

        if result:
            return result



        # 3 Fuzzy

        result=await self.fuzzy_match(
            make,
            model
        )

        if result:
            return result



        return {

            "matched":False,

            "make":make,

            "model":model,

            "score":0,

            "method":"unmatched"

        }
