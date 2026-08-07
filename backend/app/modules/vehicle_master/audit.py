"""
Auto-D Kenya
Vehicle Master Audit Service

Tracks all vehicle master changes.
"""

import logging
from typing import Any, Dict, Optional, List

from fastapi.concurrency import run_in_threadpool

from app.core.database import get_supabase


logger = logging.getLogger(__name__)


class AuditService:
    """
    Vehicle Master Audit Manager.
    """


    def __init__(self):
        self.db = get_supabase()



    async def _run(self, fn):
        """
        Execute blocking Supabase
        calls asynchronously.
        """

        return await run_in_threadpool(fn)



    # ======================================================
    # LOG UPDATE
    # ======================================================

    async def log_update(
        self,
        variant_id: int,
        changes: Dict[str, Any],
        action: str,
        old_data: Optional[Dict[str, Any]] = None,
        new_data: Optional[Dict[str, Any]] = None,
        changed_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Store vehicle update audit record.
        """

        try:

            payload = {

                "vehicle_id":
                    variant_id,

                "action":
                    action,

                "old_data":
                    old_data or {},

                "new_data":
                    new_data or changes,

                "changed_by":
                    changed_by,

            }


            response = await self._run(
                lambda:
                self.db
                .table(
                    "vehicle_master_audit"
                )
                .insert(payload)
                .execute()
            )


            return response.data[0] if response.data else {}


        except Exception as e:

            logger.error(
                f"Audit logging failed: {e}"
            )

            # Audit failure should not
            # break vehicle operations
            return {}



    # ======================================================
    # LOG BULK ACTION
    # ======================================================

    async def log_bulk_action(
        self,
        action: str,
        count: int,
        details: Dict[str, Any],
        changed_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Store bulk operation audit.
        """

        try:

            payload = {

                "vehicle_id": 0,

                "action":
                    action,

                "old_data":
                    {},

                "new_data":
                    {
                        "count": count,
                        "details": details
                    },

                "changed_by":
                    changed_by,

            }


            response = await self._run(
                lambda:
                self.db
                .table(
                    "vehicle_master_audit"
                )
                .insert(payload)
                .execute()
            )


            return response.data[0] if response.data else {}


        except Exception as e:

            logger.error(
                f"Bulk audit failed: {e}"
            )

            return {}



    # ======================================================
    # GET VEHICLE HISTORY
    # ======================================================

    async def get_history(
        self,
        variant_id:int,
        limit:int=50
    ) -> List[Dict[str,Any]]:
        """
        Get audit history for vehicle.
        """

        try:

            response = await self._run(
                lambda:
                self.db
                .table(
                    "vehicle_master_audit"
                )
                .select("*")
                .eq(
                    "vehicle_id",
                    variant_id
                )
                .order(
                    "created_at",
                    desc=True
                )
                .limit(
                    limit
                )
                .execute()
            )


            return response.data or []


        except Exception as e:

            logger.error(
                f"History lookup failed: {e}"
            )

            return []
