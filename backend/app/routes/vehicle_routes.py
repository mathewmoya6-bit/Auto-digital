# routes/vehicle_routes.py
# Auto-D Kenya - Vehicle Routes
# ================================================================
# TYPE: ROUTES - Vehicle CRUD endpoints

from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime

from database import get_supabase
from schemas import VehicleRequest, VehicleResponse
from auth import get_current_user

router = APIRouter()


@router.get("/makes")
async def get_makes(category_id: Optional[str] = None):
    """Get all vehicle makes."""
    try:
        supabase = get_supabase()
        query = supabase.table("vehicle_makes").select("*").eq("active", True)
        if category_id:
            query = query.eq("category_id", category_id)
        response = query.order("make_name").execute()
        return {"data": response.data, "count": len(response.data)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/models/{make_id}")
async def get_models(make_id: str):
    """Get models for a specific make."""
    try:
        supabase = get_supabase()
        response = supabase.table("vehicle_models").select("*").eq("make_id", make_id).eq("active", True).order("model_name").execute()
        return {"data": response.data, "count": len(response.data)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/generations/{model_id}")
async def get_generations(model_id: str):
    """Get generations for a specific model."""
    try:
        supabase = get_supabase()
        response = supabase.table("vehicle_generations").select("*").eq("model_id", model_id).eq("active", True).order("generation_start_year", desc=True).execute()
        return {"data": response.data, "count": len(response.data)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/variants/{generation_id}")
async def get_variants(generation_id: str):
    """Get variants for a specific generation."""
    try:
        supabase = get_supabase()
        response = supabase.table("vehicle_variants").select("*").eq("generation_id", generation_id).eq("active", True).order("variant_name").execute()
        return {"data": response.data, "count": len(response.data)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/variant/{variant_id}")
async def get_variant(variant_id: str):
    """Get detailed variant information."""
    try:
        supabase = get_supabase()
        response = supabase.table("vehicle_variants").select("*").eq("variant_id", variant_id).execute()
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Variant not found"
            )
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/search")
async def search_vehicles(q: str, limit: int = 10):
    """Search for vehicles."""
    try:
        supabase = get_supabase()
        results = []
        
        makes = supabase.table("vehicle_makes").select("*").ilike("make_name", f"%{q}%").limit(limit).execute()
        for item in makes.data:
            item["type"] = "make"
            results.append(item)
        
        models = supabase.table("vehicle_models").select("*").ilike("model_name", f"%{q}%").limit(limit).execute()
        for item in models.data:
            item["type"] = "model"
            results.append(item)
        
        variants = supabase.table("vehicle_variants").select("*").ilike("variant_name", f"%{q}%").limit(limit).execute()
        for item in variants.data:
            item["type"] = "variant"
            results.append(item)
        
        return {"data": results, "count": len(results)}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/vehicles")
async def add_vehicle(
    request: VehicleRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add a new vehicle for the user."""
    try:
        supabase = get_supabase()
        
        existing = supabase.table("vehicles").select("*").eq("user_id", current_user["id"]).eq("plate", request.plate.upper()).execute()
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vehicle already exists"
            )
        
        data = {
            "user_id": current_user["id"],
            "plate": request.plate.upper(),
            "make_model": request.make_model,
            "vin": request.vin,
            "year": request.year,
            "mileage": request.mileage,
            "created_at": datetime.utcnow().isoformat()
        }
        
        response = supabase.table("vehicles").insert(data).execute()
        
        if response.data:
            return {"message": "Vehicle added successfully", "vehicle": response.data[0]}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add vehicle"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/vehicles")
async def get_user_vehicles(current_user: dict = Depends(get_current_user)):
    """Get all vehicles for the current user."""
    try:
        supabase = get_supabase()
        response = supabase.table("vehicles").select("*").eq("user_id", current_user["id"]).order("created_at", desc=True).execute()
        return {"data": response.data, "count": len(response.data)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/vehicles/{vehicle_id}")
async def delete_vehicle(
    vehicle_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a vehicle."""
    try:
        supabase = get_supabase()
        
        response = supabase.table("vehicles").select("*").eq("id", vehicle_id).eq("user_id", current_user["id"]).execute()
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found"
            )
        
        supabase.table("vehicles").delete().eq("id", vehicle_id).execute()
        return {"message": "Vehicle deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
