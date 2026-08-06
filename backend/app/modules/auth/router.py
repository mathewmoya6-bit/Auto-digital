# app/modules/auth/router.py
# Auto-D Kenya - Authentication Routes
# ================================================================
# TYPE: MODULE - Authentication API routes

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.core.database import get_supabase
from app.core.security import create_access_token
from app.modules.auth.schemas import (
    LoginRequest, RegisterRequest, TokenResponse, UserResponse
)
from app.modules.auth.service import AuthService

router = APIRouter()
auth_service = AuthService()


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login user and return JWT token."""
    result = await auth_service.login(request.email, request.password)
    return TokenResponse(
        access_token=result["access_token"],
        token_type="bearer",
        expires_in=result["expires_in"]
    )


@router.post("/register")
async def register(request: RegisterRequest):
    """Register a new user."""
    result = await auth_service.register(request.email, request.password, request.full_name)
    return result


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout current user."""
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user information."""
    # The current_user already contains all the user info from the token
    # No need to fetch from database again
    return current_user
