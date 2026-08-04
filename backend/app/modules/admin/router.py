from fastapi import APIRouter, Depends

from .dependencies import require_admin
from .schemas import DashboardStats, ServiceUpdate
from .service import AdminService

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)

service = AdminService()


@router.get(
    "/dashboard",
    response_model=DashboardStats,
)
async def dashboard(
    admin=Depends(require_admin),
):
    return await service.dashboard()


@router.get("/services")
async def services(
    admin=Depends(require_admin),
):
    return await service.list_services()


@router.put("/services/{service_id}")
async def update_service(
    service_id: int,
    data: ServiceUpdate,
    admin=Depends(require_admin),
):
    return await service.update_service(
        service_id,
        data.model_dump(exclude_none=True),
    )
