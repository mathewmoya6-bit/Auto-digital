"""
Auto-D Kenya - Admin Service
================================================
Business logic for the Admin module.
"""

from app.modules.admin.repository import AdminRepository


class AdminService:

    def __init__(self):

        self.repository = AdminRepository()

    async def dashboard(self):

        stats = await self.repository.dashboard_stats()

        recent_users = await self.repository.recent_users()

        recent_payments = await self.repository.recent_payments()

        return {
            "stats": {
                "total_users": stats["users"].count or 0,
                "total_payments": stats["payments"].count or 0,
                "services_sold": stats["services"].count or 0,
            },
            "recent_users": recent_users.data or [],
            "recent_payments": recent_payments.data or [],
        }
