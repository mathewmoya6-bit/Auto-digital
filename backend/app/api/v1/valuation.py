"""
Valuation API Endpoints
Handles vehicle valuation calculations with market adjustments
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from app.schemas.request import ValuationRequest
from app.schemas.response import ValuationResponse, ErrorResponse
from app.services.vehicle_service import VehicleService
from app.engines.valuation_engine import ValuationEngine
from app.core.database import supabase

# Optional authentication - comment out if not needed
# from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()
vehicle_service = VehicleService()
valuation_engine = ValuationEngine()


@router.post(
    "/calculate",
    response_model=ValuationResponse,
    summary="Calculate vehicle valuation",
    description="Calculate the market value of a vehicle based on its variant and condition"
)
async def calculate_valuation(
    request: ValuationRequest,
    # Uncomment for authentication:
    # current_user: dict = Depends(get_current_user)
) -> ValuationResponse:
    """
    Calculate vehicle valuation based on variant ID and vehicle details
    
    This endpoint:
    1. Fetches vehicle variant data from Supabase
    2. Passes it to the valuation engine
    3. Returns comprehensive valuation with adjustments
    
    **Request Body:**
    - `variant_id`: Vehicle variant ID from database
    - `year`: Year of manufacture
    - `mileage`: Current odometer reading in km
    - `condition`: Vehicle condition (excellent, very_good, good, fair, poor)
    - `accident_history`: Accident history (none, minor, major, total_loss)
    - `previous_owners`: Number of previous owners
    - `service_history`: Whether service history is available
    - `location`: Vehicle location/county
    - `modifications`: List of modifications (optional)
    - `custom_adjustments`: Custom value adjustments (optional)
    - `images`: Base64 encoded images for AI analysis (optional)
    """
    try:
        logger.info(f"📊 Valuation request for variant: {request.variant_id}")
        
        # ─── 1. Get Vehicle Details ──────────────────────────────
        variant_data = await get_variant_from_supabase(request.variant_id)
        
        if not variant_data:
            # Try fallback using vehicle_service
            try:
                variant_data = vehicle_service.get_variant(request.variant_id)
                if variant_data:
                    logger.info(f"✅ Found variant via vehicle_service: {variant_data.get('name', 'Unknown')}")
            except Exception as e:
                logger.warning(f"Vehicle service fallback failed: {e}")
                variant_data = None
        
        if not variant_data:
            logger.error(f"❌ Vehicle variant not found: {request.variant_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vehicle variant '{request.variant_id}' not found. Please check the variant ID and try again."
            )
        
        logger.info(f"✅ Found variant: {variant_data.get('name', 'Unknown')}")
        logger.info(f"   Make: {variant_data.get('make_name', 'Unknown')}")
        logger.info(f"   Model: {variant_data.get('model_name', 'Unknown')}")
        logger.info(f"   Base Value: KES {variant_data.get('market_value', 0):,}")
        
        # ─── 2. Prepare Data for Valuation Engine ──────────────
        variant_for_engine = {
            "market_value": variant_data.get("market_value", 0),
            "depreciation_class": variant_data.get("depreciation_class", "DEFAULT"),
            "fuel_type": variant_data.get("fuel_type", "petrol"),
            "transmission": variant_data.get("transmission", "automatic"),
            "body_type": variant_data.get("body_type", "sedan"),
            "name": variant_data.get("name", "Unknown"),
            "model_name": variant_data.get("model_name", variant_data.get("name", "Unknown")),
            "make_name": variant_data.get("make_name", ""),
            "engine_cc": variant_data.get("engine_cc", 0),
            "year": variant_data.get("year", request.year),
        }
        
        # ─── 3. Calculate Valuation ─────────────────────────────
        try:
            result = valuation_engine.calculate_valuation(
                variant=variant_for_engine,
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
            
            logger.info(f"✅ Valuation complete: KES {result['market_value']:,.0f}")
            logger.info(f"   Confidence: {result['confidence_score']:.1f}%")
            logger.info(f"   Value Retained: {result['value_retained']:.1f}%")
            
        except Exception as e:
            logger.error(f"❌ Valuation engine error: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Valuation calculation failed: {str(e)}"
            )
        
        # ─── 4. Save Valuation History (Optional) ──────────────
        try:
            # Uncomment to save to database
            # await save_valuation_history(
            #     variant_id=request.variant_id,
            #     user_id=current_user.get("id") if current_user else None,
            #     request=request,
            #     result=result
            # )
            pass
        except Exception as e:
            logger.warning(f"⚠️ Could not save valuation history: {e}")
        
        # ─── 5. Return Response ──────────────────────────────────
        return ValuationResponse(
            status="success",
            data=result,
            timestamp=datetime.utcnow().isoformat(),
            message="Valuation calculated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in valuation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post(
    "/batch",
    summary="Batch vehicle valuation",
    description="Calculate valuations for multiple vehicles at once"
)
async def batch_valuation(
    requests: List[ValuationRequest],
    # Uncomment for authentication:
    # current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Calculate valuations for multiple vehicles in batch
    
    **Request Body:**
    - List of ValuationRequest objects
    
    **Response:**
    - Results for each valuation with success/error status
    """
    results = []
    errors = []
    
    for idx, request in enumerate(requests):
        try:
            # Calculate valuation for each request
            # Note: This calls the calculate_valuation function which has its own error handling
            result = await calculate_valuation(request)
            results.append({
                "index": idx,
                "status": "success",
                "data": result.data,
                "variant_id": request.variant_id
            })
        except HTTPException as e:
            errors.append({
                "index": idx,
                "status": "error",
                "error": e.detail,
                "variant_id": request.variant_id
            })
        except Exception as e:
            errors.append({
                "index": idx,
                "status": "error",
                "error": str(e),
                "variant_id": request.variant_id
            })
    
    return {
        "status": "success" if len(errors) == 0 else "partial",
        "total": len(requests),
        "success_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get(
    "/variant/{variant_id}",
    summary="Get variant details",
    description="Get detailed information about a vehicle variant"
)
async def get_variant_details(
    variant_id: str,
    # Uncomment for authentication:
    # current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get detailed variant information including base value
    
    **Path Parameters:**
    - `variant_id`: Vehicle variant ID
    
    **Response:**
    - Complete variant data including model and make information
    """
    try:
        variant = await get_variant_from_supabase(variant_id)
        if not variant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Variant '{variant_id}' not found"
            )
        
        return {
            "status": "success",
            "data": variant,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching variant: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch variant: {str(e)}"
        )


@router.get(
    "/market-trends",
    summary="Get market trends",
    description="Get current market trends for vehicles"
)
async def get_market_trends(
    make: Optional[str] = None,
    model: Optional[str] = None,
    # Uncomment for authentication:
    # current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get market trends for vehicles
    
    **Query Parameters:**
    - `make`: Filter by make (optional)
    - `model`: Filter by model (optional)
    
    **Response:**
    - Market trends data including sentiment and average depreciation
    """
    try:
        # Build query
        query = supabase.table("vehicle_variants").select("*")
        
        # For now, return sample trends
        # In production, this would query actual market data
        return {
            "status": "success",
            "data": {
                "trend": "stable",
                "average_depreciation": 12.5,
                "market_sentiment": "positive",
                "last_updated": datetime.utcnow().isoformat(),
                "top_makes": [
                    {"name": "Toyota", "market_share": 35.2},
                    {"name": "Nissan", "market_share": 18.7},
                    {"name": "Honda", "market_share": 12.5},
                    {"name": "Subaru", "market_share": 8.3},
                    {"name": "Mercedes-Benz", "market_share": 6.1}
                ],
                "price_trends": {
                    "last_month": 1.2,
                    "last_3_months": 3.5,
                    "last_6_months": 8.7,
                    "last_year": -2.1
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching market trends: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch market trends: {str(e)}"
        )


@router.get(
    "/depreciation/{variant_id}",
    summary="Get depreciation curve",
    description="Get the depreciation curve for a vehicle variant"
)
async def get_depreciation_curve(
    variant_id: str,
    years: int = 10,
    # Uncomment for authentication:
    # current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the depreciation curve for a vehicle over time
    
    **Path Parameters:**
    - `variant_id`: Vehicle variant ID
    
    **Query Parameters:**
    - `years`: Number of years to project (default: 10)
    
    **Response:**
    - Depreciation curve data with annual values
    """
    try:
        variant = await get_variant_from_supabase(variant_id)
        if not variant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Variant '{variant_id}' not found"
            )
        
        base_value = variant.get("market_value", 0)
        depreciation_class = variant.get("depreciation_class", "DEFAULT")
        
        # Get depreciation rate
        depreciation_rate = valuation_engine.get_depreciation_rate(depreciation_class)
        
        # Generate depreciation curve
        curve = []
        current_value = base_value
        for year in range(years + 1):
            curve.append({
                "year": year,
                "value": round(current_value, 2),
                "depreciation": round(base_value - current_value, 2),
                "value_retained": round((current_value / base_value) * 100, 1) if base_value > 0 else 0
            })
            current_value *= (1 - depreciation_rate)
        
        return {
            "status": "success",
            "data": {
                "variant_id": variant_id,
                "variant_name": variant.get("name", "Unknown"),
                "base_value": base_value,
                "depreciation_rate": depreciation_rate * 100,
                "depreciation_class": depreciation_class,
                "curve": curve
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating depreciation curve: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate depreciation curve: {str(e)}"
        )


# ─── HELPER FUNCTIONS ──────────────────────────────────────────────

async def get_variant_from_supabase(variant_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch variant data from Supabase with related model and make info
    """
    try:
        # Try to get variant with joins
        response = supabase.table("vehicle_variants")\
            .select("*, vehicle_models(*, vehicle_makes(*))")\
            .eq("id", variant_id)\
            .execute()
        
        if not response.data:
            logger.warning(f"⚠️ Variant '{variant_id}' not found in Supabase")
            return None
        
        variant = response.data[0]
        
        # Extract nested data
        model_data = variant.get("vehicle_models", {})
        make_data = model_data.get("vehicle_makes", {}) if model_data else {}
        
        # Flatten the data for the valuation engine
        flattened = {
            "id": variant.get("id"),
            "name": variant.get("name"),
            "model_name": model_data.get("name") if model_data else None,
            "make_name": make_data.get("name") if make_data else None,
            "market_value": variant.get("market_value", 0),
            "depreciation_class": variant.get("depreciation_class", "DEFAULT"),
            "fuel_type": variant.get("fuel_type", "petrol"),
            "transmission": variant.get("transmission", "automatic"),
            "body_type": model_data.get("body_type") if model_data else "sedan",
            "engine_cc": variant.get("engine_cc", 0),
            "year": variant.get("year", 2020),
            "fuel_consumption": variant.get("fuel_consumption", 8.0),
            "insurance_group": variant.get("insurance_group", 5),
            "service_interval": variant.get("service_interval", 15000),
            "service_cost": variant.get("service_cost", 15000),
            "tyre_cost": variant.get("tyre_cost", 12000),
        }
        
        # Remove None values
        flattened = {k: v for k, v in flattened.items() if v is not None}
        
        return flattened
        
    except Exception as e:
        logger.error(f"❌ Supabase query error: {e}", exc_info=True)
        return None


async def save_valuation_history(
    variant_id: str,
    user_id: Optional[str],
    request: ValuationRequest,
    result: Dict[str, Any]
) -> None:
    """
    Save valuation history to Supabase for analytics
    """
    try:
        history_data = {
            "variant_id": variant_id,
            "user_id": user_id,
            "year": request.year,
            "mileage": request.mileage,
            "condition": request.condition,
            "accident_history": request.accident_history,
            "previous_owners": request.previous_owners,
            "location": request.location,
            "market_value": result.get("market_value", 0),
            "trade_value": result.get("trade_value", 0),
            "retail_value": result.get("retail_value", 0),
            "confidence_score": result.get("confidence_score", 0),
            "valuation_data": result,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Uncomment when table exists
        # supabase.table("valuation_history").insert(history_data).execute()
        
        logger.info(f"💾 Valuation history saved for variant: {variant_id}")
        
    except Exception as e:
        logger.warning(f"⚠️ Failed to save valuation history: {e}")
        # Don't raise - this is non-critical
