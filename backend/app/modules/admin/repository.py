"""
Auto-D Kenya - Admin Repository
================================================
Handles all Supabase database operations.
"""

import logging

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class AdminRepository:

    def __init__(self):
        self.db = get_supabase()

    # --------------------------------------------------

    async def dashboard_stats(self):

        return {
            "users": self.db.table("profiles").select("*", count="exact").execute(),
            "payments": self.db.table("payments").select("*", count="exact").execute(),
            "services": self.db.table("services").select("*", count="exact").execute(),
        }

    # --------------------------------------------------

    async def recent_users(self, limit: int = 10):

        return (
            self.db.table("profiles")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

    # --------------------------------------------------

    async def recent_payments(self, limit: int = 10):

        return (
            self.db.table("payments")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

    # --------------------------------------------------

    async def services(self):

        return (
            self.db.table("services")
            .select("*")
            .order("display_order")
            .execute()
        )
