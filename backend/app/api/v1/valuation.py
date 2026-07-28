"""
Valuation API
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

from app.schemas.request import ValuationRequest
from app.schemas.response import ValuationResponse
from app.engines.valuation_engine import ValuationEngine
from app.core.database import supabase
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

valuation_engine = ValuationEngine()


# ─── Helpers ──────────────────────────────────────────────────────────


async def get_variant_from_supabase(variant_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch a vehicle variant from Supabase.
    
    Uses the CURRENT schema:
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

        # Fuel type lookup
        fuel_lookup = {
            1: "diesel",
            2: "petrol",
            3: "hybrid",
            4: "electric",
        }

        # Transmission lookup
        transmission_lookup = {
            1: "manual",
            2: "automatic",
            3: "cvt",
        }

        return {
            "id": row["id"],
            "name": row.get("name", "Unknown"),
            "generation_id": row.get("generation_id"),
            "engine_cc": row.get("engine_size_cc", 0),
            "power_hp": row.get("power_hp", 0),
            "torque_nm": row.get("torque_nm", 0),
            "fuel_type": fuel_lookup.get(row.get("fuel_type_id"), "petrol"),
            "transmission": transmission_lookup.get(row.get("transmission_type_id"), "automatic"),
            "body_type": row.get("body_type", "SUV"),
            "market_value": row.get("market_value", 2800000),
            "depreciation_class": row.get("depreciation_class", "SUV_D"),
            "fuel_consumption_combined": row.get("fuel_consumption_combined", 8.0),
            "seats": row.get("seats", 5),
            "doors": row.get("doors", 4),
        }

    except Exception as e:
        logger.error(f"Error fetching variant {variant_id}: {e}")
        return None


# ─── Calculate Valuation ─────────────────────────────────────────────


@router.post("/calculate")
async def calculate_valuation(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Calculate vehicle valuation.
    
    Uses scraped market data and database values for accurate pricing.
    """
    try:
        logger.info(f"Valuation request for variant {request.variant_id} by user {current_user.get('id') if current_user else 'anonymous'}")

        # Get variant from database
        variant = await get_variant_from_supabase(request.variant_id)

        if variant is None:
            raise HTTPException(
                status_code=404,
                detail=f"Vehicle variant '{request.variant_id}' not found."
            )

        logger.info(f"Variant found: {variant.get('name', 'Unknown')}")

        # ─── Extract modifications safely ──────────────────────────────
        modifications = []
        if hasattr(request, 'modifications') and request.modifications:
            modifications = request.modifications
        
        custom_adjustments = {}
        if hasattr(request, 'custom_adjustments') and request.custom_adjustments:
            custom_adjustments = request.custom_adjustments

        # ─── Calculate valuation ──────────────────────────────────────
        result = valuation_engine.calculate_valuation(
            variant=variant,
            year=request.year,
            mileage=request.mileage,
            condition=request.condition,
            accident_history=request.accident_history,
            previous_owners=request.previous_owners,
            location=request.location,
            service_history=request.service_history,
            modifications=modifications,
            custom_adjustments=custom_adjustments
        )

        # ─── Build response ────────────────────────────────────────────
        return {
            "status": "success",
            "message": "Valuation calculated successfully",
            "timestamp": datetime.utcnow().isoformat(),
            "data": result,
            "user_id": current_user.get("id") if current_user else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Valuation calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Variant Lookup ──────────────────────────────────────────────────


@router.get("/variant/{variant_id}")
async def get_variant(variant_id: int):
    """Get vehicle variant details"""
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching variant {variant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Bulk Valuation ──────────────────────────────────────────────────


@router.post("/calculate/bulk")
async def calculate_bulk_valuation(
    requests: List[ValuationRequest],
    current_user: dict = Depends(get_current_user)
):
    """Calculate valuations for multiple vehicles"""
    try:
        results = []
        errors = []

        for request in requests:
            try:
                variant = await get_variant_from_supabase(request.variant_id)
                if variant is None:
                    errors.append({
                        "variant_id": request.variant_id,
                        "error": "Variant not found"
                    })
                    continue

                modifications = []
                if hasattr(request, 'modifications') and request.modifications:
                    modifications = request.modifications
                
                custom_adjustments = {}
                if hasattr(request, 'custom_adjustments') and request.custom_adjustments:
                    custom_adjustments = request.custom_adjustments

                result = valuation_engine.calculate_valuation(
                    variant=variant,
                    year=request.year,
                    mileage=request.mileage,
                    condition=request.condition,
                    accident_history=request.accident_history,
                    previous_owners=request.previous_owners,
                    location=request.location,
                    service_history=request.service_history,
                    modifications=modifications,
                    custom_adjustments=custom_adjustments
                )

                results.append({
                    "variant_id": request.variant_id,
                    "result": result
                })

            except Exception as e:
                errors.append({
                    "variant_id": request.variant_id,
                    "error": str(e)
                })

        return {
            "status": "success" if results else "partial",
            "timestamp": datetime.utcnow().isoformat(),
            "total": len(requests),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors
        }

    except Exception as e:
        logger.error(f"Bulk valuation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Valuation History ──────────────────────────────────────────────


@router.get("/history")
async def get_valuation_history(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get valuation history for current user"""
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        response = supabase.table("valuation_reports")\
            .select("*")\
            .eq("user_id", current_user.get("id"))\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()

        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": response.data or []
        }

    except Exception as e:
        logger.error(f"Error fetching valuation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Market Comparison ──────────────────────────────────────────────


@router.get("/compare/{variant_id}")
async def get_market_comparison(
    variant_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get market comparison for a vehicle"""
    try:
        variant = await get_variant_from_supabase(variant_id)
        if variant is None:
            raise HTTPException(status_code=404, detail="Variant not found")

        # Get similar vehicles from market data
        response = supabase.table("market_prices")\
            .select("*")\
            .ilike("make", f"%{variant.get('name', '').split()[0]}%")\
            .limit(20)\
            .execute()

        similar_listings = response.data or []

        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "vehicle": variant,
                "similar_listings": similar_listings,
                "total_similar": len(similar_listings)
            }
        }

    except Exception as e:
        logger.error(f"Error fetching market comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))
