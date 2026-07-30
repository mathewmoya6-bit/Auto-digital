# app/modules/admin/service.py
# Auto-D Kenya - Admin Service
# ================================================================
# TYPE: MODULE - Admin business logic

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.core.database import get_supabase
from app.core.exceptions import UnauthorizedException, NotFoundException

logger = logging.getLogger(__name__)


class AdminService:
    """Admin service for administrative functions."""
    
    def __init__(self):
        self.supabase = get_supabase()
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get admin statistics.
        
        Returns:
            Dict with user, vehicle, payment, and revenue statistics
        """
        try:
            # Get user count
            users_response = self.supabase.auth.admin.list_users()
            total_users = len(users_response.users) if users_response else 0
            
            # Get vehicle count
            vehicles_response = self.supabase.table("vehicles").select("count", count="exact").execute()
            total_vehicles = vehicles_response.count if vehicles_response else 0
            
            # Get payment count and total
            payments_response = self.supabase.table("mpesa_payments").select("*").execute()
            payments = payments_response.data if payments_response else []
            
            total_payments = len(payments)
            total_revenue = sum(float(p.get("amount", 0)) for p in payments if p.get("status") == "completed")
            
            # Get user services count
            services_response = self.supabase.table("user_services").select("count", count="exact").execute()
            total_services_purchased = services_response.count if services_response else 0
            
            # Get recent users (last 7 days)
            week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
            recent_users_response = self.supabase.table("users").select("count", count="exact").gte("created_at", week_ago).execute()
            new_users_this_week = recent_users_response.count if recent_users_response else 0
            
            return {
                "total_users": total_users,
                "total_vehicles": total_vehicles,
                "total_payments": total_payments,
                "total_revenue": round(total_revenue, 2),
                "total_services_purchased": total_services_purchased,
                "new_users_this_week": new_users_this_week,
                "updated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting admin stats: {str(e)}")
            return {
                "error": str(e),
                "total_users": 0,
                "total_vehicles": 0,
                "total_payments": 0,
                "total_revenue": 0,
                "total_services_purchased": 0,
                "new_users_this_week": 0,
                "updated_at": datetime.utcnow().isoformat()
            }
    
    async def get_users(
        self, 
        limit: int = 50, 
        offset: int = 0,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all users with pagination.
        
        Args:
            limit: Number of users to return
            offset: Pagination offset
            search: Optional search term for email
            
        Returns:
            Dict with users list and pagination info
        """
        try:
            # Get users from Supabase Auth
            response = self.supabase.auth.admin.list_users()
            
            if not response or not response.users:
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
            
            return {
                "users": paginated_users,
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"Error getting users: {str(e)}")
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
            
            if not response or not response.user:
                raise NotFoundException(f"User with ID {user_id} not found")
            
            user = response.user
            return {
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
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {str(e)}")
            raise NotFoundException(f"User with ID {user_id} not found")
    
    async def get_all_payments(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all payments with pagination and filtering.
        
        Args:
            limit: Number of payments to return
            offset: Pagination offset
            status: Filter by status (pending, completed, failed)
            
        Returns:
            Dict with payments list and pagination info
        """
        try:
            query = self.supabase.table("mpesa_payments").select("*")
            
            if status:
                query = query.eq("status", status)
            
            response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            payments = response.data if response else []
            
            # Get total count
            count_query = self.supabase.table("mpesa_payments").select("count", count="exact")
            if status:
                count_query = count_query.eq("status", status)
            count_response = count_query.execute()
            total = count_response.count if count_response else 0
            
            # Get user details for each payment
            for payment in payments:
                if payment.get("user_id"):
                    try:
                        user_response = self.supabase.auth.admin.get_user_by_id(payment["user_id"])
                        if user_response and user_response.user:
                            payment["user_email"] = user_response.user.email
                            payment["user_name"] = user_response.user.user_metadata.get("full_name", "")
                    except Exception:
                        payment["user_email"] = "Unknown"
                        payment["user_name"] = "Unknown"
            
            return {
                "payments": payments,
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"Error getting payments: {str(e)}")
            return {"payments": [], "total": 0, "limit": limit, "offset": offset}
    
    async def get_all_vehicles(
        self,
        limit: int = 50,
        offset: int = 0,
        verified: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Get all vehicles with pagination.
        
        Args:
            limit: Number of vehicles to return
            offset: Pagination offset
            verified: Filter by verification status
            
        Returns:
            Dict with vehicles list and pagination info
        """
        try:
            query = self.supabase.table("vehicles").select("*")
            
            if verified is not None:
                query = query.eq("verified", verified)
            
            response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            vehicles = response.data if response else []
            
            # Get total count
            count_query = self.supabase.table("vehicles").select("count", count="exact")
            if verified is not None:
                count_query = count_query.eq("verified", verified)
            count_response = count_query.execute()
            total = count_response.count if count_response else 0
            
            # Get user emails for each vehicle
            for vehicle in vehicles:
                if vehicle.get("user_id"):
                    try:
                        user_response = self.supabase.auth.admin.get_user_by_id(vehicle["user_id"])
                        if user_response and user_response.user:
                            vehicle["user_email"] = user_response.user.email
                    except Exception:
                        vehicle["user_email"] = "Unknown"
            
            return {
                "vehicles": vehicles,
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"Error getting vehicles: {str(e)}")
            return {"vehicles": [], "total": 0, "limit": limit, "offset": offset}
    
    async def get_all_services(self) -> Dict[str, Any]:
        """
        Get all available services.
        
        Returns:
            Dict with services list
        """
        try:
            response = self.supabase.table("services").select("*").order("display_order").execute()
            services = response.data if response else []
            
            # Count purchases for each service
            for service in services:
                try:
                    count_response = self.supabase.table("user_services").select("count", count="exact").eq("service_id", service["id"]).execute()
                    service["purchase_count"] = count_response.count if count_response else 0
                except Exception:
                    service["purchase_count"] = 0
            
            return {
                "services": services,
                "total": len(services)
            }
            
        except Exception as e:
            logger.error(f"Error getting services: {str(e)}")
            return {"services": [], "total": 0}
    
    async def get_platform_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get platform analytics for the specified period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict with analytics data
        """
        try:
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # Daily user registrations
            users_response = self.supabase.table("users").select("created_at").gte("created_at", start_date).execute()
            user_data = users_response.data if users_response else []
            
            # Daily payments
            payments_response = self.supabase.table("mpesa_payments").select("*").gte("created_at", start_date).execute()
            payment_data = payments_response.data if payments_response else []
            
            # Daily vehicle additions
            vehicles_response = self.supabase.table("vehicles").select("created_at").gte("created_at", start_date).execute()
            vehicle_data = vehicles_response.data if vehicles_response else []
            
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
                    daily_stats[date_key]["revenue"] += float(payment.get("amount", 0))
            
            for vehicle in vehicle_data:
                date_key = vehicle["created_at"][:10] if vehicle.get("created_at") else None
                if date_key in daily_stats:
                    daily_stats[date_key]["vehicles"] += 1
            
            # Convert to list and sort by date
            analytics = sorted(
                [daily_stats[date] for date in daily_stats.keys() if date in daily_stats],
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
            logger.error(f"Error getting analytics: {str(e)}")
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
        """
        try:
            # Check if user exists
            try:
                user_response = self.supabase.auth.admin.get_user_by_id(user_id)
                if not user_response or not user_response.user:
                    raise NotFoundException(f"User {user_id} not found")
            except Exception:
                raise NotFoundException(f"User {user_id} not found")
            
            # Check if service exists
            service_response = self.supabase.table("services").select("*").eq("id", service_id).execute()
            if not service_response.data:
                raise NotFoundException(f"Service {service_id} not found")
            
            # Update or create user service
            existing = self.supabase.table("user_services").select("*").eq("user_id", user_id).eq("service_id", service_id).execute()
            
            if existing.data:
                # Update existing
                response = self.supabase.table("user_services").update({
                    "status": status,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", existing.data[0]["id"]).execute()
            else:
                # Create new
                response = self.supabase.table("user_services").insert({
                    "user_id": user_id,
                    "service_id": service_id,
                    "status": status,
                    "purchased_at": datetime.utcnow().isoformat(),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }).execute()
            
            return {
                "message": f"User service updated to {status}",
                "user_id": user_id,
                "service_id": service_id,
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error updating user service: {str(e)}")
            raise
    
    async def delete_user(self, user_id: str) -> Dict[str, Any]:
        """
        Delete a user (admin action).
        
        Args:
            user_id: User ID
            
        Returns:
            Success message
        """
        try:
            # Check if user exists
            try:
                user_response = self.supabase.auth.admin.get_user_by_id(user_id)
                if not user_response or not user_response.user:
                    raise NotFoundException(f"User {user_id} not found")
            except Exception:
                raise NotFoundException(f"User {user_id} not found")
            
            # Delete user from Supabase Auth
            self.supabase.auth.admin.delete_user(user_id)
            
            # Delete user data from tables (cascade will handle)
            self.supabase.table("vehicles").delete().eq("user_id", user_id).execute()
            self.supabase.table("user_services").delete().eq("user_id", user_id).execute()
            self.supabase.table("mpesa_payments").delete().eq("user_id", user_id).execute()
            
            return {
                "message": f"User {user_id} deleted successfully",
                "user_id": user_id,
                "deleted_at": datetime.utcnow().isoformat()
            }
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            raise
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get system status for admin dashboard.
        
        Returns:
            System status information
        """
        status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {}
        }
        
        # Check Supabase
        try:
            self.supabase.table("services").select("count").limit(1).execute()
            status["components"]["supabase"] = "healthy"
        except Exception as e:
            status["components"]["supabase"] = f"unhealthy: {str(e)}"
            status["status"] = "degraded"
        
        # Check M-Pesa
        try:
            from app.modules.mpesa.service import MpesaService
            mpesa = MpesaService()
            await mpesa.stk_push._get_access_token()
            status["components"]["mpesa"] = "healthy"
        except Exception as e:
            status["components"]["mpesa"] = f"unhealthy: {str(e)}"
            if status["status"] == "healthy":
                status["status"] = "degraded"
        
        return status
