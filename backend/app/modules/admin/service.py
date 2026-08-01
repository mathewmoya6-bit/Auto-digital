# app/modules/admin/service.py
# Auto-D Kenya - Admin Service
# ================================================================
# TYPE: MODULE - Admin business logic

import logging
import asyncio
from decimal import Decimal
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from functools import lru_cache

from app.core.database import get_supabase
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)

# ─── CONSTANTS ──────────────────────────────────────────────────
SUCCESS_STATUSES = {"completed", "paid", "success"}
PAYMENT_STATUSES = {"pending", "completed", "failed", "cancelled", "paid", "success"}
SERVICE_CODES = {"valuation", "mileage", "ownership", "tco"}

# ─── HELPERS ──────────────────────────────────────────────────

def safe_data(response) -> List[Dict[str, Any]]:
    """Safely extract data from Supabase response."""
    return response.data if response and hasattr(response, 'data') else []

def now_iso() -> str:
    """Get current UTC time as ISO string."""
    return datetime.utcnow().isoformat()


class AdminService:
    """Admin service for administrative functions."""
    
    def __init__(self):
        self.supabase = get_supabase()
        self._services_cache = None
        self._services_cache_time = None
        self._services_cache_ttl = 300  # 5 minutes
    
    # ─── CACHE HELPERS ──────────────────────────────────────────
    
    async def _get_services_map(self) -> Dict[int, Dict[str, Any]]:
        """
        Get cached services map.
        
        Returns:
            Dict mapping service_id to service data
        """
        now = datetime.utcnow().timestamp()
        
        if (self._services_cache is not None and 
            self._services_cache_time is not None and
            now - self._services_cache_time < self._services_cache_ttl):
            return self._services_cache
        
        try:
            response = self.supabase.table("services").select("id, name, code, price, currency").execute()
            services = safe_data(response)
            
            service_map = {}
            for service in services:
                service_map[service["id"]] = service
            
            self._services_cache = service_map
            self._services_cache_time = now
            
            return service_map
            
        except Exception as e:
            logger.exception("Failed to load services map")
            return {}
    
    def _clear_services_cache(self) -> None:
        """Clear the services cache."""
        self._services_cache = None
        self._services_cache_time = None
    
    # ─── STATISTICS ──────────────────────────────────────────────
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get admin statistics.
        
        Returns:
            Dict with user, vehicle, payment, and revenue statistics
        """
        try:
            # Get user count from auth (paginated)
            total_users = await self._get_user_count()
            
            # Get vehicle count
            vehicles_response = self.supabase.table("vehicles").select("id", count="exact").execute()
            total_vehicles = vehicles_response.count if vehicles_response else 0
            
            # Get payment stats - only count and revenue
            revenue_response = (
                self.supabase.table("payments")
                .select("amount, status")
                .in_("status", list(SUCCESS_STATUSES))
                .execute()
            )
            
            payments = safe_data(revenue_response)
            total_payments = len(payments)
            total_revenue = sum(Decimal(str(p.get("amount", 0))) for p in payments)
            
            # Get user services count
            services_response = self.supabase.table("user_services").select("id", count="exact").execute()
            total_services_purchased = services_response.count if services_response else 0
            
            # Get recent users (last 7 days)
            week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
            recent_users_response = (
                self.supabase.table("users")
                .select("id", count="exact")
                .gte("created_at", week_ago)
                .execute()
            )
            new_users_this_week = recent_users_response.count if recent_users_response else 0
            
            # Get active services from database
            active_services_response = (
                self.supabase.table("services")
                .select("id", count="exact")
                .eq("active", True)
                .execute()
            )
            active_services = active_services_response.count if active_services_response else 0
            
            return {
                "total_users": total_users,
                "total_vehicles": total_vehicles,
                "total_payments": total_payments,
                "total_revenue": float(total_revenue),
                "total_services_purchased": total_services_purchased,
                "new_users_this_week": new_users_this_week,
                "active_services": active_services,
                "updated_at": now_iso()
            }
            
        except Exception as e:
            logger.exception("Error getting admin stats")
            return {
                "error": str(e),
                "total_users": 0,
                "total_vehicles": 0,
                "total_payments": 0,
                "total_revenue": 0,
                "total_services_purchased": 0,
                "new_users_this_week": 0,
                "active_services": 0,
                "updated_at": now_iso()
            }
    
    async def _get_user_count(self) -> int:
        """Get total user count with pagination support."""
        try:
            response = self.supabase.auth.admin.list_users()
            if response and hasattr(response, 'users'):
                return len(response.users)
            return 0
        except Exception as e:
            logger.warning(f"Could not get user count: {e}")
            return 0
    
    # ─── USERS ────────────────────────────────────────────────────
    
    async def get_users(
        self, 
        limit: int = 50, 
        offset: int = 0,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all users with pagination.
        
        Args:
            limit: Number of users to return (1-200)
            offset: Pagination offset (>= 0)
            search: Optional search term for email
            
        Returns:
            Dict with users list and pagination info
        """
        # Validate pagination
        limit = max(1, min(200, limit))
        offset = max(0, offset)
        
        try:
            # Get users from Supabase Auth
            response = self.supabase.auth.admin.list_users()
            
            if not response or not hasattr(response, 'users'):
                return {"users": [], "total": 0, "limit": limit, "offset": offset}
            
            # Convert to list and filter
            users = []
            for user in response.users:
                user_data = {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.user_metadata.get("full_name", ""),
                    "created_at": user.created_at,
                    "last_sign_in_at": user.last_sign_in_at,
                    "confirmed_at": user.confirmed_at,
                    "phone": user.phone,
                    "user_metadata": user.user_metadata
                }
                users.append(user_data)
            
            # Apply search filter
            if search:
                search_lower = search.lower()
                users = [
                    u for u in users 
                    if search_lower in u["email"].lower() 
                    or search_lower in u["full_name"].lower()
                ]
            
            total = len(users)
            
            # Apply pagination
            paginated_users = users[offset:offset + limit]
            
            # Get service map for user services
            service_map = await self._get_services_map()
            
            # Get user services for each user (batch query)
            if paginated_users:
                user_ids = [u["id"] for u in paginated_users]
                services_response = (
                    self.supabase.table("user_services")
                    .select("user_id, service_id, status")
                    .in_("user_id", user_ids)
                    .execute()
                )
                user_services = safe_data(services_response)
                
                # Group services by user_id
                services_by_user = {}
                for us in user_services:
                    user_id = us.get("user_id")
                    if user_id not in services_by_user:
                        services_by_user[user_id] = []
                    
                    service = service_map.get(us.get("service_id"), {})
                    services_by_user[user_id].append({
                        "service_id": us.get("service_id"),
                        "service_name": service.get("name"),
                        "service_code": service.get("code"),
                        "status": us.get("status")
                    })
                
                # Attach services to users
                for user in paginated_users:
                    user["services"] = services_by_user.get(user["id"], [])
            
            return {
                "users": paginated_users,
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.exception("Error getting users")
            return {"users": [], "total": 0, "limit": limit, "offset": offset}
    
    async def get_user_by_id(self, user_id: str) -> Dict[str, Any]:
        """
        Get a specific user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User data
            
        Raises:
            NotFoundException: If user not found
        """
        try:
            response = self.supabase.auth.admin.get_user_by_id(user_id)
            
            if not response or not hasattr(response, 'user'):
                raise NotFoundException(f"User with ID {user_id} not found")
            
            user = response.user
            user_data = {
                "id": user.id,
                "email": user.email,
                "full_name": user.user_metadata.get("full_name", ""),
                "created_at": user.created_at,
                "last_sign_in_at": user.last_sign_in_at,
                "confirmed_at": user.confirmed_at,
                "phone": user.phone,
                "user_metadata": user.user_metadata,
                "app_metadata": user.app_metadata
            }
            
            # Get user services
            services_response = (
                self.supabase.table("user_services")
                .select("*, services(*)")
                .eq("user_id", user_id)
                .execute()
            )
            user_data["services"] = safe_data(services_response)
            
            # Get user payments
            payments_response = (
                self.supabase.table("payments")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )
            user_data["payments"] = safe_data(payments_response)
            
            return user_data
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.exception(f"Error getting user {user_id}")
            raise NotFoundException(f"User with ID {user_id} not found")
    
    # ─── PAYMENTS ──────────────────────────────────────────────────
    
    async def get_all_payments(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all payments with pagination and filtering.
        
        Args:
            limit: Number of payments to return (1-200)
            offset: Pagination offset (>= 0)
            status: Filter by status
            
        Returns:
            Dict with payments list and pagination info
        """
        # Validate pagination
        limit = max(1, min(200, limit))
        offset = max(0, offset)
        
        # Validate status
        if status and status not in PAYMENT_STATUSES:
            status = None
        
        try:
            query = self.supabase.table("payments").select("*")
            
            if status:
                query = query.eq("status", status)
            
            response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            payments = safe_data(response)
            
            # Get total count
            count_query = self.supabase.table("payments").select("id", count="exact")
            if status:
                count_query = count_query.eq("status", status)
            count_response = count_query.execute()
            total = count_response.count if count_response else 0
            
            # Get service map for payments (batch query)
            if payments:
                service_map = await self._get_services_map()
                for payment in payments:
                    service_id = payment.get("service_id")
                    if service_id and service_id in service_map:
                        payment["service_name"] = service_map[service_id].get("name")
                        payment["service_code"] = service_map[service_id].get("code")
                    else:
                        payment["service_name"] = "Unknown"
            
            return {
                "payments": payments,
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.exception("Error getting payments")
            return {"payments": [], "total": 0, "limit": limit, "offset": offset}
    
    # ─── VEHICLES ──────────────────────────────────────────────────
    
    async def get_all_vehicles(
        self,
        limit: int = 50,
        offset: int = 0,
        verified: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Get all vehicles with pagination.
        
        Args:
            limit: Number of vehicles to return (1-200)
            offset: Pagination offset (>= 0)
            verified: Filter by verification status
            
        Returns:
            Dict with vehicles list and pagination info
        """
        # Validate pagination
        limit = max(1, min(200, limit))
        offset = max(0, offset)
        
        try:
            query = self.supabase.table("vehicles").select("*")
            
            if verified is not None:
                query = query.eq("verified", verified)
            
            response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            vehicles = safe_data(response)
            
            # Get total count
            count_query = self.supabase.table("vehicles").select("id", count="exact")
            if verified is not None:
                count_query = count_query.eq("verified", verified)
            count_response = count_query.execute()
            total = count_response.count if count_response else 0
            
            return {
                "vehicles": vehicles,
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.exception("Error getting vehicles")
            return {"vehicles": [], "total": 0, "limit": limit, "offset": offset}
    
    # ─── SERVICES ──────────────────────────────────────────────────
    
    async def get_all_services(self) -> Dict[str, Any]:
        """
        Get all available services with prices from database.
        
        Returns:
            Dict with services list
        """
        try:
            response = self.supabase.table("services").select("*").order("display_order", ascending=True).execute()
            services = safe_data(response)
            
            # Count purchases for each service
            if services:
                service_ids = [s["id"] for s in services]
                count_response = (
                    self.supabase.table("user_services")
                    .select("service_id", count="exact")
                    .in_("service_id", service_ids)
                    .execute()
                )
                
                # Group counts by service_id
                counts = {}
                for item in safe_data(count_response):
                    sid = item.get("service_id")
                    if sid:
                        counts[sid] = counts.get(sid, 0) + 1
                
                for service in services:
                    service["purchase_count"] = counts.get(service["id"], 0)
            
            return {
                "services": services,
                "total": len(services)
            }
            
        except Exception as e:
            logger.exception("Error getting services")
            return {"services": [], "total": 0}
    
    async def update_service(
        self,
        service_id: int,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a service (admin action).
        
        Args:
            service_id: Service ID
            data: Service data to update
            
        Returns:
            Updated service data
            
        Raises:
            NotFoundException: If service not found
            ValueError: If validation fails
        """
        # Validate data
        if "price" in data:
            if data["price"] is not None and data["price"] < 0:
                raise ValueError("Price cannot be negative")
        
        if "display_order" in data:
            if data["display_order"] is not None and data["display_order"] < 0:
                raise ValueError("Display order cannot be negative")
        
        if "currency" in data:
            if data["currency"] is not None and not data["currency"].strip():
                raise ValueError("Currency cannot be empty")
        
        if "name" in data:
            if data["name"] is not None and not data["name"].strip():
                raise ValueError("Name cannot be empty")
        
        try:
            # Check if service exists
            response = self.supabase.table("services").select("*").eq("id", service_id).execute()
            if not safe_data(response):
                raise NotFoundException(f"Service {service_id} not found")
            
            # Update service
            update_data = {
                "updated_at": now_iso()
            }
            
            allowed_fields = ["name", "price", "currency", "description", "icon", "active", "display_order"]
            for field in allowed_fields:
                if field in data and data[field] is not None:
                    update_data[field] = data[field]
            
            response = self.supabase.table("services").update(update_data).eq("id", service_id).execute()
            
            # Clear cache
            self._clear_services_cache()
            
            logger.info(f"Service {service_id} updated: {update_data}")
            
            return {
                "message": "Service updated successfully",
                "service": safe_data(response)[0] if safe_data(response) else None
            }
            
        except NotFoundException:
            raise
        except ValueError:
            raise
        except Exception as e:
            logger.exception(f"Error updating service {service_id}")
            raise
    
    async def create_service(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new service (admin action).
        
        Args:
            data: Service data
            
        Returns:
            Created service data
            
        Raises:
            ValueError: If validation fails
        """
        # Validate required fields
        if not data.get("code"):
            raise ValueError("Service code is required")
        
        if not data.get("name"):
            raise ValueError("Service name is required")
        
        if data.get("price") is None:
            raise ValueError("Service price is required")
        
        if data["price"] < 0:
            raise ValueError("Price cannot be negative")
        
        if data["code"] not in SERVICE_CODES:
            raise ValueError(f"Service code must be one of: {', '.join(SERVICE_CODES)}")
        
        try:
            # Check if service code already exists
            existing = self.supabase.table("services").select("*").eq("code", data["code"]).execute()
            if safe_data(existing):
                raise ValueError(f"Service with code '{data['code']}' already exists")
            
            service_data = {
                "code": data["code"],
                "name": data["name"],
                "price": data["price"],
                "currency": data.get("currency", "KES"),
                "description": data.get("description"),
                "icon": data.get("icon"),
                "active": data.get("active", True),
                "display_order": data.get("display_order", 0),
                "created_at": now_iso(),
                "updated_at": now_iso()
            }
            
            response = self.supabase.table("services").insert(service_data).execute()
            
            # Clear cache
            self._clear_services_cache()
            
            logger.info(f"Service created: {data['code']}")
            
            return {
                "message": "Service created successfully",
                "service": safe_data(response)[0] if safe_data(response) else None
            }
            
        except ValueError:
            raise
        except Exception as e:
            logger.exception(f"Error creating service {data.get('code')}")
            raise
    
    async def delete_service(self, service_id: int) -> Dict[str, Any]:
        """
        Delete a service (admin action).
        
        Args:
            service_id: Service ID
            
        Returns:
            Success message
            
        Raises:
            NotFoundException: If service not found
            ValueError: If service has user purchases
        """
        try:
            # Check if service exists
            response = self.supabase.table("services").select("*").eq("id", service_id).execute()
            if not safe_data(response):
                raise NotFoundException(f"Service {service_id} not found")
            
            # Check if service has user_services records
            user_services = self.supabase.table("user_services").select("id", count="exact").eq("service_id", service_id).execute()
            if user_services.count and user_services.count > 0:
                raise ValueError(f"Service has {user_services.count} user purchases. Cannot delete.")
            
            # Delete service
            self.supabase.table("services").delete().eq("id", service_id).execute()
            
            # Clear cache
            self._clear_services_cache()
            
            logger.info(f"Service {service_id} deleted")
            
            return {
                "message": f"Service {service_id} deleted successfully",
                "service_id": service_id
            }
            
        except NotFoundException:
            raise
        except ValueError:
            raise
        except Exception as e:
            logger.exception(f"Error deleting service {service_id}")
            raise
    
    # ─── USER SERVICES ─────────────────────────────────────────────
    
    async def update_user_service(
        self, 
        user_id: str, 
        service_id: str, 
        status: str
    ) -> Dict[str, Any]:
        """
        Update a user's service status (admin action).
        
        Args:
            user_id: User ID
            service_id: Service ID
            status: New status (active, suspended, cancelled)
            
        Returns:
            Updated service data
            
        Raises:
            NotFoundException: If service or user not found
        """
        if status not in {"active", "suspended", "cancelled"}:
            raise ValueError(f"Invalid status: {status}")
        
        try:
            # Check if service exists
            service_response = self.supabase.table("services").select("*").eq("id", service_id).execute()
            if not safe_data(service_response):
                raise NotFoundException(f"Service {service_id} not found")
            
            # Update or create user service
            existing = (
                self.supabase.table("user_services")
                .select("*")
                .eq("user_id", user_id)
                .eq("service_id", service_id)
                .execute()
            )
            
            if safe_data(existing):
                # Update existing
                response = self.supabase.table("user_services").update({
                    "status": status,
                    "updated_at": now_iso()
                }).eq("id", safe_data(existing)[0]["id"]).execute()
            else:
                # Create new
                response = self.supabase.table("user_services").insert({
                    "user_id": user_id,
                    "service_id": service_id,
                    "status": status,
                    "created_at": now_iso(),
                    "updated_at": now_iso()
                }).execute()
            
            logger.info(f"User service updated: user={user_id}, service={service_id}, status={status}")
            
            return {
                "message": f"User service updated to {status}",
                "user_id": user_id,
                "service_id": service_id,
                "status": status,
                "updated_at": now_iso()
            }
            
        except NotFoundException:
            raise
        except ValueError:
            raise
        except Exception as e:
            logger.exception(f"Error updating user service for user {user_id}")
            raise
    
    # ─── PLATFORM ANALYTICS ──────────────────────────────────────
    
    async def get_platform_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get platform analytics for the specified period.
        
        Args:
            days: Number of days to analyze (1-365)
            
        Returns:
            Dict with analytics data
        """
        days = max(1, min(365, days))
        
        try:
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # Daily user registrations
            users_response = (
                self.supabase.table("users")
                .select("created_at")
                .gte("created_at", start_date)
                .execute()
            )
            user_data = safe_data(users_response)
            
            # Daily payments (only needed fields)
            payments_response = (
                self.supabase.table("payments")
                .select("created_at, amount, status")
                .gte("created_at", start_date)
                .execute()
            )
            payment_data = safe_data(payments_response)
            
            # Daily vehicle additions
            vehicles_response = (
                self.supabase.table("vehicles")
                .select("created_at")
                .gte("created_at", start_date)
                .execute()
            )
            vehicle_data = safe_data(vehicles_response)
            
            # Calculate daily stats
            daily_stats = {}
            current_date = datetime.utcnow() - timedelta(days=days)
            
            for i in range(days + 1):
                date_key = current_date.strftime("%Y-%m-%d")
                daily_stats[date_key] = {
                    "date": date_key,
                    "users": 0,
                    "payments": 0,
                    "revenue": 0,
                    "vehicles": 0
                }
                current_date += timedelta(days=1)
            
            # Populate daily stats
            for user in user_data:
                date_key = user["created_at"][:10] if user.get("created_at") else None
                if date_key in daily_stats:
                    daily_stats[date_key]["users"] += 1
            
            for payment in payment_data:
                date_key = payment["created_at"][:10] if payment.get("created_at") else None
                if date_key in daily_stats:
                    daily_stats[date_key]["payments"] += 1
                    if payment.get("status") in SUCCESS_STATUSES:
                        daily_stats[date_key]["revenue"] += float(payment.get("amount", 0))
            
            for vehicle in vehicle_data:
                date_key = vehicle["created_at"][:10] if vehicle.get("created_at") else None
                if date_key in daily_stats:
                    daily_stats[date_key]["vehicles"] += 1
            
            # Convert to list and sort by date
            analytics = sorted(
                [daily_stats[date] for date in daily_stats.keys()],
                key=lambda x: x["date"]
            )
            
            # Calculate totals
            total_users = sum(d["users"] for d in analytics)
            total_payments = sum(d["payments"] for d in analytics)
            total_revenue = sum(d["revenue"] for d in analytics)
            total_vehicles = sum(d["vehicles"] for d in analytics)
            
            return {
                "period_days": days,
                "start_date": start_date[:10],
                "end_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "daily_stats": analytics,
                "totals": {
                    "users": total_users,
                    "payments": total_payments,
                    "revenue": round(total_revenue, 2),
                    "vehicles": total_vehicles
                }
            }
            
        except Exception as e:
            logger.exception("Error getting analytics")
            return {
                "period_days": days,
                "daily_stats": [],
                "totals": {
                    "users": 0,
                    "payments": 0,
                    "revenue": 0,
                    "vehicles": 0
                }
            }
    
    # ─── USER MANAGEMENT ──────────────────────────────────────────
    
    async def delete_user(self, user_id: str) -> Dict[str, Any]:
        """
        Delete a user (admin action).
        
        Args:
            user_id: User ID
            
        Returns:
            Success message
            
        Raises:
            NotFoundException: If user not found
        """
        try:
            # Check if user exists
            try:
                user_response = self.supabase.auth.admin.get_user_by_id(user_id)
                if not user_response or not hasattr(user_response, 'user'):
                    raise NotFoundException(f"User {user_id} not found")
            except Exception:
                raise NotFoundException(f"User {user_id} not found")
            
            # Delete child tables first (safer order)
            self.supabase.table("user_services").delete().eq("user_id", user_id).execute()
            self.supabase.table("vehicles").delete().eq("user_id", user_id).execute()
            self.supabase.table("payments").delete().eq("user_id", user_id).execute()
            
            # Delete user from Supabase Auth last
            self.supabase.auth.admin.delete_user(user_id)
            
            logger.info(f"User {user_id} deleted")
            
            return {
                "message": f"User {user_id} deleted successfully",
                "user_id": user_id,
                "deleted_at": now_iso()
            }
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.exception(f"Error deleting user {user_id}")
            raise
    
    # ─── SYSTEM STATUS ────────────────────────────────────────────
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get system status for admin dashboard.
        
        Returns:
            System status information
        """
        status = {
            "status": "healthy",
            "timestamp": now_iso(),
            "components": {}
        }
        
        # Check Supabase
        try:
            self.supabase.table("services").select("id").limit(1).execute()
            status["components"]["supabase"] = "healthy"
        except Exception as e:
            status["components"]["supabase"] = f"unhealthy: {str(e)}"
            status["status"] = "degraded"
        
        # Check M-Pesa
        try:
            from app.modules.mpesa.service import MpesaService
            mpesa = MpesaService()
            await mpesa.health_check()
            status["components"]["mpesa"] = "healthy"
        except Exception as e:
            status["components"]["mpesa"] = f"unhealthy: {str(e)}"
            if status["status"] == "healthy":
                status["status"] = "degraded"
        
        # Check Database
        try:
            self.supabase.table("payments").select("id").limit(1).execute()
            status["components"]["database"] = "healthy"
        except Exception as e:
            status["components"]["database"] = f"unhealthy: {str(e)}"
            if status["status"] == "healthy":
                status["status"] = "degraded"
        
        return status
    
    # ─── SERVICE PRICE MANAGEMENT ──────────────────────────────────
    
    async def update_service_price(
        self,
        service_code: str,
        price: float,
        currency: str = "KES"
    ) -> Dict[str, Any]:
        """
        Update a service price (admin action).
        
        Args:
            service_code: Service code (e.g., 'valuation', 'mileage')
            price: New price (must be > 0)
            currency: Currency code
            
        Returns:
            Updated service data
            
        Raises:
            NotFoundException: If service not found
            ValueError: If price is invalid
        """
        # Validate price
        if price <= 0:
            raise ValueError("Price must be greater than 0")
        
        if not currency or not currency.strip():
            raise ValueError("Currency cannot be empty")
        
        try:
            # Check if service exists
            response = self.supabase.table("services").select("*").eq("code", service_code).execute()
            if not safe_data(response):
                raise NotFoundException(f"Service '{service_code}' not found")
            
            # Update price
            update_data = {
                "price": price,
                "currency": currency,
                "updated_at": now_iso()
            }
            
            response = self.supabase.table("services").update(update_data).eq("code", service_code).execute()
            
            # Clear cache
            self._clear_services_cache()
            
            logger.info(f"Service price updated: {service_code} = {currency} {price}")
            
            return {
                "message": f"Service '{service_code}' price updated to {currency} {price}",
                "service": safe_data(response)[0] if safe_data(response) else None
            }
            
        except NotFoundException:
            raise
        except ValueError:
            raise
        except Exception as e:
            logger.exception(f"Error updating service price for {service_code}")
            raise
    
    # ─── REVENUE REPORT ────────────────────────────────────────────
    
    async def get_revenue_report(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get revenue report for a date range.
        
        Args:
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            
        Returns:
            Revenue report
        """
        try:
            query = self.supabase.table("payments").select("*").in_("status", list(SUCCESS_STATUSES))
            
            if start_date:
                query = query.gte("created_at", start_date)
            if end_date:
                query = query.lte("created_at", end_date)
            
            response = query.order("created_at", desc=True).execute()
            payments = safe_data(response)
            
            # Get service map for revenue by service
            service_map = await self._get_services_map()
            
            # Calculate revenue by service
            revenue_by_service = {}
            for payment in payments:
                service_id = payment.get("service_id")
                if service_id and service_id in service_map:
                    service_name = service_map[service_id].get("name", str(service_id))
                else:
                    service_name = payment.get("service_name", "Unknown")
                
                if service_name not in revenue_by_service:
                    revenue_by_service[service_name] = Decimal(0)
                revenue_by_service[service_name] += Decimal(str(payment.get("amount", 0)))
            
            total_revenue = sum(revenue_by_service.values())
            
            return {
                "total_revenue": float(total_revenue),
                "total_transactions": len(payments),
                "revenue_by_service": {
                    k: float(v) for k, v in revenue_by_service.items()
                },
                "start_date": start_date,
                "end_date": end_date or now_iso()
            }
            
        except Exception as e:
            logger.exception("Error getting revenue report")
            return {
                "total_revenue": 0,
                "total_transactions": 0,
                "revenue_by_service": {},
                "error": str(e)
            }
    
    # ─── GET SERVICE PRICES ──────────────────────────────────────
    
    async def get_service_prices(self) -> Dict[str, Any]:
        """
        Get all service prices from the database.
        
        Returns:
            Dict with service prices
        """
        try:
            response = self.supabase.table("services").select("code, price, currency, name").eq("active", True).execute()
            services = safe_data(response)
            
            prices = {}
            for service in services:
                prices[service["code"]] = {
                    "price": service.get("price"),
                    "currency": service.get("currency", "KES"),
                    "name": service.get("name")
                }
            
            return {
                "prices": prices,
                "services": services,
                "total": len(services)
            }
            
        except Exception as e:
            logger.exception("Error getting service prices")
            return {"prices": {}, "services": [], "total": 0}
