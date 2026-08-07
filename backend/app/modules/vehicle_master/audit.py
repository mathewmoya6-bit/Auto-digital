"""
Auto-D Kenya
Vehicle Master Audit Service
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import UUID

from app.core.database import get_supabase
from fastapi.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)


class AuditService:
    """Audit logging for vehicle master operations."""

    def __init__(self):
        self.db = get_supabase()

    async def _run(self, fn):
        return await run_in_threadpool(fn)

    async def log_update(
        self,
        variant_id: int,
        changes: Dict[str, Any],
        action: str = "update",
        user_id: Optional[UUID] = None,
        user_email: Optional[str] = None,
    ) -> bool:
        """Log a vehicle update."""
        try:
            data = {
                "variant_id": variant_id,
                "action": action,
                "changes": changes,
                "user_id": str(user_id) if user_id else None,
                "user_email": user_email,
                "created_at": datetime.utcnow().isoformat(),
            }
            
            response = await self._run(
                lambda: self.db.table("vehicle_audit_logs")
                .insert(data)
                .execute()
            )
            
            return response.data is not None and len(response.data) > 0
        except Exception as e:
            logger.error(f"Error logging audit for variant {variant_id}: {e}")
            return False

    async def log_bulk_action(
        self,
        action: str,
        count: int,
        details: Dict[str, Any],
        user_id: Optional[UUID] = None,
        user_email: Optional[str] = None,
    ) -> bool:
        """Log a bulk action."""
        try:
            data = {
                "action": action,
                "count": count,
                "details": details,
                "user_id": str(user_id) if user_id else None,
                "user_email": user_email,
                "created_at": datetime.utcnow().isoformat(),
            }
            
            response = await self._run(
                lambda: self.db.table("vehicle_audit_logs")
                .insert(data)
                .execute()
            )
            
            return response.data is not None and len(response.data) > 0
        except Exception as e:
            logger.error(f"Error logging bulk action: {e}")
            return False

    async def get_audit_logs(
        self,
        variant_id: Optional[int] = None,
        action: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get audit logs with filters."""
        try:
            query = self.db.table("vehicle_audit_logs").select("*")
            
            if variant_id:
                query = query.eq("variant_id", variant_id)
            if action:
                query = query.eq("action", action)
            
            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
            
            response = await self._run(lambda: query.execute())
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching audit logs: {e}")
            return []

    async def get_vehicle_history(self, variant_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get full history for a specific vehicle."""
        return await self.get_audit_logs(variant_id=variant_id, limit=limit)
