"""
Auto-D Kenya
Vehicle Master Permissions
"""

import logging
from typing import Optional

from fastapi import HTTPException, Depends, status
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)


async def require_vehicle_master_access(
    current_user: dict = Depends(get_current_user),
) -> bool:
    """
    Require vehicle master admin access.
    
    Checks:
    1. User is authenticated
    2. User has admin role or vehicle_master_admin permission
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    
    # Check if user has admin role
    user_roles = current_user.get("roles", [])
    if "admin" in user_roles or "super_admin" in user_roles:
        return True
    
    # Check for specific permission
    permissions = current_user.get("permissions", [])
    if "vehicle_master_admin" in permissions:
        return True
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions for vehicle master access",
    )


async def require_vehicle_edit_access(
    current_user: dict = Depends(get_current_user),
) -> bool:
    """
    Require vehicle edit permissions.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    
    user_roles = current_user.get("roles", [])
    if "admin" in user_roles or "super_admin" in user_roles:
        return True
    
    permissions = current_user.get("permissions", [])
    if "vehicle_edit" in permissions or "vehicle_master_admin" in permissions:
        return True
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions for vehicle editing",
    )


async def require_vehicle_view_access(
    current_user: dict = Depends(get_current_user),
) -> bool:
    """
    Require vehicle view permissions (read-only access).
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    
    user_roles = current_user.get("roles", [])
    if "admin" in user_roles or "super_admin" in user_roles:
        return True
    
    permissions = current_user.get("permissions", [])
    if "vehicle_view" in permissions or "vehicle_master_admin" in permissions:
        return True
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions for vehicle viewing",
    )


# Alias for backward compatibility
require_vehicle_master_permission = require_vehicle_master_access
