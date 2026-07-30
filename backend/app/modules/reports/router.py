# app/modules/reports/router.py
# Auto-D Kenya - Reports Routes
# ================================================================
# TYPE: MODULE - Reports API routes

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.dependencies import get_current_user
from app.modules.reports.service import ReportService

router = APIRouter()
report_service = ReportService()


@router.post("/reports/valuation")
async def generate_valuation_report(
    vehicle_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Generate a valuation report for a vehicle."""
    result = await report_service.generate_valuation_report(vehicle_id, current_user["id"])
    return result


@router.post("/reports/running-cost")
async def generate_running_cost_report(
    vehicle_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Generate a running cost report for a vehicle."""
    result = await report_service.generate_running_cost_report(vehicle_id, current_user["id"])
    return result


@router.get("/reports/history")
async def get_report_history(current_user: dict = Depends(get_current_user)):
    """Get report history for the current user."""
    return await report_service.get_report_history(current_user["id"])
