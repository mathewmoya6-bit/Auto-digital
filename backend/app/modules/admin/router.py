# app/modules/admin/router.py
# Auto-D Kenya - Admin Routes
# ================================================================
# TYPE: MODULE - Admin API routes

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.modules.admin.service import AdminService

router = APIRouter()
admin_service = AdminService()


@router.get("/admin/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    """Get admin statistics."""
    return await admin_service.get_stats()


@router.get("/admin/users")
async def get_users(current_user: dict = Depends(get_current_user)):
    """Get all users (admin only)."""
    return await admin_service.get_users()


@router.get("/admin/payments")
async def get_all_payments(current_user: dict = Depends(get_current_user)):
    """Get all payments (admin only)."""
    return await admin_service.get_all_payments()
