from fastapi import Depends, HTTPException

from app.core.dependencies import get_current_user


async def require_admin(
    current_user: dict = Depends(get_current_user),
):
    role = (
        current_user.get("app_metadata", {}).get("role")
        or current_user.get("user_metadata", {}).get("role")
        or current_user.get("account_type")
    )

    if role not in ["admin", "super_admin", "staff"]:
        raise HTTPException(403, "Admin access required")

    return current_user
