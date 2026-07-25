"""
Valuation API
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Optional, Dict, Any
import logging

from app.schemas.request import ValuationRequest
from app.schemas.response import ValuationResponse
from app.engines.valuation_engine import ValuationEngine
from app.core.database import supabase

logger = logging.getLogger(__name__)

router = APIRouter()

valuation_engine = ValuationEngine()


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------


async def get_variant_from_supabase(variant_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch a vehicle variant.

    Uses the CURRENT schema.

    vehicle_variants
        id
        generation_id
        name
        fuel_type_id
        transmission_type_id
        engine_size_cc
        power_hp
        torque_nm
        ...
    """

    try:

        response = (
            supabase
            .table("vehicle_variants")
            .select("*")
            .eq("id", int(variant_id))
            .single()
            .execute()
        )

        if not response.data:
            return None

        row = response.data

        fuel_lookup = {
            1: "diesel",
            2: "petrol",
            3: "hybrid",
            4: "electric",
        }

        transmission_lookup = {
            1: "manual",
            2: "automatic",
            3: "cvt",
        }

        return {

            "id": row["id"],

            "name": row["name"],

            "generation_id": row["generation_id"],

            "engine_cc": row.get("engine_size_cc", 0),

            "power_hp": row.get("power_hp", 0),

            "torque_nm": row.get("torque_nm", 0),

            "fuel_type": fuel_lookup.get(
                row.get("fuel_type_id"),
                "petrol"
            ),

            "transmission": transmission_lookup.get(
                row.get("transmission_type_id"),
                "automatic"
            ),

            "body_type": "SUV",

            "market_value": 2800000,

            "depreciation_class": "SUV"

        }

    except Exception as e:
        logger.exception(e)
        return None


# -------------------------------------------------------------------------
# Calculate valuation
# -------------------------------------------------------------------------


@router.post("/calculate", response_model=ValuationResponse)
async def calculate_valuation(request: ValuationRequest):

    logger.info(f"Valuation request for variant {request.variant_id}")

    variant = await get_variant_from_supabase(request.variant_id)

    if variant is None:

        raise HTTPException(
            status_code=404,
            detail=f"Vehicle variant '{request.variant_id}' not found."
        )

    logger.info(f"Variant found: {variant['name']}")

    result = valuation_engine.calculate_valuation(

        variant=variant,

        year=request.year,

        mileage=request.mileage,

        condition=request.condition,

        accident_history=request.accident_history,

        previous_owners=request.previous_owners,

        location=request.location,

        service_history=request.service_history,

        modifications=request.modifications or [],

        custom_adjustments=request.custom_adjustments or {}

    )

    return ValuationResponse(

        status="success",

        message="Valuation calculated successfully",

        timestamp=datetime.utcnow().isoformat(),

        data=result

    )


# -------------------------------------------------------------------------
# Variant lookup
# -------------------------------------------------------------------------


@router.get("/variant/{variant_id}")
async def get_variant(variant_id: int):

    variant = await get_variant_from_supabase(variant_id)

    if variant is None:

        raise HTTPException(
            status_code=404,
            detail="Variant not found"
        )

    return {

        "status": "success",

        "timestamp": datetime.utcnow().isoformat(),

        "data": variant

    }
