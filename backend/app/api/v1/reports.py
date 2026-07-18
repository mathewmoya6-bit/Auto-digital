# backend/app/api/v1/reports.py
"""
Reports API - Report generation endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List
from app.services.report_service import ReportService
from app.core.security import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
report_service = ReportService()


@router.get("/mileage")
async def get_mileage_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get mileage report for the current user"""
    try:
        user_id = current_user.get("id")
        report = report_service.generate_mileage_report(user_id, start_date, end_date)
        return report
    except Exception as e:
        logger.error(f"Error generating mileage report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate mileage report"
        )


@router.get("/ownership")
async def get_ownership_report(
    current_user: dict = Depends(get_current_user)
):
    """Get ownership report for the current user"""
    try:
        user_id = current_user.get("id")
        report = report_service.generate_ownership_report(user_id)
        return report
    except Exception as e:
        logger.error(f"Error generating ownership report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate ownership report"
        )


@router.get("/valuation")
async def get_valuation_report(
    vehicle_ids: Optional[List[str]] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get valuation report for vehicles"""
    try:
        user_id = current_user.get("id")
        report = report_service.generate_valuation_report(user_id, vehicle_ids)
        return report
    except Exception as e:
        logger.error(f"Error generating valuation report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate valuation report"
        )
