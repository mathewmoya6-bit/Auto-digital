"""
Auto-D Kenya - Admin Service
================================================
TYPE: MODULE - Business Logic
"""

import logging
from typing import Dict, Any

from app.modules.admin.repository import AdminRepository

logger = logging.getLogger(__name__)


class AdminService:
    """Admin business logic."""

    def __init__(self):
        self.repository = AdminRepository()

    # -------------------------------------------------------------
    # Dashboard
    # -------------------------------------------------------------

    async def dashboard(self) -> Dict[str, Any]:
        """Return dashboard statistics."""
        return await self.repository.get_dashboard_stats()

    # -------------------------------------------------------------
    # Users
    # -------------------------------------------------------------

    async def get_users(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Return paginated users."""
        return await self.repository.get_users(
            limit=limit,
            offset=offset,
        )

    async def get_user(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """Return a single user."""
        return await self.repository.get_user(user_id)

    async def delete_user(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """Delete a user."""
        return await self.repository.delete_user(user_id)

    # -------------------------------------------------------------
    # Payments
    # -------------------------------------------------------------

    async def get_payments(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Return paginated payments."""
        return await self.repository.get_payments(
            limit=limit,
            offset=offset,
        )

    async def get_payment(
        self,
        payment_id: str,
    ) -> Dict[str, Any]:
        """Return payment details."""
        return await self.repository.get_payment(payment_id)

    # -------------------------------------------------------------
    # Services
    # -------------------------------------------------------------

    async def get_services(self) -> Dict[str, Any]:
        """Return all services."""
        return await self.repository.get_services()

    async def update_service(
        self,
        service_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update service."""
        return await self.repository.update_service(
            service_id,
            payload,
        )

    # -------------------------------------------------------------
    # Reports
    # -------------------------------------------------------------

    async def revenue_report(
        self,
        start_date=None,
        end_date=None,
    ) -> Dict[str, Any]:
        """Generate revenue report."""
        return await self.repository.revenue_report(
            start_date,
            end_date,
        )

    # -------------------------------------------------------------
    # Health
    # -------------------------------------------------------------

    async def health(self) -> Dict[str, Any]:
        """Return module health."""
        return await self.repository.health()
