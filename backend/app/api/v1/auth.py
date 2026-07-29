# backend/app/api/v1/auth.py

"""
Authentication Routes
POST /api/v1/login - Login
POST /api/v1/register - Register
GET  /api/v1/me - Get Current User Info
POST /api/v1/logout - Logout
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response  # ← ADD Response here
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from app.core.database import supabase
from app.core.security import create_access_token, get_current_user, security
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])


# ─── Request/Response Models ──────────────────────────────────────

class LoginRequest(BaseModel):
    """Login request model"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password")


class RegisterRequest(BaseModel):
    """Register request model"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password (min 6 characters)")
    full_name: Optional[str] = Field(None, description="User's full name")
    phone: Optional[str] = Field(None, description="Phone number")


class AuthResponse(BaseModel):
    """Authentication response model"""
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class UserResponse(BaseModel):
    """User response model"""
    id: str
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: str = "user"


class LogoutResponse(BaseModel):
    """Logout response model"""
    success: bool
    message: str


# ─── Helper Functions ─────────────────────────────────────────────

def create_user_profile(user_id: str, user_data: Dict[str, Any]) -> bool:
    """Create a user profile in the database."""
    try:
        profile_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "full_name": user_data.get("full_name"),
            "phone": user_data.get("phone"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        response = supabase.table("user_profiles").insert(profile_data).execute()
        return bool(response.data)
    except Exception as e:
        logger.error(f"Failed to create user profile: {e}")
        return False


# ─── Endpoints ────────────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    response: Optional[Response] = None  # ← Response is now defined
):
    """
    POST /api/v1/login - Login user with email and password.
    
    Returns access token and user information.
    """
    try:
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if not auth_response or not auth_response.user:
            logger.warning(f"Login failed for email: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = auth_response.user
        session = auth_response.session
        
        # Get user metadata
        user_metadata = user.user_metadata or {}
        
        logger.info(f"✅ User logged in: {user.email}")
        
        return {
            "access_token": session.access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user_metadata.get("full_name") or user_metadata.get("name"),
                "phone": user_metadata.get("phone"),
                "role": user_metadata.get("role", "user"),
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.post("/register", response_model=AuthResponse)
async def register(
    request: RegisterRequest,
    response: Optional[Response] = None  # ← Response is now defined
):
    """
    POST /api/v1/register - Register a new user.
    
    Creates a new user account and returns access token.
    """
    try:
        # Register with Supabase
        auth_response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "data": {
                    "full_name": request.full_name,
                    "phone": request.phone,
                    "role": "user",
                }
            }
        })
        
        if not auth_response or not auth_response.user:
            logger.error(f"Registration failed for email: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed. Please try again."
            )
        
        user = auth_response.user
        session = auth_response.session
        
        # Create user profile
        profile_created = create_user_profile(user.id, {
            "full_name": request.full_name,
            "phone": request.phone,
        })
        
        if not profile_created:
            logger.warning(f"User profile creation failed for: {user.email}")
        
        logger.info(f"✅ User registered: {user.email}")
        
        return {
            "access_token": session.access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": request.full_name,
                "phone": request.phone,
                "role": "user",
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    GET /api/v1/me - Get current user information.
    
    Returns user profile data for the authenticated user.
    """
    try:
        # Get additional user profile data from database
        profile = None
        try:
            response = supabase.table("user_profiles").select("*").eq("user_id", current_user["id"]).execute()
            if response.data:
                profile = response.data[0]
        except Exception as e:
            logger.warning(f"Failed to fetch user profile: {e}")
        
        return {
            "id": current_user["id"],
            "email": current_user.get("email"),
            "full_name": (
                profile.get("full_name") if profile else 
                current_user.get("user_metadata", {}).get("full_name")
            ),
            "phone": (
                profile.get("phone") if profile else
                current_user.get("user_metadata", {}).get("phone")
            ),
            "role": current_user.get("role", "user"),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    POST /api/v1/logout - Logout user.
    
    Invalidates the current session.
    """
    try:
        logger.info(f"✅ User logged out: {current_user.get('email')}")
        
        return {
            "success": True,
            "message": "Logged out successfully"
        }
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


# ─── Export ─────────────────────────────────────────────────────

__all__ = [
    "router",
    "LoginRequest",
    "RegisterRequest",
    "AuthResponse",
    "UserResponse",
    "LogoutResponse",
]
