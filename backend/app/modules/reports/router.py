# app/modules/reports/router.py
# Auto-D Kenya - Reports API

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_user
from app.modules.reports.service import ReportService

router = APIRouter(
    prefix="/reports",
    tags=["Reports"]
)

report_service = ReportService()


@router.get(
    "/valuation/{vehicle_id}",
    summary="Generate Vehicle Valuation Report",
    description="Generate a valuation report using a paid M-Pesa transaction."
)
async def generate_valuation_report(
    vehicle_id: str,
    payment_id: str = Query(..., description="UUID of the successful payment"),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await report_service.generate_valuation_report(
            vehicle_id=vehicle_id,
            payment_id=payment_id,
            user_id=current_user["id"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/running-cost/{vehicle_id}",
    summary="Generate Running Cost Report",
    description="Generate a running cost report using a paid M-Pesa transaction."
)
async def generate_running_cost_report(
    vehicle_id: str,
    payment_id: str = Query(..., description="UUID of the successful payment"),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await report_service.generate_running_cost_report(
            vehicle_id=vehicle_id,
            payment_id=payment_id,
            user_id=current_user["id"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/history",
    summary="Report History",
)
async def get_report_history(
    current_user: dict = Depends(get_current_user),
):
    return await report_service.get_report_history(current_user["id"])


@router.get(
    "/download/{report_id}",
    summary="Download Report",
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
)
async def delete_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Delete report not implemented yet."
    )
