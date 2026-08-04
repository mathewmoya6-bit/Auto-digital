"""
Auto-D Kenya - Admin Router
================================================
"""

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_admin
from app.modules.admin.service import AdminService

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)

service = AdminService()


@router.get("/dashboard")
async def dashboard(
    admin=Depends(get_current_admin),
):
    return await service.dashboard()
