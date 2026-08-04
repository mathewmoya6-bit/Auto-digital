# app/modules/admin/router.py
# Auto-D Kenya - Admin Router
# ================================================================
# TYPE: MODULE - Admin API endpoints

from typing import Optional, List
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_admin_user
from app.core.logging import get_logger
from app.modules.admin.schemas import *
from app.modules.admin.service import AdminService

logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin_user)],
)


# ─── HELPER ──────────────────────────────────────────────────────

def get_admin_service() -> AdminService:
    """Get admin service instance."""
    return AdminService()


# ─── HEALTH & STATUS ────────────────────────────────────────────

@router.get("/health", response_model=AdminHealthResponse)
async def admin_health():
    """Admin health check endpoint."""
    return AdminHealthResponse(
        status=ComponentStatus.HEALTHY,
        service="admin",
        timestamp=datetime.utcnow()
    )


@router.get("/status", response_model=AdminStatusResponse)
async def system_status(
    service: AdminService = Depends(get_admin_service),
):
    """Get system component status."""
    status_data = await service.get_system_status()
    
    return AdminStatusResponse(
        status=ComponentStatus.HEALTHY if status_data["status"] == "healthy" else ComponentStatus.DEGRADED,
        timestamp=datetime.utcnow(),
        components=ComponentStatuses(
            supabase=ComponentStatus.HEALTHY if status_data["components"].get("supabase") == "healthy" else ComponentStatus.UNHEALTHY,
            database=ComponentStatus.HEALTHY if status_data["components"].get("database") == "healthy" else ComponentStatus.UNHEALTHY,
            mpesa=ComponentStatus.HEALTHY,  # Placeholder
        )
    )


# ─── STATISTICS ──────────────────────────────────────────────────

@router.get("/stats", response_model=AdminStatsResponse)
async def admin_stats(
    service: AdminService = Depends(get_admin_service),
):
    """Get admin dashboard statistics."""
    stats = await service.get_stats()
    
    if stats.get("error"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=stats["error"]
        )
    
    return AdminStatsResponse(
        total_users=stats["total_users"],
        total_vehicles=stats["total_vehicles"],
        total_payments=stats["total_payments"],
        total_revenue=stats["total_revenue"],
        total_services_purchased=stats["total_services_purchased"],
        new_users_this_week=stats["new_users_this_week"],
        active_services=stats["active_services"],
        updated_at=datetime.fromisoformat(stats["updated_at"]) if isinstance(stats["updated_at"], str) else stats["updated_at"]
    )


# ─── USERS ──────────────────────────────────────────────────────

@router.get("/users", response_model=AdminUsersResponse)
async def list_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, description="Search by email or name"),
    service: AdminService = Depends(get_admin_service),
):
    """List all users with pagination."""
    result = await service.get_users(limit=limit, offset=offset, search=search)
    
    users = []
    for user in result["users"]:
        users.append(AdminUser(
            id=UUID(user["id"]),
            email=user["email"],
            full_name=user.get("full_name", ""),
            created_at=datetime.fromisoformat(user["created_at"]) if isinstance(user["created_at"], str) else user["created_at"],
            last_sign_in_at=datetime.fromisoformat(user["last_sign_in_at"]) if user.get("last_sign_in_at") and isinstance(user["last_sign_in_at"], str) else user.get("last_sign_in_at"),
            confirmed_at=datetime.fromisoformat(user["confirmed_at"]) if user.get("confirmed_at") and isinstance(user["confirmed_at"], str) else user.get("confirmed_at"),
            phone=user.get("phone"),
            services=[
                AdminUserService(
                    service_id=UUID(s["service_id"]),
                    service_name=s["service_name"],
                    service_code=ServiceCode(s["service_code"]),
                    status=UserServiceStatus(s["status"]),
                )
                for s in user.get("services", [])
            ],
        ))
    
    return AdminUsersResponse(
        users=users,
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.get("/users/{user_id}", response_model=AdminUserDetailResponse)
async def get_user_detail(
    user_id: UUID,
    service: AdminService = Depends(get_admin_service),
):
    """Get detailed user information."""
    try:
        user = await service.get_user_by_id(str(user_id))
        
        services = []
        for s in user.get("services", []):
            service_data = s.get("services", {})
            services.append(AdminUserService(
                service_id=UUID(s["service_id"]),
                service_name=service_data.get("name", ""),
                service_code=ServiceCode(service_data.get("code", "valuation")),
                status=UserServiceStatus(s.get("status", "active")),
            ))
        
        payments = []
        for p in user.get("payments", []):
            payments.append(AdminPayment(
                id=UUID(p["id"]),
                user_id=UUID(p["user_id"]) if p.get("user_id") else None,
                service_id=UUID(p["service_id"]) if p.get("service_id") else None,
                service_name=p.get("service_name"),
                service_code=ServiceCode(p["service_code"]) if p.get("service_code") else None,
                amount=p["amount"],
                currency=p.get("currency", "KES"),
                status=PaymentStatus(p["status"]),
                phone=p.get("phone"),
                checkout_request_id=p.get("checkout_request_id"),
                mpesa_receipt=p.get("mpesa_receipt"),
                created_at=datetime.fromisoformat(p["created_at"]) if isinstance(p["created_at"], str) else p["created_at"],
                completed_at=datetime.fromisoformat(p["completed_at"]) if p.get("completed_at") and isinstance(p["completed_at"], str) else p.get("completed_at"),
            ))
        
        return AdminUserDetailResponse(
            success=True,
            data=AdminUserDetail(
                id=UUID(user["id"]),
                email=user["email"],
                full_name=user.get("full_name", ""),
                created_at=datetime.fromisoformat(user["created_at"]) if isinstance(user["created_at"], str) else user["created_at"],
                last_sign_in_at=datetime.fromisoformat(user["last_sign_in_at"]) if user.get("last_sign_in_at") and isinstance(user["last_sign_in_at"], str) else user.get("last_sign_in_at"),
                confirmed_at=datetime.fromisoformat(user["confirmed_at"]) if user.get("confirmed_at") and isinstance(user["confirmed_at"], str) else user.get("confirmed_at"),
                phone=user.get("phone"),
                services=services,
                app_metadata=user.get("app_metadata", {}),
                user_metadata=user.get("user_metadata", {}),
                payments=payments,
            )
        )
    except Exception as e:
        logger.error(f"Error getting user details: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


@router.delete("/users/{user_id}", response_model=DeleteUserResponse)
async def delete_user(
    user_id: UUID,
    service: AdminService = Depends(get_admin_service),
):
    """Delete a user (admin only)."""
    try:
        result = await service.delete_user(str(user_id))
        return DeleteUserResponse(
            success=True,
            message=result["message"],
            user_id=user_id,
            deleted_at=datetime.fromisoformat(result["deleted_at"]) if isinstance(result["deleted_at"], str) else datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


# ─── PAYMENTS ────────────────────────────────────────────────────

@router.get("/payments", response_model=AdminPaymentsResponse)
async def list_payments(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[PaymentStatus] = None,
    user_id: Optional[UUID] = None,
    service: AdminService = Depends(get_admin_service),
):
    """List all payments with pagination and filters."""
    result = await service.get_all_payments(
        limit=limit,
        offset=offset,
        status=status.value if status else None
    )
    
    # If user_id filter is provided, filter the results
    payments_data = result["payments"]
    if user_id:
        payments_data = [p for p in payments_data if p.get("user_id") == str(user_id)]
    
    payments = []
    for p in payments_data:
        payments.append(AdminPayment(
            id=UUID(p["id"]),
            user_id=UUID(p["user_id"]) if p.get("user_id") else None,
            service_id=UUID(p["service_id"]) if p.get("service_id") else None,
            service_name=p.get("service_name"),
            service_code=ServiceCode(p["service_code"]) if p.get("service_code") else None,
            amount=p["amount"],
            currency=p.get("currency", "KES"),
            status=PaymentStatus(p["status"]),
            phone=p.get("phone"),
            checkout_request_id=p.get("checkout_request_id"),
            mpesa_receipt=p.get("mpesa_receipt"),
            created_at=datetime.fromisoformat(p["created_at"]) if isinstance(p["created_at"], str) else p["created_at"],
            completed_at=datetime.fromisoformat(p["completed_at"]) if p.get("completed_at") and isinstance(p["completed_at"], str) else p.get("completed_at"),
        ))
    
    return AdminPaymentsResponse(
        payments=payments,
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


# ─── VEHICLES ────────────────────────────────────────────────────

@router.get("/vehicles", response_model=AdminVehiclesResponse)
async def list_vehicles(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    verified: Optional[bool] = None,
    user_id: Optional[UUID] = None,
    service: AdminService = Depends(get_admin_service),
):
    """List all vehicles with pagination and filters."""
    result = await service.get_all_vehicles(
        limit=limit,
        offset=offset,
        verified=verified
    )
    
    # If user_id filter is provided, filter the results
    vehicles_data = result["vehicles"]
    if user_id:
        vehicles_data = [v for v in vehicles_data if v.get("user_id") == str(user_id)]
    
    vehicles = []
    for v in vehicles_data:
        vehicles.append(AdminVehicle(
            id=UUID(v["id"]),
            user_id=UUID(v["user_id"]) if v.get("user_id") else None,
            make=v.get("make", ""),
            model=v.get("model", ""),
            year=v.get("year"),
            variant=v.get("variant"),
            verified=v.get("verified", False),
            created_at=datetime.fromisoformat(v["created_at"]) if isinstance(v["created_at"], str) else v["created_at"],
        ))
    
    return AdminVehiclesResponse(
        vehicles=vehicles,
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


# ─── SERVICES ────────────────────────────────────────────────────

@router.get("/services", response_model=AdminServicesResponse)
async def list_services(
    active: Optional[bool] = None,
    service: AdminService = Depends(get_admin_service),
):
    """List all services."""
    result = await service.get_all_services()
    
    services_data = result["services"]
    if active is not None:
        services_data = [s for s in services_data if s.get("active") == active]
    
    services = []
    for s in services_data:
        services.append(AdminService(
            id=UUID(s["id"]),
            code=ServiceCode(s["code"]),
            name=s["name"],
            price=s["price"],
            currency=s.get("currency", "KES"),
            description=s.get("description"),
            icon=s.get("icon"),
            active=s.get("active", True),
            display_order=s.get("display_order", 0),
            purchase_count=s.get("purchase_count", 0),
            created_at=datetime.fromisoformat(s["created_at"]) if isinstance(s["created_at"], str) else s["created_at"],
            updated_at=datetime.fromisoformat(s["updated_at"]) if isinstance(s["updated_at"], str) else s["updated_at"],
        ))
    
    return AdminServicesResponse(
        services=services,
        total=len(services),
    )


@router.post("/services", response_model=ServiceResponse)
async def create_service(
    request: CreateServiceRequest,
    service: AdminService = Depends(get_admin_service),
):
    """Create a new service."""
    try:
        result = await service.create_service(request.model_dump())
        
        s = result["service"]
        return ServiceResponse(
            success=True,
            message=result["message"],
            service=AdminService(
                id=UUID(s["id"]),
                code=ServiceCode(s["code"]),
                name=s["name"],
                price=s["price"],
                currency=s.get("currency", "KES"),
                description=s.get("description"),
                icon=s.get("icon"),
                active=s.get("active", True),
                display_order=s.get("display_order", 0),
                purchase_count=0,
                created_at=datetime.fromisoformat(s["created_at"]) if isinstance(s["created_at"], str) else s["created_at"],
                updated_at=datetime.fromisoformat(s["updated_at"]) if isinstance(s["updated_at"], str) else s["updated_at"],
            )
        )
    except Exception as e:
        logger.error(f"Error creating service: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/services/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: UUID,
    request: UpdateServiceRequest,
    service: AdminService = Depends(get_admin_service),
):
    """Update an existing service."""
    try:
        result = await service.update_service(str(service_id), request.model_dump(exclude_unset=True))
        
        s = result["service"]
        return ServiceResponse(
            success=True,
            message=result["message"],
            service=AdminService(
                id=UUID(s["id"]),
                code=ServiceCode(s["code"]),
                name=s["name"],
                price=s["price"],
                currency=s.get("currency", "KES"),
                description=s.get("description"),
                icon=s.get("icon"),
                active=s.get("active", True),
                display_order=s.get("display_order", 0),
                purchase_count=s.get("purchase_count", 0),
                created_at=datetime.fromisoformat(s["created_at"]) if isinstance(s["created_at"], str) else s["created_at"],
                updated_at=datetime.fromisoformat(s["updated_at"]) if isinstance(s["updated_at"], str) else s["updated_at"],
            )
        )
    except Exception as e:
        logger.error(f"Error updating service: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/services/{service_id}/price", response_model=ServiceResponse)
async def update_service_price(
    service_id: UUID,
    request: UpdateServicePriceRequest,
    service: AdminService = Depends(get_admin_service),
):
    """Update service price."""
    try:
        # Get service by ID first
        services = await service.get_all_services()
        target_service = None
        for s in services["services"]:
            if s["id"] == str(service_id):
                target_service = s
                break
        
        if not target_service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )
        
        result = await service.update_service_price(
            target_service["code"],
            request.price,
            request.currency
        )
        
        s = result["service"]
        return ServiceResponse(
            success=True,
            message=result["message"],
            service=AdminService(
                id=UUID(s["id"]),
                code=ServiceCode(s["code"]),
                name=s["name"],
                price=s["price"],
                currency=s.get("currency", "KES"),
                description=s.get("description"),
                icon=s.get("icon"),
                active=s.get("active", True),
                display_order=s.get("display_order", 0),
                purchase_count=s.get("purchase_count", 0),
                created_at=datetime.fromisoformat(s["created_at"]) if isinstance(s["created_at"], str) else s["created_at"],
                updated_at=datetime.fromisoformat(s["updated_at"]) if isinstance(s["updated_at"], str) else s["updated_at"],
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating service price: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/services/{service_id}", response_model=DeleteServiceResponse)
async def delete_service(
    service_id: UUID,
    service: AdminService = Depends(get_admin_service),
):
    """Delete a service."""
    try:
        result = await service.delete_service(str(service_id))
        return DeleteServiceResponse(
            success=True,
            message=result["message"],
            service_id=service_id,
            deleted_at=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Error deleting service: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/services/prices", response_model=ServicePricesResponse)
async def get_service_prices(
    service: AdminService = Depends(get_admin_service),
):
    """Get all service prices."""
    result = await service.get_service_prices()
    
    prices = {}
    for code, price_data in result["prices"].items():
        prices[ServiceCode(code)] = ServicePriceItem(
            price=price_data["price"],
            currency=price_data["currency"],
            name=price_data["name"],
        )
    
    services = []
    for s in result["services"]:
        services.append(AdminService(
            id=UUID(s["id"]),
            code=ServiceCode(s["code"]),
            name=s["name"],
            price=s["price"],
            currency=s.get("currency", "KES"),
            description=s.get("description"),
            icon=s.get("icon"),
            active=s.get("active", True),
            display_order=s.get("display_order", 0),
            purchase_count=s.get("purchase_count", 0),
            created_at=datetime.fromisoformat(s["created_at"]) if isinstance(s["created_at"], str) else s["created_at"],
            updated_at=datetime.fromisoformat(s["updated_at"]) if isinstance(s["updated_at"], str) else s["updated_at"],
        ))
    
    return ServicePricesResponse(
        prices=prices,
        services=services,
        total=result["total"],
    )


# ─── USER SERVICES ──────────────────────────────────────────────

@router.get("/users/{user_id}/services", response_model=UserServicesResponse)
async def get_user_services(
    user_id: UUID,
    service: AdminService = Depends(get_admin_service),
):
    """Get all services purchased by a user."""
    try:
        user = await service.get_user_by_id(str(user_id))
        
        services = []
        for s in user.get("services", []):
            service_data = s.get("services", {})
            services.append(UserServiceItem(
                id=UUID(s["id"]),
                user_id=UUID(s["user_id"]),
                service_id=UUID(s["service_id"]),
                status=UserServiceStatus(s.get("status", "active")),
                created_at=datetime.fromisoformat(s["created_at"]) if isinstance(s["created_at"], str) else s["created_at"],
                updated_at=datetime.fromisoformat(s["updated_at"]) if isinstance(s["updated_at"], str) else s["updated_at"],
                service=AdminService(
                    id=UUID(service_data["id"]),
                    code=ServiceCode(service_data["code"]),
                    name=service_data["name"],
                    price=service_data["price"],
                    currency=service_data.get("currency", "KES"),
                    description=service_data.get("description"),
                    icon=service_data.get("icon"),
                    active=service_data.get("active", True),
                    display_order=service_data.get("display_order", 0),
                    purchase_count=service_data.get("purchase_count", 0),
                    created_at=datetime.fromisoformat(service_data["created_at"]) if isinstance(service_data["created_at"], str) else service_data["created_at"],
                    updated_at=datetime.fromisoformat(service_data["updated_at"]) if isinstance(service_data["updated_at"], str) else service_data["updated_at"],
                )
            ))
        
        return UserServicesResponse(
            user_id=user_id,
            services=services,
            total=len(services),
        )
    except Exception as e:
        logger.error(f"Error getting user services: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


@router.patch("/users/{user_id}/services/{service_id}", response_model=UpdateUserServiceResponse)
async def update_user_service_status(
    user_id: UUID,
    service_id: UUID,
    request: UpdateUserServiceRequest,
    service: AdminService = Depends(get_admin_service),
):
    """Update a user's service status."""
    try:
        result = await service.update_user_service(
            str(user_id),
            str(service_id),
            request.status.value
        )
        
        return UpdateUserServiceResponse(
            success=True,
            message=result["message"],
            user_id=user_id,
            service_id=service_id,
            status=UserServiceStatus(result["status"]),
            updated_at=datetime.fromisoformat(result["updated_at"]) if isinstance(result["updated_at"], str) else result["updated_at"],
        )
    except Exception as e:
        logger.error(f"Error updating user service: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ─── ANALYTICS ──────────────────────────────────────────────────

@router.get("/analytics", response_model=AdminAnalyticsResponse)
async def get_analytics(
    days: int = Query(30, ge=1, le=365),
    service: AdminService = Depends(get_admin_service),
):
    """Get analytics data for the specified period."""
    result = await service.get_platform_analytics(days)
    
    daily_stats = []
    for stat in result.get("daily_stats", []):
        daily_stats.append(AnalyticsDay(
            date=datetime.fromisoformat(stat["date"]).date() if isinstance(stat["date"], str) else stat["date"],
            users=stat["users"],
            payments=stat["payments"],
            revenue=stat["revenue"],
            vehicles=stat["vehicles"],
        ))
    
    totals = result.get("totals", {})
    
    return AdminAnalyticsResponse(
        period_days=result["period_days"],
        start_date=datetime.fromisoformat(result["start_date"]).date() if isinstance(result["start_date"], str) else result["start_date"],
        end_date=datetime.fromisoformat(result["end_date"]).date() if isinstance(result["end_date"], str) else result["end_date"],
        daily_stats=daily_stats,
        totals=AnalyticsTotals(
            users=totals.get("users", 0),
            payments=totals.get("payments", 0),
            revenue=totals.get("revenue", 0),
            vehicles=totals.get("vehicles", 0),
        )
    )


@router.get("/analytics/revenue", response_model=RevenueReportResponse)
async def get_revenue_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    service: AdminService = Depends(get_admin_service),
):
    """Get revenue report."""
    result = await service.get_revenue_report(
        start_date=start_date.isoformat() if start_date else None,
        end_date=end_date.isoformat() if end_date else None,
    )
    
    if result.get("error"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )
    
    return RevenueReportResponse(
        total_revenue=result["total_revenue"],
        total_transactions=result["total_transactions"],
        revenue_by_service=result["revenue_by_service"],
        start_date=datetime.fromisoformat(result["start_date"]) if result.get("start_date") and isinstance(result["start_date"], str) else start_date,
        end_date=datetime.fromisoformat(result["end_date"]) if result.get("end_date") and isinstance(result["end_date"], str) else end_date,
    )
