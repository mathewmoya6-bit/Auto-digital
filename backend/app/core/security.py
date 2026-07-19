# backend/app/core/security.py
"""
Security / Authentication
Verifies Supabase access tokens and resolves the current user.

Fix: previously this manually decoded JWTs with PyJWT using a fixed
`algorithms=["HS256"]` allow-list. If the Supabase project issues tokens
signed with a different algorithm (e.g. ES256, after a signing-key
migration), PyJWT raises: "The specified alg value is not allowed",
which was being caught and reported as a generic 401 "session expired".

This version verifies the token via supabase.auth.get_user(token) instead,
which lets Supabase's own SDK handle whatever signing algorithm the
project is actually using — no JWT_ALGORITHM env var needed at all.
"""

import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from starlette.concurrency import run_in_threadpool

from app.core.database import supabase

logger = logging.getLogger(__name__)

# tokenUrl is not actually used for a real login flow here since Supabase
# issues the tokens client-side, but FastAPI's OAuth2PasswordBearer needs
# a value; it's only used to build the Swagger "Authorize" UI.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    FastAPI dependency: verifies the bearer token against Supabase and
    returns the authenticated user as a dict. Raises 401 on any failure.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # supabase-py's auth.get_user is synchronous under the hood;
        # run it in a threadpool so it doesn't block the event loop.
        response = await run_in_threadpool(supabase.auth.get_user, token)
    except Exception as e:
        logger.warning(f"Supabase token verification failed: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = getattr(response, "user", None)
    if not user:
        logger.warning("Supabase token verification returned no user")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Normalize into a plain dict for the rest of the app.
    # user.id, user.email, user.user_metadata, user.app_metadata are the
    # typical fields available on the gotrue User object.
    user_dict = {
        "id": user.id,
        "email": getattr(user, "email", None),
        "role": (getattr(user, "app_metadata", {}) or {}).get("role", "user"),
        "user_metadata": getattr(user, "user_metadata", {}) or {},
        "app_metadata": getattr(user, "app_metadata", {}) or {},
    }

    return user_dict


async def get_current_user_optional(token: str = Depends(oauth2_scheme)) -> dict | None:
    """
    Like get_current_user, but returns None instead of raising when no
    valid token is present. Use for endpoints that behave differently for
    logged-in vs anonymous users but don't require auth.
    """
    if not token:
        return None
    try:
        return await get_current_user(token)
    except HTTPException:
        return None


def verify_api_key(x_api_key: str | None = None) -> bool:
    """
    Placeholder for admin/service API key verification, if your app uses
    a separate API key header for admin endpoints (as referenced in
    mpesa admin routes). Wire this up to a real header dependency + a
    secret comparison against settings if you need it enforced.
    """
    # Example real implementation once you have a secret configured:
    #
    # from app.core.config import settings
    # if x_api_key != settings.ADMIN_API_KEY:
    #     raise HTTPException(status_code=403, detail="Invalid API key")
    # return True
    return True
