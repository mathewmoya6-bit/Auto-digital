# app/core/dependencies.py
"""
Auto-D Kenya - Dependencies
Clean production-ready dependency module.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.database import get_supabase

logger = logging.getLogger(__name__)
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    token = credentials.credentials
    secrets = [
        getattr(settings, "SUPABASE_JWT_SECRET", None),
        getattr(settings, "JWT_SECRET_KEY", None),
    ]
    payload = None
    for secret in filter(None, secrets):
        try:
            payload = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
            break
        except jwt.InvalidTokenError:
            pass

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    res = get_supabase().table("users").select("*").eq("id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=401, detail="User not found")

    user = res.data[0]
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Inactive user")
    return user


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    return current_user


async def get_current_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not (
        current_user.get("is_admin")
        or current_user.get("role") in ("admin", "super_admin")
    ):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user


async def get_current_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_admin),
):
    return current_user


async def get_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_admin),
):
    return current_user


async def get_current_super_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_admin),
):
    if current_user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin required")
    return current_user


async def get_db():
    yield get_supabase()


def require_roles(roles: List[str]):
    async def checker(user: Dict[str, Any] = Depends(get_current_user)):
        if user.get("is_admin") or user.get("role") == "super_admin":
            return user
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user
    return checker


def require_permission(permission: str):
    async def checker(user: Dict[str, Any] = Depends(get_current_user)):
        if user.get("is_admin") or user.get("role") in ("admin","super_admin"):
            return user
        resp = get_supabase().table("user_permissions").select("permission").eq(
            "user_id", user["id"]
        ).execute()
        perms = [p["permission"] for p in resp.data]
        if permission not in perms:
            raise HTTPException(status_code=403, detail="Permission denied")
        return user
    return checker


def get_pagination_params(page:int=1, limit:int=20):
    page=max(page,1)
    limit=min(max(limit,1),100)
    return {"page":page,"limit":limit,"offset":(page-1)*limit}


def create_access_token(data:Dict[str,Any], expires_delta:Optional[timedelta]=None):
    payload=data.copy()
    payload["exp"]=datetime.utcnow()+(expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_token(token:str):
    return jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


__all__=[
"security","get_current_user","get_current_active_user","get_current_admin",
"get_current_admin_user","get_admin_user","get_current_super_admin_user",
"get_db","require_roles","require_permission","get_pagination_params",
"create_access_token","verify_token"
]
