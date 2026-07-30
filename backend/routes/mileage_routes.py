# routes/mileage_routes.py
# Auto-D Kenya - Mileage Calculator Routes
# ================================================================
# TYPE: ROUTES - Mileage calculation endpoints

from fastapi import APIRouter, HTTPException, status, Depends

from schemas import MileageRequest, MileageResponse
from auth import get_current_user
from mileage import MileageService

router = APIRouter()
mileage_service = MileageService()


@router.post("/mileage/calculate", response_model=MileageResponse)
async def calculate_mileage(
    request: MileageRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Calculate mileage costs and fuel consumption.
    """
    try:
        result = await mileage_service.calculate(request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Mileage calculation failed: {str(e)}"
        )


@router.get("/mileage/history")
async def get_mileage_history(current_user: dict = Depends(get_current_user)):
    """
    Get mileage calculation history for the current user.
    """
    try:
        supabase = get_supabase()
        response = supabase.table("mileage_reports").select("*").eq("user_id", current_user["id"]).order("created_at", desc=True).execute()
        return {"data": response.data, "count": len(response.data)}
    except Exception as e:
        return {"data": [], "count": 0}
