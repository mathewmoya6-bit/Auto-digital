"""
Auto-D Kenya - Admin Repository
================================================
TYPE: MODULE - Database Access Layer
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class AdminRepository:
    """Repository for admin database operations."""

    def __init__(self):
        pass

    @property
    def db(self):
        client = get_supabase()

        if client is None:
            raise RuntimeError("Supabase client is not initialized")

        return client

    # ==============================================================
    # DASHBOARD
    # ==============================================================

    async def get_dashboard_stats(self) -> Dict[str, Any]:

        users = self.db.table("profiles").select("*", count="exact").execute()

        vehicles = self.db.table("vehicles").select("*", count="exact").execute()

        payments = self.db.table("payments").select("*", count="exact").execute()

        services = self.db.table("services").select("*", count="exact").execute()

        revenue = (
            self.db.table("payments")
            .select("amount")
            .in_("status", ["paid", "completed", "success"])
            .execute()
        )

        total_revenue = 0.0

        if revenue.data:
            total_revenue = sum(
                float(item.get("amount", 0))
                for item in revenue.data
            )

        return {
            "total_users": users.count or 0,
            "total_vehicles": vehicles.count or 0,
            "total_payments": payments.count or 0,
            "total_services_purchased": payments.count or 0,
            "active_services": services.count or 0,
            "new_users_this_week": 0,
            "total_revenue": total_revenue,
            "updated_at": datetime.utcnow(),
            "error": None,
        }

    # ==============================================================
    # USERS
    # ==============================================================

    async def get_users(
        self,
        limit: int,
        offset: int,
    ) -> Dict[str, Any]:

        response = (
            self.db.table("profiles")
            .select("*", count="exact")
            .range(offset, offset + limit - 1)
            .order("created_at", desc=True)
            .execute()
        )

        return {
            "users": response.data or [],
            "total": response.count or 0,
            "limit": limit,
            "offset": offset,
        }

    async def get_user(
        self,
        user_id: str,
    ) -> Optional[Dict]:

        response = (
            self.db.table("profiles")
            .select("*")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )

        return response.data

    async def delete_user(
        self,
        user_id: str,
    ) -> Dict[str, Any]:

        self.db.table("profiles").delete().eq("id", user_id).execute()

        return {
            "success": True,
            "user_id": user_id,
            "deleted_at": datetime.utcnow(),
            "message": "User deleted successfully",
        }

    # ==============================================================
    # PAYMENTS
    # ==============================================================

    async def get_payments(
        self,
        limit: int,
        offset: int,
    ) -> Dict[str, Any]:

        response = (
            self.db.table("payments")
            .select("*", count="exact")
            .range(offset, offset + limit - 1)
            .order("created_at", desc=True)
            .execute()
        )

        return {
            "payments": response.data or [],
            "total": response.count or 0,
            "limit": limit,
            "offset": offset,
        }

    async def get_payment(
        self,
        payment_id: str,
    ) -> Optional[Dict]:

        response = (
            self.db.table("payments")
            .select("*")
            .eq("id", payment_id)
            .maybe_single()
            .execute()
        )

        return response.data

    # ==============================================================
    # SERVICES
    # ==============================================================

    async def get_services(self) -> Dict[str, Any]:

        response = (
            self.db.table("services")
            .select("*", count="exact")
            .order("display_order")
            .execute()
        )

        return {
            "services": response.data or [],
            "total": response.count or 0,
        }

    async def update_service(
        self,
        service_id: str,
        payload: Dict[str, Any],
    ) -> Optional[Dict]:

        response = (
            self.db.table("services")
            .update(payload)
            .eq("id", service_id)
            .execute()
        )

        return response.data[0] if response.data else None

    # ==============================================================
    # REPORTS
    # ==============================================================

    async def revenue_report(
        self,
        start_date=None,
        end_date=None,
    ) -> Dict[str, Any]:

        response = (
            self.db.table("payments")
            .select("amount")
            .in_("status", ["paid", "completed", "success"])
            .execute()
        )

        total = sum(
            float(item.get("amount", 0))
            for item in (response.data or [])
        )

        return {
            "total_revenue": total,
            "total_transactions": len(response.data or []),
            "revenue_by_service": {},
            "start_date": start_date,
            "end_date": end_date,
            "error": None,
        }

    # ==============================================================
    # HEALTH
    # ==============================================================

    async def health(self) -> Dict[str, Any]:

        try:

            self.db.table("services").select("id").limit(1).execute()

            return {
                "status": "healthy",
                "service": "admin",
                "timestamp": datetime.utcnow(),
            }

        except Exception as e:

            logger.exception("Admin health check failed")

            return {
                "status": "unhealthy",
                "service": "admin",
                "timestamp": datetime.utcnow(),
                "error": str(e),
            }
