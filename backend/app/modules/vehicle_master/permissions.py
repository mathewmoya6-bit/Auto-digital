"""
Auto-D Kenya
Vehicle Master Permissions

Authorization layer for Vehicle Master Admin operations.
"""

import logging
from typing import Optional

from fastapi import HTTPException, status

from app.core.database import get_supabase


logger = logging.getLogger(__name__)


class VehicleMasterPermission:

    """
    Vehicle Master permission checker.
    """


    def __init__(self):
        self.db = get_supabase()



    async def has_permission(
        self,
        user_id: str,
        permission: str
    ) -> bool:
        """
        Check whether user has permission.
        """

        try:

            response = (
                self.db
                .table("role_permissions")
                .select(
                    """
                    permission_id,
                    permissions(
                        name
                    ),
                    user_roles!inner(
                        user_id
                    )
                    """
                )
                .eq(
                    "user_roles.user_id",
                    user_id
                )
                .execute()
            )


            permissions = response.data or []


            for item in permissions:

                permission_data = (
                    item.get("permissions")
                    or {}
                )

                if (
                    permission_data.get("name")
                    == permission
                ):
                    return True


            return False


        except Exception as e:

            logger.error(
                f"Permission check failed: {e}"
            )

            return False



    async def require_permission(
        self,
        user_id:str,
        permission:str
    ):
        """
        Raise exception if permission denied.
        """

        allowed = await self.has_permission(
            user_id,
            permission
        )


        if not allowed:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Insufficient permission "
                    f"required: {permission}"
                )
            )


        return True



# ==========================================================
# VEHICLE MASTER PERMISSIONS
# ==========================================================


VEHICLE_MASTER_PERMISSIONS = {

    "VIEW":
        "vehicle_master.view",

    "CREATE":
        "vehicle_master.create",

    "UPDATE":
        "vehicle_master.update",

    "UPDATE_PRICE":
        "vehicle_master.update_price",

    "DELETE":
        "vehicle_master.delete",

    "IMPORT":
        "vehicle_master.import",

    "EXPORT":
        "vehicle_master.export",

}
