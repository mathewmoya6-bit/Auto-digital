# app/modules/reports/router.py
# Auto-D Kenya - Reports API
# ================================================================
# TYPE: MODULE - FastAPI Routes

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.modules.reports.service import ReportService

router = APIRouter(
    prefix="/reports",
    tags=["Reports"]
)

report_service = ReportService()


@router.get(
    "/valuation/{vehicle_id}",
    summary="Generate Quick Vehicle Valuation Report",
    description="Returns a quick market valuation report for the selected vehicle."
)
async def generate_valuation_report(
    vehicle_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        return await report_service.generate_valuation_report(
            vehicle_id=vehicle_id,
            user_id=current_user["id"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/running-cost/{vehicle_id}",
    summary="Generate Running Cost Report",
    description="Returns the annual running cost report for the selected vehicle."
)
async def generate_running_cost_report(
    vehicle_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        return await report_service.generate_running_cost_report(
            vehicle_id=vehicle_id,
            user_id=current_user["id"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/history",
    summary="Report History",
    description="Returns previously generated reports for the logged-in user."
)
async def get_report_history(
    current_user: dict = Depends(get_current_user),
):
    return await report_service.get_report_history(current_user["id"])


@router.get(
    "/download/{report_id}",
    summary="Download Report",
    description="Download a generated report (PDF)."
)
async def download_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="PDF download not implemented yet."
    )


@router.delete(
    "/{report_id}",
    summary="Delete Report",
    description="Delete a previously generated report."
)
async def delete_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Delete report not implemented yet."
    )
