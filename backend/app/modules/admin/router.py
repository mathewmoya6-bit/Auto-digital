# app/modules/admin/router.py
# Auto-D Kenya - Admin Router
# ================================================================
# TYPE: MODULE - Admin API endpoints (Supabase-based)

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from decimal import Decimal
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_admin_user
from app.core.logging import get_logger
from app.core.supabase import get_supabase_client
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

logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin_user)],
)


# ─── HELPER FUNCTIONS ────────────────────────────────────────────

def get_supabase():
    """Get Supabase client."""
    return get_supabase_client()


def parse_uuid(value: str) -> UUID:
    """Parse UUID from string."""
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format"
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
async def system_status():
    """Get system component status."""
    supabase = get_supabase()
    
    # Check Supabase connectivity
    try:
        # Try to ping the database
        supabase.table("users").select("count", count="exact").limit(0).execute()
        db_status = ComponentStatus.HEALTHY
        supabase_status = ComponentStatus.HEALTHY
    except Exception as e:
        logger.error(f"Supabase connection error: {e}")
        db_status = ComponentStatus.UNHEALTHY
        supabase_status = ComponentStatus.UNHEALTHY

    # Check M-Pesa connectivity (placeholder)
    mpesa_status = ComponentStatus.HEALTHY

    # Overall status
    if db_status == ComponentStatus.UNHEALTHY or supabase_status == ComponentStatus.UNHEALTHY:
        overall = ComponentStatus.UNHEALTHY
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
async def admin_stats():
    """Get admin dashboard statistics."""
    supabase = get_supabase()
    
    try:
        # Total users
        users_result = supabase.table("users").select("count", count="exact").limit(0).execute()
        total_users = users_result.count or 0

        # Total vehicles
        vehicles_result = supabase.table("vehicles").select("count", count="exact").limit(0).execute()
        total_vehicles = vehicles_result.count or 0

        # Total payments
        payments_result = supabase.table("payments").select("count", count="exact").limit(0).execute()
        total_payments = payments_result.count or 0

        # Total revenue (from completed payments)
        revenue_result = supabase.table("payments") \
            .select("amount") \
            .eq("status", "completed") \
            .execute()
        
        total_revenue = Decimal(0)
        if revenue_result.data:
            for payment in revenue_result.data:
                total_revenue += Decimal(str(payment.get("amount", 0)))

        # Total services purchased
        services_result = supabase.table("user_services").select("count", count="exact").limit(0).execute()
        total_services_purchased = services_result.count or 0

        # New users this week
        week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        new_users_result = supabase.table("users") \
            .select("count", count="exact") \
            .gte("created_at", week_ago) \
            .limit(0) \
            .execute()
        new_users_this_week = new_users_result.count or 0

        # Active services
        active_services_result = supabase.table("services") \
            .select("count", count="exact") \
            .eq("active", True) \
            .limit(0) \
            .execute()
        active_services = active_services_result.count or 0

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
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch statistics"
        )


# ─── USERS ──────────────────────────────────────────────────────

@router.get("/users", response_model=AdminUsersResponse)
async def list_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, description="Search by email or name"),
):
    """List all users with pagination."""
    supabase = get_supabase()
    
    try:
        # Build query
        query = supabase.table("users").select("*", count="exact")
        
        if search:
            query = query.or_(f"email.ilike.%{search}%,full_name.ilike.%{search}%")
        
        # Get total count
        count_result = query.limit(0).execute()
        total = count_result.count or 0
        
        # Get users with pagination
        result = query.order("created_at", desc=True).limit(limit).offset(offset).execute()
        users_data = result.data or []

        # Convert to schema
        user_list = []
        for user_data in users_data:
            # Get user services
            services_result = supabase.table("user_services") \
                .select("*, services(*)") \
                .eq("user_id", user_data["id"]) \
                .execute()
            
            user_services = []
            if services_result.data:
                for us in services_result.data:
                    service = us.get("services", {})
                    user_services.append({
                        "service_id": service.get("id"),
                        "service_name": service.get("name"),
                        "service_code": service.get("code"),
                        "status": us.get("status"),
                    })

            user_list.append(AdminUser(
                id=parse_uuid(user_data["id"]),
                email=user_data.get("email", ""),
                full_name=user_data.get("full_name", ""),
                created_at=datetime.fromisoformat(user_data["created_at"]) if user_data.get("created_at") else datetime.utcnow(),
                last_sign_in_at=datetime.fromisoformat(user_data["last_sign_in_at"]) if user_data.get("last_sign_in_at") else None,
                confirmed_at=datetime.fromisoformat(user_data["confirmed_at"]) if user_data.get("confirmed_at") else None,
                phone=user_data.get("phone"),
                services=user_services,
            ))

        return AdminUsersResponse(
            users=user_list,
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch users"
        )


@router.get("/users/{user_id}", response_model=AdminUserDetailResponse)
async def get_user_detail(
    user_id: UUID,
):
    """Get detailed user information."""
    supabase = get_supabase()
    
    try:
        # Get user
        user_result = supabase.table("users").select("*").eq("id", str(user_id)).execute()
        if not user_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_data = user_result.data[0]

        # Get user services
        services_result = supabase.table("user_services") \
            .select("*, services(*)") \
            .eq("user_id", str(user_id)) \
            .execute()
        
        user_services = []
        if services_result.data:
            for us in services_result.data:
                service = us.get("services", {})
                user_services.append({
                    "service_id": service.get("id"),
                    "service_name": service.get("name"),
                    "service_code": service.get("code"),
                    "status": us.get("status"),
                })

        # Get user payments
        payments_result = supabase.table("payments") \
            .select("*, services(*)") \
            .eq("user_id", str(user_id)) \
            .order("created_at", desc=True) \
            .execute()
        
        user_payments = []
        if payments_result.data:
            for payment in payments_result.data:
                service = payment.get("services", {})
                user_payments.append(AdminPayment(
                    id=parse_uuid(payment["id"]),
                    user_id=parse_uuid(payment["user_id"]) if payment.get("user_id") else None,
                    service_id=parse_uuid(payment["service_id"]) if payment.get("service_id") else None,
                    service_name=service.get("name") if service else None,
                    service_code=service.get("code") if service else None,
                    amount=Decimal(str(payment.get("amount", 0))),
                    currency=payment.get("currency", "KES"),
                    status=PaymentStatus(payment.get("status", "pending")),
                    phone=payment.get("phone"),
                    checkout_request_id=payment.get("checkout_request_id"),
                    mpesa_receipt=payment.get("mpesa_receipt"),
                    created_at=datetime.fromisoformat(payment["created_at"]) if payment.get("created_at") else datetime.utcnow(),
                    completed_at=datetime.fromisoformat(payment["completed_at"]) if payment.get("completed_at") else None,
                ))

        return AdminUserDetailResponse(
            success=True,
            data=AdminUserDetail(
                id=parse_uuid(user_data["id"]),
                email=user_data.get("email", ""),
                full_name=user_data.get("full_name", ""),
                created_at=datetime.fromisoformat(user_data["created_at"]) if user_data.get("created_at") else datetime.utcnow(),
                last_sign_in_at=datetime.fromisoformat(user_data["last_sign_in_at"]) if user_data.get("last_sign_in_at") else None,
                confirmed_at=datetime.fromisoformat(user_data["confirmed_at"]) if user_data.get("confirmed_at") else None,
                phone=user_data.get("phone"),
                services=user_services,
                app_metadata=user_data.get("app_metadata", {}),
                user_metadata=user_data.get("user_metadata", {}),
                payments=user_payments,
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user details"
        )


@router.delete("/users/{user_id}", response_model=DeleteUserResponse)
async def delete_user(
    user_id: UUID,
):
    """Delete a user (admin only)."""
    supabase = get_supabase()
    
    try:
        # Check if user exists
        user_result = supabase.table("users").select("id").eq("id", str(user_id)).execute()
        if not user_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Delete user (Supabase will cascade delete related records if set up)
        supabase.table("users").delete().eq("id", str(user_id)).execute()

        return DeleteUserResponse(
            success=True,
            message="User deleted successfully",
            user_id=user_id,
            deleted_at=datetime.utcnow()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


# ─── PAYMENTS ────────────────────────────────────────────────────

@router.get("/payments", response_model=AdminPaymentsResponse)
async def list_payments(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[PaymentStatus] = None,
    user_id: Optional[UUID] = None,
):
    """List all payments with pagination and filters."""
    supabase = get_supabase()
    
    try:
        # Build query
        query = supabase.table("payments").select("*, services(*)", count="exact")
        
        if status:
            query = query.eq("status", status.value)
        if user_id:
            query = query.eq("user_id", str(user_id))
        
        # Get total count
        count_result = query.limit(0).execute()
        total = count_result.count or 0
        
        # Get payments with pagination
        result = query.order("created_at", desc=True).limit(limit).offset(offset).execute()
        payments_data = result.data or []

        # Convert to schema
        payment_list = []
        for payment in payments_data:
            service = payment.get("services", {})
            payment_list.append(AdminPayment(
                id=parse_uuid(payment["id"]),
                user_id=parse_uuid(payment["user_id"]) if payment.get("user_id") else None,
                service_id=parse_uuid(payment["service_id"]) if payment.get("service_id") else None,
                service_name=service.get("name") if service else None,
                service_code=service.get("code") if service else None,
                amount=Decimal(str(payment.get("amount", 0))),
                currency=payment.get("currency", "KES"),
                status=PaymentStatus(payment.get("status", "pending")),
                phone=payment.get("phone"),
                checkout_request_id=payment.get("checkout_request_id"),
                mpesa_receipt=payment.get("mpesa_receipt"),
                created_at=datetime.fromisoformat(payment["created_at"]) if payment.get("created_at") else datetime.utcnow(),
                completed_at=datetime.fromisoformat(payment["completed_at"]) if payment.get("completed_at") else None,
            ))

        return AdminPaymentsResponse(
            payments=payment_list,
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Error listing payments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch payments"
        )


# ─── VEHICLES ────────────────────────────────────────────────────

@router.get("/vehicles", response_model=AdminVehiclesResponse)
async def list_vehicles(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    verified: Optional[bool] = None,
    user_id: Optional[UUID] = None,
):
    """List all vehicles with pagination and filters."""
    supabase = get_supabase()
    
    try:
        # Build query
        query = supabase.table("vehicles").select("*", count="exact")
        
        if verified is not None:
            query = query.eq("verified", verified)
        if user_id:
            query = query.eq("user_id", str(user_id))
        
        # Get total count
        count_result = query.limit(0).execute()
        total = count_result.count or 0
        
        # Get vehicles with pagination
        result = query.order("created_at", desc=True).limit(limit).offset(offset).execute()
        vehicles_data = result.data or []

        # Convert to schema
        vehicle_list = [
            AdminVehicle(
                id=parse_uuid(vehicle["id"]),
                user_id=parse_uuid(vehicle["user_id"]) if vehicle.get("user_id") else None,
                make=vehicle.get("make", ""),
                model=vehicle.get("model", ""),
                year=vehicle.get("year"),
                variant=vehicle.get("variant"),
                verified=vehicle.get("verified", False),
                created_at=datetime.fromisoformat(vehicle["created_at"]) if vehicle.get("created_at") else datetime.utcnow(),
            )
            for vehicle in vehicles_data
        ]

        return AdminVehiclesResponse(
            vehicles=vehicle_list,
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Error listing vehicles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch vehicles"
        )


# ─── SERVICES ────────────────────────────────────────────────────

@router.get("/services", response_model=AdminServicesResponse)
async def list_services(
    active: Optional[bool] = None,
):
    """List all services."""
    supabase = get_supabase()
    
    try:
        query = supabase.table("services").select("*")
        
        if active is not None:
            query = query.eq("active", active)
        
        result = query.order("display_order", desc=False).order("name", desc=False).execute()
        services_data = result.data or []

        service_list = [
            AdminService(
                id=parse_uuid(service["id"]),
                code=ServiceCode(service["code"]),
                name=service["name"],
                price=Decimal(str(service.get("price", 0))),
                currency=service.get("currency", "KES"),
                description=service.get("description"),
                icon=service.get("icon"),
                active=service.get("active", True),
                display_order=service.get("display_order", 0),
                purchase_count=service.get("purchase_count", 0),
                created_at=datetime.fromisoformat(service["created_at"]) if service.get("created_at") else datetime.utcnow(),
                updated_at=datetime.fromisoformat(service["updated_at"]) if service.get("updated_at") else datetime.utcnow(),
            )
            for service in services_data
        ]

        return AdminServicesResponse(
            services=service_list,
            total=len(service_list),
        )
    except Exception as e:
        logger.error(f"Error listing services: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch services"
        )


@router.post("/services", response_model=ServiceResponse)
async def create_service(
    request: CreateServiceRequest,
):
    """Create a new service."""
    supabase = get_supabase()
    
    try:
        # Check if service code already exists
        existing = supabase.table("services").select("id").eq("code", request.code.value).execute()
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Service with code '{request.code.value}' already exists"
            )

        # Create service
        service_data = {
            "id": str(uuid4()),
            "code": request.code.value,
            "name": request.name,
            "price": float(request.price),
            "currency": request.currency,
            "description": request.description,
            "icon": request.icon,
            "active": request.active,
            "display_order": request.display_order,
            "purchase_count": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        result = supabase.table("services").insert(service_data).execute()
        service = result.data[0] if result.data else None

        if not service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create service"
            )

        return ServiceResponse(
            success=True,
            message="Service created successfully",
            service=AdminService(
                id=parse_uuid(service["id"]),
                code=ServiceCode(service["code"]),
                name=service["name"],
                price=Decimal(str(service.get("price", 0))),
                currency=service.get("currency", "KES"),
                description=service.get("description"),
                icon=service.get("icon"),
                active=service.get("active", True),
                display_order=service.get("display_order", 0),
                purchase_count=service.get("purchase_count", 0),
                created_at=datetime.fromisoformat(service["created_at"]),
                updated_at=datetime.fromisoformat(service["updated_at"]),
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create service"
        )


@router.put("/services/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: UUID,
    request: UpdateServiceRequest,
):
    """Update an existing service."""
    supabase = get_supabase()
    
    try:
        # Check if service exists
        existing = supabase.table("services").select("id").eq("id", str(service_id)).execute()
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )

        # Build update data
        update_data = request.model_dump(exclude_unset=True)
        if "price" in update_data:
            update_data["price"] = float(update_data["price"])
        if "code" in update_data:
            update_data["code"] = update_data["code"].value
        update_data["updated_at"] = datetime.utcnow().isoformat()

        result = supabase.table("services").update(update_data).eq("id", str(service_id)).execute()
        service = result.data[0] if result.data else None

        if not service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update service"
            )

        return ServiceResponse(
            success=True,
            message="Service updated successfully",
            service=AdminService(
                id=parse_uuid(service["id"]),
                code=ServiceCode(service["code"]),
                name=service["name"],
                price=Decimal(str(service.get("price", 0))),
                currency=service.get("currency", "KES"),
                description=service.get("description"),
                icon=service.get("icon"),
                active=service.get("active", True),
                display_order=service.get("display_order", 0),
                purchase_count=service.get("purchase_count", 0),
                created_at=datetime.fromisoformat(service["created_at"]),
                updated_at=datetime.fromisoformat(service["updated_at"]),
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update service"
        )


@router.patch("/services/{service_id}/price", response_model=ServiceResponse)
async def update_service_price(
    service_id: UUID,
    request: UpdateServicePriceRequest,
):
    """Update service price."""
    supabase = get_supabase()
    
    try:
        # Check if service exists
        existing = supabase.table("services").select("id").eq("id", str(service_id)).execute()
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )

        # Update price
        update_data = {
            "price": float(request.price),
            "currency": request.currency,
            "updated_at": datetime.utcnow().isoformat(),
        }

        result = supabase.table("services").update(update_data).eq("id", str(service_id)).execute()
        service = result.data[0] if result.data else None

        if not service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update service price"
            )

        return ServiceResponse(
            success=True,
            message="Service price updated successfully",
            service=AdminService(
                id=parse_uuid(service["id"]),
                code=ServiceCode(service["code"]),
                name=service["name"],
                price=Decimal(str(service.get("price", 0))),
                currency=service.get("currency", "KES"),
                description=service.get("description"),
                icon=service.get("icon"),
                active=service.get("active", True),
                display_order=service.get("display_order", 0),
                purchase_count=service.get("purchase_count", 0),
                created_at=datetime.fromisoformat(service["created_at"]),
                updated_at=datetime.fromisoformat(service["updated_at"]),
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating service price: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update service price"
        )


@router.delete("/services/{service_id}", response_model=DeleteServiceResponse)
async def delete_service(
    service_id: UUID,
):
    """Delete a service."""
    supabase = get_supabase()
    
    try:
        # Check if service exists
        existing = supabase.table("services").select("id").eq("id", str(service_id)).execute()
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )

        # Delete service
        supabase.table("services").delete().eq("id", str(service_id)).execute()

        return DeleteServiceResponse(
            success=True,
            message="Service deleted successfully",
            service_id=service_id,
            deleted_at=datetime.utcnow()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete service"
        )


@router.get("/services/prices", response_model=ServicePricesResponse)
async def get_service_prices():
    """Get all service prices."""
    supabase = get_supabase()
    
    try:
        result = supabase.table("services") \
            .select("*") \
            .eq("active", True) \
            .order("display_order", desc=False) \
            .execute()
        services_data = result.data or []

        prices = {}
        service_list = []

        for service in services_data:
            service_code = ServiceCode(service["code"])
            prices[service_code] = {
                "price": Decimal(str(service.get("price", 0))),
                "currency": service.get("currency", "KES"),
                "name": service["name"],
            }
            service_list.append(AdminService(
                id=parse_uuid(service["id"]),
                code=service_code,
                name=service["name"],
                price=Decimal(str(service.get("price", 0))),
                currency=service.get("currency", "KES"),
                description=service.get("description"),
                icon=service.get("icon"),
                active=service.get("active", True),
                display_order=service.get("display_order", 0),
                purchase_count=service.get("purchase_count", 0),
                created_at=datetime.fromisoformat(service["created_at"]) if service.get("created_at") else datetime.utcnow(),
                updated_at=datetime.fromisoformat(service["updated_at"]) if service.get("updated_at") else datetime.utcnow(),
            ))

        return ServicePricesResponse(
            prices=prices,
            services=service_list,
            total=len(service_list),
        )
    except Exception as e:
        logger.error(f"Error fetching service prices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch service prices"
        )


# ─── USER SERVICES ──────────────────────────────────────────────

@router.get("/users/{user_id}/services", response_model=UserServicesResponse)
async def get_user_services(
    user_id: UUID,
):
    """Get all services purchased by a user."""
    supabase = get_supabase()
    
    try:
        # Check if user exists
        user_result = supabase.table("users").select("id").eq("id", str(user_id)).execute()
        if not user_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        result = supabase.table("user_services") \
            .select("*, services(*)") \
            .eq("user_id", str(user_id)) \
            .order("created_at", desc=True) \
            .execute()
        
        user_services_data = result.data or []

        service_list = []
        for us in user_services_data:
            service = us.get("services", {})
            if service:
                service_list.append({
                    "id": parse_uuid(us["id"]),
                    "user_id": parse_uuid(us["user_id"]),
                    "service_id": parse_uuid(us["service_id"]),
                    "status": UserServiceStatus(us.get("status", "active")),
                    "created_at": datetime.fromisoformat(us["created_at"]) if us.get("created_at") else datetime.utcnow(),
                    "updated_at": datetime.fromisoformat(us["updated_at"]) if us.get("updated_at") else datetime.utcnow(),
                    "service": AdminService(
                        id=parse_uuid(service["id"]),
                        code=ServiceCode(service["code"]),
                        name=service["name"],
                        price=Decimal(str(service.get("price", 0))),
                        currency=service.get("currency", "KES"),
                        description=service.get("description"),
                        icon=service.get("icon"),
                        active=service.get("active", True),
                        display_order=service.get("display_order", 0),
                        purchase_count=service.get("purchase_count", 0),
                        created_at=datetime.fromisoformat(service["created_at"]) if service.get("created_at") else datetime.utcnow(),
                        updated_at=datetime.fromisoformat(service["updated_at"]) if service.get("updated_at") else datetime.utcnow(),
                    )
                })

        return UserServicesResponse(
            user_id=user_id,
            services=service_list,
            total=len(service_list),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user services: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user services"
        )


@router.patch("/users/{user_id}/services/{service_id}", response_model=UpdateUserServiceResponse)
async def update_user_service_status(
    user_id: UUID,
    service_id: UUID,
    request: UpdateUserServiceRequest,
):
    """Update a user's service status."""
    supabase = get_supabase()
    
    try:
        # Check if user service exists
        existing = supabase.table("user_services") \
            .select("id") \
            .eq("user_id", str(user_id)) \
            .eq("service_id", str(service_id)) \
            .execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User service not found"
            )

        # Update status
        update_data = {
            "status": request.status.value,
            "updated_at": datetime.utcnow().isoformat(),
        }

        result = supabase.table("user_services") \
            .update(update_data) \
            .eq("user_id", str(user_id)) \
            .eq("service_id", str(service_id)) \
            .execute()
        
        user_service = result.data[0] if result.data else None

        if not user_service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user service"
            )

        return UpdateUserServiceResponse(
            success=True,
            message="User service status updated successfully",
            user_id=user_id,
            service_id=service_id,
            status=UserServiceStatus(user_service["status"]),
            updated_at=datetime.fromisoformat(user_service["updated_at"]) if user_service.get("updated_at") else datetime.utcnow(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user service"
        )


# ─── ANALYTICS ──────────────────────────────────────────────────

@router.get("/analytics", response_model=AdminAnalyticsResponse)
async def get_analytics(
    days: int = Query(30, ge=1, le=365),
):
    """Get analytics data for the specified period."""
    supabase = get_supabase()
    
    try:
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
            date_start = datetime.combine(current_date, datetime.min.time()).isoformat()
            date_end = datetime.combine(next_date, datetime.min.time()).isoformat()

            # New users on this day
            users_result = supabase.table("users") \
                .select("count", count="exact") \
                .gte("created_at", date_start) \
                .lt("created_at", date_end) \
                .limit(0) \
                .execute()
            users_count = users_result.count or 0

            # Payments on this day
            payments_result = supabase.table("payments") \
                .select("count", count="exact") \
                .gte("created_at", date_start) \
                .lt("created_at", date_end) \
                .eq("status", "completed") \
                .limit(0) \
                .execute()
            payments_count = payments_result.count or 0

            # Revenue on this day
            revenue_result = supabase.table("payments") \
                .select("amount") \
                .gte("created_at", date_start) \
                .lt("created_at", date_end) \
                .eq("status", "completed") \
                .execute()
            
            revenue = Decimal(0)
            if revenue_result.data:
                for payment in revenue_result.data:
                    revenue += Decimal(str(payment.get("amount", 0)))

            # Vehicles added on this day
            vehicles_result = supabase.table("vehicles") \
                .select("count", count="exact") \
                .gte("created_at", date_start) \
                .lt("created_at", date_end) \
                .limit(0) \
                .execute()
            vehicles_count = vehicles_result.count or 0

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
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch analytics"
        )


@router.get("/analytics/revenue", response_model=RevenueReportResponse)
async def get_revenue_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """Get revenue report."""
    supabase = get_supabase()
    
    try:
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Get payments in date range
        result = supabase.table("payments") \
            .select("*, services(*)") \
            .eq("status", "completed") \
            .gte("created_at", start_date.isoformat()) \
            .lte("created_at", end_date.isoformat()) \
            .execute()
        
        payments_data = result.data or []

        total_revenue = Decimal(0)
        revenue_by_service = {}

        for payment in payments_data:
            amount = Decimal(str(payment.get("amount", 0)))
            total_revenue += amount

            # Get service name
            service = payment.get("services", {})
            service_name = service.get("name", "Unknown") if service else "Unknown"

            if service_name in revenue_by_service:
                revenue_by_service[service_name] += amount
            else:
                revenue_by_service[service_name] = amount

        return RevenueReportResponse(
            total_revenue=total_revenue,
            total_transactions=len(payments_data),
            revenue_by_service=revenue_by_service,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as e:
        logger.error(f"Error fetching revenue report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch revenue report"
        )
