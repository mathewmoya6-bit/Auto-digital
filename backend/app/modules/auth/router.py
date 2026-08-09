# app/modules/auth/router.py
# Auto-D Kenya - Authentication Routes
# ================================================================
# TYPE: MODULE - Authentication API routes

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.database import get_supabase
from app.modules.auth.schemas import (
    LoginRequest, RegisterRequest, TokenResponse, UserResponse
)
from app.modules.auth.service import AuthService

router = APIRouter()
auth_service = AuthService()

# ── Cookie config ────────────────────────────────────────────────
# Must match ACCESS_COOKIE_NAME in app/core/dependencies.py
ACCESS_COOKIE_NAME = "sb_access_token"
REFRESH_COOKIE_NAME = "sb_refresh_token"

# In production this MUST be True (cookie only sent over HTTPS).
COOKIE_SECURE = settings.ENVIRONMENT == "production"
COOKIE_SAMESITE = "lax"  # same-domain frontend + API confirmed


def _set_session_cookies(response: Response, access_token: str, refresh_token: str, expires_in: int):
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=expires_in,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=60 * 60 * 24 * 30,  # 30 days
        path="/",
    )


def _clear_session_cookies(response: Response):
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/")


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, response: Response):
    """Login user, return JWT token, and set HttpOnly session cookies."""
    result = await auth_service.login(request.email, request.password)

    _set_session_cookies(
        response,
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        expires_in=result["expires_in"],
    )

    return TokenResponse(
        access_token=result["access_token"],
        token_type="bearer",
        expires_in=result["expires_in"]
    )


@router.post("/register")
async def register(request: RegisterRequest, response: Response):
    """Register a new user. Sets session cookies if auto-confirmed."""
    result = await auth_service.register(
        request.email,
        request.password,
        request.full_name,
        request.account_type,
    )

    if result.get("access_token") and result.get("refresh_token"):
        _set_session_cookies(
            response,
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            expires_in=result.get("expires_in", 3600),
        )

    return result


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response):
    """Refresh the session using the refresh token cookie."""
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token found",
        )

    result = await auth_service.refresh_token(refresh_token)

    _set_session_cookies(
        response,
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        expires_in=result["expires_in"],
    )

    return TokenResponse(
        access_token=result["access_token"],
        token_type="bearer",
        expires_in=result["expires_in"]
    )


@router.post("/logout")
async def logout(response: Response, current_user: dict = Depends(get_current_user)):
    """Logout current user and clear session cookies."""
    _clear_session_cookies(response)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user information."""
    return current_user
