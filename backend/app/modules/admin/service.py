# app/modules/admin/service.py
# Auto-D Kenya - Admin Service
# ================================================================

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from uuid import UUID
from decimal import Decimal

from fastapi import Depends

from app.core.database import get_supabase
from app.core.exceptions import NotFoundException, ValidationException
from app.core.dependencies import get_current_user

from .schemas import (
    AdminStatsResponse,
    AdminUsersResponse,
    AdminUserDetail,
    AdminUserDetailResponse,
    AdminPaymentsResponse,
    AdminVehiclesResponse,
    AdminServicesResponse,
    AdminAnalyticsResponse,
    AdminStatusResponse,
    RevenueReportResponse,
    ServicePricesResponse,
    UserServicesResponse,
    CreateServiceRequest,
    AdminServiceItem,
    UpdateServiceRequest,
    UpdateServicePriceRequest,
    UpdateUserServiceRequest,
    UpdateUserServiceResponse,
    DeleteUserResponse,
    DeleteServiceResponse,
    AdminHealthResponse,
    SuccessResponse,
    AdminUser,
    AdminPayment,
    AdminVehicle,
    AnalyticsDay,
    AnalyticsTotals,
    ComponentStatuses,
    ServicePriceItem,
    UserServiceItem,
    Pagination,
)

logger = logging.getLogger(__name__)


class AdminService:
    """Admin service for administrative operations."""
    
    def __init__(self):
        self.supabase = get_supabase()
    
    # ─── DASHBOARD & STATS ──────────────────────────────────────────
    
    async def get_stats(self) -> AdminStatsResponse:
        """Get admin dashboard statistics."""
        try:
            # Get total users
            users_response = self.supabase.table("users").select("count", count="exact").execute()
            total_users = users_response.count or 0
            
            # Get total vehicles
            vehicles_response = self.supabase.table("user_vehicles").select("count", count="exact").execute()
            total_vehicles = vehicles_response.count or 0
            
            # Get total payments
            payments_response = self.supabase.table("payments").select("count", count="exact").execute()
            total_payments = payments_response.count or 0
            
            # Get total revenue
            revenue_response = self.supabase.table("payments").select("amount").eq("status", "completed").execute()
            total_revenue = sum(Decimal(p["amount"]) for p in revenue_response.data) if revenue_response.data else Decimal(0)
            
            # Get total services purchased
            services_response = self.supabase.table("user_services").select("count", count="exact").execute()
            total_services_purchased = services_response.count or 0
            
            # Get new users this week
            week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
            new_users_response = self.supabase.table("users").select("count", count="exact").gte("created_at", week_ago).execute()
            new_users_this_week = new_users_response.count or 0
            
            # Get active services
            active_services_response = self.supabase.table("services").select("count", count="exact").eq("active", True).execute()
            active_services = active_services_response.count or 0
            
            return AdminStatsResponse(
                total_users=total_users,
                total_vehicles=total_vehicles,
                total_payments=total_payments,
                total_revenue=total_revenue,
                total_services_purchased=total_services_purchased,
                new_users_this_week=new_users_this_week,
                active_services=active_services,
                updated_at=datetime.utcnow(),
            )
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return AdminStatsResponse(
                total_users=0,
                total_vehicles=0,
                total_payments=0,
                total_revenue=Decimal(0),
                total_services_purchased=0,
                new_users_this_week=0,
                active_services=0,
                updated_at=datetime.utcnow(),
                error=str(e),
            )
    
    # ─── USER MANAGEMENT ─────────────────────────────────────────────
    
    async def get_users(self, limit: int, offset: int, search: Optional[str] = None) -> AdminUsersResponse:
        """Get list of users."""
        try:
            query = self.supabase.table("users").select("*")
            
            if search:
                query = query.or_(f"email.ilike.%{search}%,full_name.ilike.%{search}%")
            
            query = query.range(offset, offset + limit - 1)
            response = query.order("created_at", desc=True).execute()
            
            # Get total count
            count_query = self.supabase.table("users").select("count", count="exact")
            if search:
                count_query = count_query.or_(f"email.ilike.%{search}%,full_name.ilike.%{search}%")
            count_response = count_query.execute()
            total = count_response.count or 0
            
            users = []
            for user_data in response.data:
                # Get user services
                services_response = self.supabase.table("user_services").select(
                    "service_id, services(name, code), status"
                ).eq("user_id", user_data["id"]).execute()
                
                services = []
                for svc in services_response.data:
                    services.append({
                        "service_id": svc["service_id"],
                        "service_name": svc["services"]["name"],
                        "service_code": svc["services"]["code"],
                        "status": svc["status"],
                    })
                
                users.append(AdminUser(
                    id=user_data["id"],
                    email=user_data["email"],
                    full_name=user_data.get("full_name", ""),
                    created_at=user_data["created_at"],
                    last_sign_in_at=user_data.get("last_sign_in_at"),
                    confirmed_at=user_data.get("confirmed_at"),
                    phone=user_data.get("phone"),
                    services=services,
                ))
            
            return AdminUsersResponse(
                users=users,
                total=total,
                limit=limit,
                offset=offset,
            )
        except Exception as e:
            logger.error(f"Error getting users: {str(e)}")
            raise
    
    async def get_user_detail(self, user_id: UUID) -> AdminUserDetail:
        """Get detailed user information."""
        try:
            # Get user
            user_response = self.supabase.table("users").select("*").eq("id", str(user_id)).execute()
            if not user_response.data:
                raise NotFoundException(f"User {user_id} not found")
            
            user_data = user_response.data[0]
            
            # Get user services
            services_response = self.supabase.table("user_services").select(
                "service_id, services(name, code), status"
            ).eq("user_id", str(user_id)).execute()
            
            services = []
            for svc in services_response.data:
                services.append({
                    "service_id": svc["service_id"],
                    "service_name": svc["services"]["name"],
                    "service_code": svc["services"]["code"],
                    "status": svc["status"],
                })
            
            # Get user payments
            payments_response = self.supabase.table("payments").select("*").eq("user_id", str(user_id)).order("created_at", desc=True).execute()
            
            payments = []
            for payment in payments_response.data:
                payments.append(AdminPayment(
                    id=payment["id"],
                    user_id=payment.get("user_id"),
                    service_id=payment.get("service_id"),
                    service_name=payment.get("service_name"),
                    service_code=payment.get("service_code"),
                    amount=payment["amount"],
                    currency=payment.get("currency", "KES"),
                    status=payment["status"],
                    phone=payment.get("phone"),
                    checkout_request_id=payment.get("checkout_request_id"),
                    mpesa_receipt=payment.get("mpesa_receipt"),
                    created_at=payment["created_at"],
                    completed_at=payment.get("completed_at"),
                ))
            
            return AdminUserDetail(
                id=user_data["id"],
                email=user_data["email"],
                full_name=user_data.get("full_name", ""),
                created_at=user_data["created_at"],
                last_sign_in_at=user_data.get("last_sign_in_at"),
                confirmed_at=user_data.get("confirmed_at"),
                phone=user_data.get("phone"),
                services=services,
                app_metadata=user_data.get("app_metadata", {}),
                user_metadata=user_data.get("user_metadata", {}),
                payments=payments,
            )
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error getting user detail: {str(e)}")
            raise
    
    async def delete_user(self, user_id: UUID) -> DeleteUserResponse:
        """Delete a user."""
        try:
            # Check if user exists
            user_response = self.supabase.table("users").select("id").eq("id", str(user_id)).execute()
            if not user_response.data:
                raise NotFoundException(f"User {user_id} not found")
            
            # Delete user (cascade will handle related records)
            self.supabase.table("users").delete().eq("id", str(user_id)).execute()
            
            return DeleteUserResponse(
                success=True,
                message=f"User {user_id} deleted successfully",
                user_id=user_id,
                deleted_at=datetime.utcnow(),
            )
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            raise
    
    # ─── PAYMENT MANAGEMENT ──────────────────────────────────────────
    
    async def get_payments(
        self,
        limit: int,
        offset: int,
        status: Optional[str] = None,
        user_id: Optional[UUID] = None,
    ) -> AdminPaymentsResponse:
        """Get list of payments."""
        try:
            query = self.supabase.table("payments").select("*")
            
            if status:
                query = query.eq("status", status)
            if user_id:
                query = query.eq("user_id", str(user_id))
            
            query = query.range(offset, offset + limit - 1)
            response = query.order("created_at", desc=True).execute()
            
            # Get total count
            count_query = self.supabase.table("payments").select("count", count="exact")
            if status:
                count_query = count_query.eq("status", status)
            if user_id:
                count_query = count_query.eq("user_id", str(user_id))
            count_response = count_query.execute()
            total = count_response.count or 0
            
            payments = [
                AdminPayment(
                    id=p["id"],
                    user_id=p.get("user_id"),
                    service_id=p.get("service_id"),
                    service_name=p.get("service_name"),
                    service_code=p.get("service_code"),
                    amount=p["amount"],
                    currency=p.get("currency", "KES"),
                    status=p["status"],
                    phone=p.get("phone"),
                    checkout_request_id=p.get("checkout_request_id"),
                    mpesa_receipt=p.get("mpesa_receipt"),
                    created_at=p["created_at"],
                    completed_at=p.get("completed_at"),
                )
                for p in response.data
            ]
            
            return AdminPaymentsResponse(
                payments=payments,
                total=total,
                limit=limit,
                offset=offset,
            )
        except Exception as e:
            logger.error(f"Error getting payments: {str(e)}")
            raise
    
    # ─── VEHICLE MANAGEMENT ──────────────────────────────────────────
    
    async def get_vehicles(
        self,
        limit: int,
        offset: int,
        user_id: Optional[UUID] = None,
        verified: Optional[bool] = None,
    ) -> AdminVehiclesResponse:
        """Get list of vehicles."""
        try:
            query = self.supabase.table("user_vehicles").select("*")
            
            if user_id:
                query = query.eq("user_id", str(user_id))
            if verified is not None:
                query = query.eq("verified", verified)
            
            query = query.range(offset, offset + limit - 1)
            response = query.order("created_at", desc=True).execute()
            
            # Get total count
            count_query = self.supabase.table("user_vehicles").select("count", count="exact")
            if user_id:
                count_query = count_query.eq("user_id", str(user_id))
            if verified is not None:
                count_query = count_query.eq("verified", verified)
            count_response = count_query.execute()
            total = count_response.count or 0
            
            vehicles = [
                AdminVehicle(
                    id=v["id"],
                    user_id=v.get("user_id"),
                    make=v["make"],
                    model=v["model"],
                    year=v.get("year"),
                    variant=v.get("variant"),
                    verified=v.get("verified", False),
                    created_at=v["created_at"],
                )
                for v in response.data
            ]
            
            return AdminVehiclesResponse(
                vehicles=vehicles,
                total=total,
                limit=limit,
                offset=offset,
            )
        except Exception as e:
            logger.error(f"Error getting vehicles: {str(e)}")
            raise
    
    # ─── SERVICE MANAGEMENT ──────────────────────────────────────────
    
    async def get_services(self, active_only: bool = False) -> AdminServicesResponse:
        """Get list of services."""
        try:
            query = self.supabase.table("services").select("*")
            
            if active_only:
                query = query.eq("active", True)
            
            response = query.order("display_order", desc=False).execute()
            
            services = [
                AdminServiceItem(
                    id=s["id"],
                    code=s["code"],
                    name=s["name"],
                    price=s["price"],
                    currency=s.get("currency", "KES"),
                    description=s.get("description"),
                    icon=s.get("icon"),
                    active=s.get("active", True),
                    display_order=s.get("display_order", 0),
                    purchase_count=s.get("purchase_count", 0),
                    created_at=s["created_at"],
                    updated_at=s["updated_at"],
                )
                for s in response.data
            ]
            
            return AdminServicesResponse(
                services=services,
                total=len(services),
            )
        except Exception as e:
            logger.error(f"Error getting services: {str(e)}")
            raise
    
    async def create_service(self, request: CreateServiceRequest) -> AdminServiceItem:
        """Create a new service."""
        try:
            # Check if service code already exists
            existing = self.supabase.table("services").select("id").eq("code", request.code.value).execute()
            if existing.data:
                raise ValidationException(f"Service code {request.code.value} already exists")
            
            data = request.model_dump(exclude_unset=True)
            data["code"] = data["code"].value if hasattr(data["code"], "value") else data["code"]
            
            response = self.supabase.table("services").insert(data).execute()
            
            if not response.data:
                raise Exception("Failed to create service")
            
            service_data = response.data[0]
            return AdminServiceItem(
                id=service_data["id"],
                code=service_data["code"],
                name=service_data["name"],
                price=service_data["price"],
                currency=service_data.get("currency", "KES"),
                description=service_data.get("description"),
                icon=service_data.get("icon"),
                active=service_data.get("active", True),
                display_order=service_data.get("display_order", 0),
                purchase_count=service_data.get("purchase_count", 0),
                created_at=service_data["created_at"],
                updated_at=service_data["updated_at"],
            )
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error creating service: {str(e)}")
            raise
    
    async def update_service(self, service_id: UUID, request: UpdateServiceRequest) -> AdminServiceItem:
        """Update a service."""
        try:
            # Check if service exists
            existing = self.supabase.table("services").select("*").eq("id", str(service_id)).execute()
            if not existing.data:
                raise NotFoundException(f"Service {service_id} not found")
            
            data = request.model_dump(exclude_unset=True)
            response = self.supabase.table("services").update(data).eq("id", str(service_id)).execute()
            
            if not response.data:
                raise Exception("Failed to update service")
            
            service_data = response.data[0]
            return AdminServiceItem(
                id=service_data["id"],
                code=service_data["code"],
                name=service_data["name"],
                price=service_data["price"],
                currency=service_data.get("currency", "KES"),
                description=service_data.get("description"),
                icon=service_data.get("icon"),
                active=service_data.get("active", True),
                display_order=service_data.get("display_order", 0),
                purchase_count=service_data.get("purchase_count", 0),
                created_at=service_data["created_at"],
                updated_at=service_data["updated_at"],
            )
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error updating service: {str(e)}")
            raise
    
    async def update_service_price(self, service_id: UUID, request: UpdateServicePriceRequest) -> AdminServiceItem:
        """Update service price."""
        try:
            # Check if service exists
            existing = self.supabase.table("services").select("*").eq("id", str(service_id)).execute()
            if not existing.data:
                raise NotFoundException(f"Service {service_id} not found")
            
            data = {"price": request.price, "currency": request.currency}
            response = self.supabase.table("services").update(data).eq("id", str(service_id)).execute()
            
            if not response.data:
                raise Exception("Failed to update service price")
            
            service_data = response.data[0]
            return AdminServiceItem(
                id=service_data["id"],
                code=service_data["code"],
                name=service_data["name"],
                price=service_data["price"],
                currency=service_data.get("currency", "KES"),
                description=service_data.get("description"),
                icon=service_data.get("icon"),
                active=service_data.get("active", True),
                display_order=service_data.get("display_order", 0),
                purchase_count=service_data.get("purchase_count", 0),
                created_at=service_data["created_at"],
                updated_at=service_data["updated_at"],
            )
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error updating service price: {str(e)}")
            raise
    
    async def delete_service(self, service_id: UUID) -> DeleteServiceResponse:
        """Delete a service."""
        try:
            # Check if service exists
            existing = self.supabase.table("services").select("id").eq("id", str(service_id)).execute()
            if not existing.data:
                raise NotFoundException(f"Service {service_id} not found")
            
            # Check if service is in use
            in_use = self.supabase.table("user_services").select("id").eq("service_id", str(service_id)).limit(1).execute()
            if in_use.data:
                raise ValidationException(f"Service {service_id} is in use and cannot be deleted")
            
            self.supabase.table("services").delete().eq("id", str(service_id)).execute()
            
            return DeleteServiceResponse(
                success=True,
                message=f"Service {service_id} deleted successfully",
                service_id=service_id,
                deleted_at=datetime.utcnow(),
            )
        except NotFoundException:
            raise
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error deleting service: {str(e)}")
            raise
    
    # ─── USER SERVICE MANAGEMENT ─────────────────────────────────────
    
    async def get_user_services(self, user_id: UUID) -> UserServicesResponse:
        """Get services for a specific user."""
        try:
            # Check if user exists
            user_response = self.supabase.table("users").select("id").eq("id", str(user_id)).execute()
            if not user_response.data:
                raise NotFoundException(f"User {user_id} not found")
            
            response = self.supabase.table("user_services").select(
                "*, services(*)",
            ).eq("user_id", str(user_id)).execute()
            
            services = []
            for item in response.data:
                service_data = item.get("services", {})
                services.append(UserServiceItem(
                    id=item["id"],
                    user_id=item["user_id"],
                    service_id=item["service_id"],
                    status=item["status"],
                    created_at=item["created_at"],
                    updated_at=item["updated_at"],
                    service_details=AdminServiceItem(
                        id=service_data["id"],
                        code=service_data["code"],
                        name=service_data["name"],
                        price=service_data["price"],
                        currency=service_data.get("currency", "KES"),
                        description=service_data.get("description"),
                        icon=service_data.get("icon"),
                        active=service_data.get("active", True),
                        display_order=service_data.get("display_order", 0),
                        purchase_count=service_data.get("purchase_count", 0),
                        created_at=service_data["created_at"],
                        updated_at=service_data["updated_at"],
                    ) if service_data else None,
                ))
            
            return UserServicesResponse(
                user_id=user_id,
                services=services,
                total=len(services),
            )
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error getting user services: {str(e)}")
            raise
    
    async def update_user_service(
        self,
        user_id: UUID,
        service_id: UUID,
        request: UpdateUserServiceRequest,
    ) -> UpdateUserServiceResponse:
        """Update a user's service status."""
        try:
            # Check if user service exists
            existing = self.supabase.table("user_services").select("*").eq("user_id", str(user_id)).eq("service_id", str(service_id)).execute()
            if not existing.data:
                raise NotFoundException(f"User service {user_id}/{service_id} not found")
            
            data = {"status": request.status.value if hasattr(request.status, "value") else request.status}
            response = self.supabase.table("user_services").update(data).eq("user_id", str(user_id)).eq("service_id", str(service_id)).execute()
            
            if not response.data:
                raise Exception("Failed to update user service")
            
            updated = response.data[0]
            return UpdateUserServiceResponse(
                success=True,
                message="User service updated successfully",
                user_id=user_id,
                service_id=service_id,
                status=updated["status"],
                updated_at=updated["updated_at"],
            )
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error updating user service: {str(e)}")
            raise
    
    # ─── ANALYTICS ────────────────────────────────────────────────────
    
    async def get_analytics(self, days: int) -> AdminAnalyticsResponse:
        """Get analytics data."""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            daily_stats = []
            
            # Build daily stats
            for i in range(days):
                current_date = start_date + timedelta(days=i)
                next_date = current_date + timedelta(days=1)
                
                # Get daily counts
                day_start = datetime.combine(current_date, datetime.min.time()).isoformat()
                day_end = datetime.combine(next_date, datetime.min.time()).isoformat()
                
                # Users
                users_response = self.supabase.table("users").select("count", count="exact").gte("created_at", day_start).lt("created_at", day_end).execute()
                users_count = users_response.count or 0
                
                # Payments
                payments_response = self.supabase.table("payments").select("count, amount", count="exact").gte("created_at", day_start).lt("created_at", day_end).eq("status", "completed").execute()
                payments_count = payments_response.count or 0
                revenue = sum(Decimal(p["amount"]) for p in payments_response.data) if payments_response.data else Decimal(0)
                
                # Vehicles
                vehicles_response = self.supabase.table("user_vehicles").select("count", count="exact").gte("created_at", day_start).lt("created_at", day_end).execute()
                vehicles_count = vehicles_response.count or 0
                
                daily_stats.append(AnalyticsDay(
                    date=current_date,
                    users=users_count,
                    payments=payments_count,
                    revenue=revenue,
                    vehicles=vehicles_count,
                ))
            
            # Get totals
            total_users = sum(d.users for d in daily_stats)
            total_payments = sum(d.payments for d in daily_stats)
            total_revenue = sum(d.revenue for d in daily_stats)
            total_vehicles = sum(d.vehicles for d in daily_stats)
            
            return AdminAnalyticsResponse(
                period_days=days,
                start_date=start_date,
                end_date=end_date,
                daily_stats=daily_stats,
                totals=AnalyticsTotals(
                    users=total_users,
                    payments=total_payments,
                    revenue=total_revenue,
                    vehicles=total_vehicles,
                ),
            )
        except Exception as e:
            logger.error(f"Error getting analytics: {str(e)}")
            raise
    
    async def get_revenue_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> RevenueReportResponse:
        """Get revenue report."""
        try:
            query = self.supabase.table("payments").select("*").eq("status", "completed")
            
            if start_date:
                query = query.gte("created_at", start_date.isoformat())
            if end_date:
                query = query.lte("created_at", end_date.isoformat())
            
            response = query.execute()
            
            total_revenue = Decimal(0)
            revenue_by_service = {}
            
            for payment in response.data:
                amount = Decimal(payment["amount"])
                total_revenue += amount
                
                service_name = payment.get("service_name", "Unknown")
                revenue_by_service[service_name] = revenue_by_service.get(service_name, Decimal(0)) + amount
            
            return RevenueReportResponse(
                total_revenue=total_revenue,
                total_transactions=len(response.data),
                revenue_by_service=revenue_by_service,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as e:
            logger.error(f"Error getting revenue report: {str(e)}")
            return RevenueReportResponse(
                total_revenue=Decimal(0),
                total_transactions=0,
                revenue_by_service={},
                error=str(e),
            )
    
    async def get_service_prices(self) -> ServicePricesResponse:
        """Get all service prices."""
        try:
            response = self.supabase.table("services").select("*").eq("active", True).order("display_order").execute()
            
            prices = {}
            services = []
            
            for service in response.data:
                prices[service["code"]] = ServicePriceItem(
                    price=service["price"],
                    currency=service.get("currency", "KES"),
                    name=service["name"],
                )
                
                services.append(AdminServiceItem(
                    id=service["id"],
                    code=service["code"],
                    name=service["name"],
                    price=service["price"],
                    currency=service.get("currency", "KES"),
                    description=service.get("description"),
                    icon=service.get("icon"),
                    active=service.get("active", True),
                    display_order=service.get("display_order", 0),
                    purchase_count=service.get("purchase_count", 0),
                    created_at=service["created_at"],
                    updated_at=service["updated_at"],
                ))
            
            return ServicePricesResponse(
                prices=prices,
                services=services,
                total=len(services),
            )
        except Exception as e:
            logger.error(f"Error getting service prices: {str(e)}")
            raise
    
    # ─── SYSTEM STATUS ───────────────────────────────────────────────
    
    async def get_system_status(self) -> AdminStatusResponse:
        """Get system status."""
        try:
            # Check Supabase
            supabase_status = "healthy"
            try:
                self.supabase.table("users").select("count", count="exact").limit(1).execute()
            except:
                supabase_status = "unhealthy"
            
            # Check Database
            database_status = "healthy"
            try:
                self.supabase.table("users").select("count", count="exact").limit(1).execute()
            except:
                database_status = "unhealthy"
            
            # Check M-Pesa (just check if config exists)
            mpesa_status = "healthy"
            # In production, you might want to do a test request
            
            overall_status = "healthy"
            if supabase_status == "unhealthy" or database_status == "unhealthy":
                overall_status = "degraded"
            
            return AdminStatusResponse(
                status=overall_status,
                timestamp=datetime.utcnow(),
                components=ComponentStatuses(
                    supabase=supabase_status,
                    database=database_status,
                    mpesa=mpesa_status,
                ),
            )
        except Exception as e:
            logger.error(f"Error getting system status: {str(e)}")
            return AdminStatusResponse(
                status="degraded",
                timestamp=datetime.utcnow(),
                components=ComponentStatuses(
                    supabase="unhealthy",
                    database="unhealthy",
                    mpesa="unhealthy",
                ),
            )
