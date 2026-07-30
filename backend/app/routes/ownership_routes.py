# routes/ownership_routes.py
# Auto-D Kenya - Ownership Cost Routes
# ================================================================
# TYPE: ROUTES - Ownership cost calculation endpoints

from fastapi import APIRouter, HTTPException, status, Depends

from schemas import OwnershipCostRequest, OwnershipCostResponse
from auth import get_current_user
from ownership_cost import OwnershipCostService

router = APIRouter()
ownership_service = OwnershipCostService()


@router.post("/ownership/calculate", response_model=OwnershipCostResponse)
async def calculate_ownership_cost(
    request: OwnershipCostRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Calculate total cost of vehicle ownership.
    """
    try:
        result = await ownership_service.calculate(request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ownership cost calculation failed: {str(e)}"
        )


@router.get("/ownership/history")
async def get_ownership_history(current_user: dict = Depends(get_current_user)):
    """
    Get ownership cost history for the current user.
    """
    try:
        supabase = get_supabase()
        response = supabase.table("ownership_reports").select("*").eq("user_id", current_user["id"]).order("created_at", desc=True).execute()
        return {"data": response.data, "count": len(response.data)}
    except Exception as e:
        return {"data": [], "count": 0}
