# app/modules/admin/router.py
# Auto-D Kenya - Admin Router
# ================================================================
# TYPE: MODULE - Admin API endpoints

from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, asc

from app.core.database import get_db
from app.core.dependencies import get_current_admin_user
from app.core.logging import get_logger
from app.modules.admin.schemas import (
    AdminStatsResponse,
    AdminUser,
    AdminUserDetail,
    AdminUserDetailResponse,
    AdminUsersResponse,
    AdminPayment,
    AdminPaymentsResponse,
    AdminVehicle,
    AdminVehiclesResponse,
    AdminService,
    AdminServicesResponse,
    AdminAnalyticsResponse,
    AdminStatusResponse,
    RevenueReportResponse,
    ServicePricesResponse,
    UserServicesResponse,
    ServiceResponse,
    DeleteUserResponse,
    DeleteServiceResponse,
    UpdateUserServiceResponse,
    AdminHealthResponse,
    CreateServiceRequest,
    UpdateServiceRequest,
    UpdateServicePriceRequest,
    UpdateUserServiceRequest,
    ServiceCode,
    UserServiceStatus,
    PaymentStatus,
    ComponentStatus,
)
from app.modules.admin.services import AdminService as AdminServiceLogic
from app.modules.users.models import User
from app.modules.vehicles.models import Vehicle
from app.modules.payments.models import Payment
from app.modules.services.models import Service, UserService
from app.modules.admin.models import AdminLog

logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin_user)],
)


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
    db: AsyncSession = Depends(get_db),
):
    """Get system component status."""
    # Check database connectivity
    try:
        await db.execute(select(1))
        db_status = ComponentStatus.HEALTHY
    except Exception:
        db_status = ComponentStatus.UNHEALTHY

    # Check Supabase connectivity (if configured)
    # This is a placeholder - implement actual Supabase health check
    supabase_status = ComponentStatus.HEALTHY

    # Check M-Pesa connectivity (if configured)
    mpesa_status = ComponentStatus.HEALTHY

    # Overall status
    if db_status == ComponentStatus.UNHEALTHY:
        overall = ComponentStatus.UNHEALTHY
    elif supabase_status == ComponentStatus.UNHEALTHY or mpesa_status == ComponentStatus.UNHEALTHY:
        overall = ComponentStatus.DEGRADED
    else:
        overall = ComponentStatus.HEALTHY

    return AdminStatusResponse(
        status=overall,
        timestamp=datetime.utcnow(),
        components={
            "supabase": supabase_status,
            "database": db_status,
            "mpesa": mpesa_status,
        }
    )


# ─── STATISTICS ──────────────────────────────────────────────────

@router.get("/stats", response_model=AdminStatsResponse)
async def admin_stats(
    db: AsyncSession = Depends(get_db),
):
    """Get admin dashboard statistics."""
    # Total users
    total_users_result = await db.execute(select(func.count()).select_from(User))
    total_users = total_users_result.scalar() or 0

    # Total vehicles
    total_vehicles_result = await db.execute(select(func.count()).select_from(Vehicle))
    total_vehicles = total_vehicles_result.scalar() or 0

    # Total payments
    total_payments_result = await db.execute(select(func.count()).select_from(Payment))
    total_payments = total_payments_result.scalar() or 0

    # Total revenue (from completed payments)
    total_revenue_result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0))
        .where(Payment.status == PaymentStatus.COMPLETED)
    )
    total_revenue = total_revenue_result.scalar() or Decimal(0)

    # Total services purchased
    total_services_result = await db.execute(select(func.count()).select_from(UserService))
    total_services_purchased = total_services_result.scalar() or 0

    # New users this week
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users_result = await db.execute(
        select(func.count()).select_from(User)
        .where(User.created_at >= week_ago)
    )
    new_users_this_week = new_users_result.scalar() or 0

    # Active services
    active_services_result = await db.execute(
        select(func.count()).select_from(Service)
        .where(Service.active == True)
    )
    active_services = active_services_result.scalar() or 0

    return AdminStatsResponse(
        total_users=total_users,
        total_vehicles=total_vehicles,
        total_payments=total_payments,
        total_revenue=total_revenue,
        total_services_purchased=total_services_purchased,
        new_users_this_week=new_users_this_week,
        active_services=active_services,
        updated_at=datetime.utcnow()
    )


# ─── USERS ──────────────────────────────────────────────────────

@router.get("/users", response_model=AdminUsersResponse)
async def list_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, description="Search by email or name"),
    db: AsyncSession = Depends(get_db),
):
    """List all users with pagination."""
    query = select(User)

    if search:
        query = query.where(
            (User.email.ilike(f"%{search}%")) |
            (User.full_name.ilike(f"%{search}%"))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get users with pagination
    query = query.order_by(desc(User.created_at)).limit(limit).offset(offset)
    result = await db.execute(query)
    users = result.scalars().all()

    # Convert to schema
    user_list = []
    for user in users:
        # Get user services
        services_result = await db.execute(
            select(UserService, Service)
            .join(Service, UserService.service_id == Service.id)
            .where(UserService.user_id == user.id)
        )
        services_data = services_result.all()

        user_services = [
            {
                "service_id": service.id,
                "service_name": service.name,
                "service_code": service.code,
                "status": user_service.status,
            }
            for user_service, service in services_data
        ]

        user_list.append(AdminUser(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            created_at=user.created_at,
            last_sign_in_at=user.last_sign_in_at,
            confirmed_at=user.confirmed_at,
            phone=user.phone,
            services=user_services,
        ))

    return AdminUsersResponse(
        users=user_list,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/users/{user_id}", response_model=AdminUserDetailResponse)
async def get_user_detail(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed user information."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get user services
    services_result = await db.execute(
        select(UserService, Service)
        .join(Service, UserService.service_id == Service.id)
        .where(UserService.user_id == user.id)
    )
    services_data = services_result.all()

    user_services = [
        {
            "service_id": service.id,
            "service_name": service.name,
            "service_code": service.code,
            "status": user_service.status,
        }
        for user_service, service in services_data
    ]

    # Get user payments
    payments_result = await db.execute(
        select(Payment, Service)
        .outerjoin(Service, Payment.service_id == Service.id)
        .where(Payment.user_id == user.id)
        .order_by(desc(Payment.created_at))
    )
    payments_data = payments_result.all()

    user_payments = [
        AdminPayment(
            id=payment.id,
            user_id=payment.user_id,
            service_id=payment.service_id,
            service_name=service.name if service else None,
            service_code=service.code if service else None,
            amount=payment.amount,
            currency=payment.currency,
            status=payment.status,
            phone=payment.phone,
            checkout_request_id=payment.checkout_request_id,
            mpesa_receipt=payment.mpesa_receipt,
            created_at=payment.created_at,
            completed_at=payment.completed_at,
        )
        for payment, service in payments_data
    ]

    return AdminUserDetailResponse(
        success=True,
        data=AdminUserDetail(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            created_at=user.created_at,
            last_sign_in_at=user.last_sign_in_at,
            confirmed_at=user.confirmed_at,
            phone=user.phone,
            services=user_services,
            app_metadata=user.app_metadata or {},
            user_metadata=user.user_metadata or {},
            payments=user_payments,
        )
    )


@router.delete("/users/{user_id}", response_model=DeleteUserResponse)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    await db.delete(user)
    await db.commit()

    return DeleteUserResponse(
        success=True,
        message="User deleted successfully",
        user_id=user_id,
        deleted_at=datetime.utcnow()
    )


# ─── PAYMENTS ────────────────────────────────────────────────────

@router.get("/payments", response_model=AdminPaymentsResponse)
async def list_payments(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[PaymentStatus] = None,
    user_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all payments with pagination and filters."""
    query = select(Payment)

    if status:
        query = query.where(Payment.status == status)
    if user_id:
        query = query.where(Payment.user_id == user_id)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get payments with pagination
    query = query.order_by(desc(Payment.created_at)).limit(limit).offset(offset)
    result = await db.execute(query)
    payments = result.scalars().all()

    # Convert to schema with service info
    payment_list = []
    for payment in payments:
        # Get service info if exists
        service = None
        if payment.service_id:
            service_result = await db.execute(
                select(Service).where(Service.id == payment.service_id)
            )
            service = service_result.scalar_one_or_none()

        payment_list.append(AdminPayment(
            id=payment.id,
            user_id=payment.user_id,
            service_id=payment.service_id,
            service_name=service.name if service else None,
            service_code=service.code if service else None,
            amount=payment.amount,
            currency=payment.currency,
            status=payment.status,
            phone=payment.phone,
            checkout_request_id=payment.checkout_request_id,
            mpesa_receipt=payment.mpesa_receipt,
            created_at=payment.created_at,
            completed_at=payment.completed_at,
        ))

    return AdminPaymentsResponse(
        payments=payment_list,
        total=total,
        limit=limit,
        offset=offset,
    )


# ─── VEHICLES ────────────────────────────────────────────────────

@router.get("/vehicles", response_model=AdminVehiclesResponse)
async def list_vehicles(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    verified: Optional[bool] = None,
    user_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all vehicles with pagination and filters."""
    query = select(Vehicle)

    if verified is not None:
        query = query.where(Vehicle.verified == verified)
    if user_id:
        query = query.where(Vehicle.user_id == user_id)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get vehicles with pagination
    query = query.order_by(desc(Vehicle.created_at)).limit(limit).offset(offset)
    result = await db.execute(query)
    vehicles = result.scalars().all()

    vehicle_list = [
        AdminVehicle(
            id=vehicle.id,
            user_id=vehicle.user_id,
            make=vehicle.make,
            model=vehicle.model,
            year=vehicle.year,
            variant=vehicle.variant,
            verified=vehicle.verified,
            created_at=vehicle.created_at,
        )
        for vehicle in vehicles
    ]

    return AdminVehiclesResponse(
        vehicles=vehicle_list,
        total=total,
        limit=limit,
        offset=offset,
    )


# ─── SERVICES ────────────────────────────────────────────────────

@router.get("/services", response_model=AdminServicesResponse)
async def list_services(
    active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all services."""
    query = select(Service)

    if active is not None:
        query = query.where(Service.active == active)

    query = query.order_by(asc(Service.display_order), asc(Service.name))
    result = await db.execute(query)
    services = result.scalars().all()

    service_list = [
        AdminService(
            id=service.id,
            code=service.code,
            name=service.name,
            price=service.price,
            currency=service.currency,
            description=service.description,
            icon=service.icon,
            active=service.active,
            display_order=service.display_order,
            purchase_count=service.purchase_count or 0,
            created_at=service.created_at,
            updated_at=service.updated_at,
        )
        for service in services
    ]

    return AdminServicesResponse(
        services=service_list,
        total=len(service_list),
    )


@router.post("/services", response_model=ServiceResponse)
async def create_service(
    request: CreateServiceRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new service."""
    # Check if service code already exists
    existing = await db.execute(
        select(Service).where(Service.code == request.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Service with code '{request.code}' already exists"
        )

    service = Service(
        code=request.code,
        name=request.name,
        price=request.price,
        currency=request.currency,
        description=request.description,
        icon=request.icon,
        active=request.active,
        display_order=request.display_order,
    )

    db.add(service)
    await db.commit()
    await db.refresh(service)

    return ServiceResponse(
        success=True,
        message="Service created successfully",
        service=AdminService(
            id=service.id,
            code=service.code,
            name=service.name,
            price=service.price,
            currency=service.currency,
            description=service.description,
            icon=service.icon,
            active=service.active,
            display_order=service.display_order,
            purchase_count=0,
            created_at=service.created_at,
            updated_at=service.updated_at,
        )
    )


@router.put("/services/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: UUID,
    request: UpdateServiceRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing service."""
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service, field, value)

    service.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(service)

    return ServiceResponse(
        success=True,
        message="Service updated successfully",
        service=AdminService(
            id=service.id,
            code=service.code,
            name=service.name,
            price=service.price,
            currency=service.currency,
            description=service.description,
            icon=service.icon,
            active=service.active,
            display_order=service.display_order,
            purchase_count=service.purchase_count or 0,
            created_at=service.created_at,
            updated_at=service.updated_at,
        )
    )


@router.patch("/services/{service_id}/price", response_model=ServiceResponse)
async def update_service_price(
    service_id: UUID,
    request: UpdateServicePriceRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update service price."""
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )

    service.price = request.price
    service.currency = request.currency
    service.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(service)

    return ServiceResponse(
        success=True,
        message="Service price updated successfully",
        service=AdminService(
            id=service.id,
            code=service.code,
            name=service.name,
            price=service.price,
            currency=service.currency,
            description=service.description,
            icon=service.icon,
            active=service.active,
            display_order=service.display_order,
            purchase_count=service.purchase_count or 0,
            created_at=service.created_at,
            updated_at=service.updated_at,
        )
    )


@router.delete("/services/{service_id}", response_model=DeleteServiceResponse)
async def delete_service(
    service_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a service."""
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )

    await db.delete(service)
    await db.commit()

    return DeleteServiceResponse(
        success=True,
        message="Service deleted successfully",
        service_id=service_id,
        deleted_at=datetime.utcnow()
    )


@router.get("/services/prices", response_model=ServicePricesResponse)
async def get_service_prices(
    db: AsyncSession = Depends(get_db),
):
    """Get all service prices."""
    result = await db.execute(
        select(Service).where(Service.active == True)
        .order_by(asc(Service.display_order))
    )
    services = result.scalars().all()

    prices = {}
    service_list = []

    for service in services:
        prices[service.code] = {
            "price": service.price,
            "currency": service.currency,
            "name": service.name,
        }
        service_list.append(AdminService(
            id=service.id,
            code=service.code,
            name=service.name,
            price=service.price,
            currency=service.currency,
            description=service.description,
            icon=service.icon,
            active=service.active,
            display_order=service.display_order,
            purchase_count=service.purchase_count or 0,
            created_at=service.created_at,
            updated_at=service.updated_at,
        ))

    return ServicePricesResponse(
        prices=prices,
        services=service_list,
        total=len(service_list),
    )


# ─── USER SERVICES ──────────────────────────────────────────────

@router.get("/users/{user_id}/services", response_model=UserServicesResponse)
async def get_user_services(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all services purchased by a user."""
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    if not user_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    result = await db.execute(
        select(UserService, Service)
        .join(Service, UserService.service_id == Service.id)
        .where(UserService.user_id == user_id)
        .order_by(desc(UserService.created_at))
    )
    user_services = result.all()

    service_list = []
    for user_service, service in user_services:
        service_list.append({
            "id": user_service.id,
            "user_id": user_service.user_id,
            "service_id": user_service.service_id,
            "status": user_service.status,
            "created_at": user_service.created_at,
            "updated_at": user_service.updated_at,
            "service": AdminService(
                id=service.id,
                code=service.code,
                name=service.name,
                price=service.price,
                currency=service.currency,
                description=service.description,
                icon=service.icon,
                active=service.active,
                display_order=service.display_order,
                purchase_count=service.purchase_count or 0,
                created_at=service.created_at,
                updated_at=service.updated_at,
            )
        })

    return UserServicesResponse(
        user_id=user_id,
        services=service_list,
        total=len(service_list),
    )


@router.patch("/users/{user_id}/services/{service_id}", response_model=UpdateUserServiceResponse)
async def update_user_service_status(
    user_id: UUID,
    service_id: UUID,
    request: UpdateUserServiceRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a user's service status."""
    result = await db.execute(
        select(UserService)
        .where(
            UserService.user_id == user_id,
            UserService.service_id == service_id
        )
    )
    user_service = result.scalar_one_or_none()

    if not user_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User service not found"
        )

    user_service.status = request.status
    user_service.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(user_service)

    return UpdateUserServiceResponse(
        success=True,
        message="User service status updated successfully",
        user_id=user_id,
        service_id=service_id,
        status=user_service.status,
        updated_at=user_service.updated_at,
    )


# ─── ANALYTICS ──────────────────────────────────────────────────

@router.get("/analytics", response_model=AdminAnalyticsResponse)
async def get_analytics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Get analytics data for the specified period."""
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days - 1)

    # Generate daily stats
    daily_stats = []
    current_date = start_date
    total_users = 0
    total_payments = 0
    total_revenue = Decimal(0)
    total_vehicles = 0

    while current_date <= end_date:
        next_date = current_date + timedelta(days=1)
        date_start = datetime.combine(current_date, datetime.min.time())
        date_end = datetime.combine(next_date, datetime.min.time())

        # New users on this day
        users_count_result = await db.execute(
            select(func.count())
            .select_from(User)
            .where(
                User.created_at >= date_start,
                User.created_at < date_end
            )
        )
        users_count = users_count_result.scalar() or 0

        # Payments on this day
        payments_count_result = await db.execute(
            select(func.count())
            .select_from(Payment)
            .where(
                Payment.created_at >= date_start,
                Payment.created_at < date_end,
                Payment.status == PaymentStatus.COMPLETED
            )
        )
        payments_count = payments_count_result.scalar() or 0

        # Revenue on this day
        revenue_result = await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .select_from(Payment)
            .where(
                Payment.created_at >= date_start,
                Payment.created_at < date_end,
                Payment.status == PaymentStatus.COMPLETED
            )
        )
        revenue = revenue_result.scalar() or Decimal(0)

        # Vehicles added on this day
        vehicles_count_result = await db.execute(
            select(func.count())
            .select_from(Vehicle)
            .where(
                Vehicle.created_at >= date_start,
                Vehicle.created_at < date_end
            )
        )
        vehicles_count = vehicles_count_result.scalar() or 0

        daily_stats.append({
            "date": current_date,
            "users": users_count,
            "payments": payments_count,
            "revenue": revenue,
            "vehicles": vehicles_count,
        })

        # Accumulate totals
        total_users += users_count
        total_payments += payments_count
        total_revenue += revenue
        total_vehicles += vehicles_count

        current_date = next_date

    return AdminAnalyticsResponse(
        period_days=days,
        start_date=start_date,
        end_date=end_date,
        daily_stats=daily_stats,
        totals={
            "users": total_users,
            "payments": total_payments,
            "revenue": total_revenue,
            "vehicles": total_vehicles,
        }
    )


@router.get("/analytics/revenue", response_model=RevenueReportResponse)
async def get_revenue_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get revenue report."""
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()

    query = select(Payment).where(
        Payment.status == PaymentStatus.COMPLETED,
        Payment.created_at >= start_date,
        Payment.created_at <= end_date
    )

    result = await db.execute(query)
    payments = result.scalars().all()

    total_revenue = Decimal(0)
    revenue_by_service = {}

    for payment in payments:
        total_revenue += payment.amount

        # Get service name
        if payment.service_id:
            service_result = await db.execute(
                select(Service).where(Service.id == payment.service_id)
            )
            service = service_result.scalar_one_or_none()
            service_name = service.name if service else "Unknown"
        else:
            service_name = "Unknown"

        if service_name in revenue_by_service:
            revenue_by_service[service_name] += payment.amount
        else:
            revenue_by_service[service_name] = payment.amount

    return RevenueReportResponse(
        total_revenue=total_revenue,
        total_transactions=len(payments),
        revenue_by_service=revenue_by_service,
        start_date=start_date,
        end_date=end_date,
    )
