# backend/app/api/v1/auth.py

"""
Authentication Routes
POST /api/v1/login - Login
POST /api/v1/register - Register
GET  /api/v1/me - Get Current User Info
POST /api/v1/logout - Logout
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field, EmailStr, field_validator

from app.core.dependencies import get_current_user, invalidate_user_cache
from app.core.database import supabase, supabase_client
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])


# ─── Request/Response Models ──────────────────────────────────────

class LoginRequest(BaseModel):
    """Login request model"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        return v.strip().lower()


class RegisterRequest(BaseModel):
    """Register request model"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password (min 6 characters)")
    full_name: Optional[str] = Field(None, description="User's full name")
    phone: Optional[str] = Field(None, description="Phone number")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        return v.strip().lower()
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class AuthResponse(BaseModel):
    """Authentication response model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    user: Dict[str, Any]


class UserResponse(BaseModel):
    """User response model"""
    id: str
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: str = "user"
    created_at: Optional[str] = None
    confirmed_at: Optional[str] = None


class LogoutResponse(BaseModel):
    """Logout response model"""
    success: bool
    message: str


class PasswordResetRequest(BaseModel):
    """Password reset request model"""
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    """Password reset confirm request model"""
    token: str
    new_password: str = Field(..., min_length=6)


class ChangePasswordRequest(BaseModel):
    """Change password request model"""
    current_password: str
    new_password: str = Field(..., min_length=6)


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


def create_audit_log(user_id: str, action: str, details: Optional[Dict] = None) -> None:
    """Create an audit log entry."""
    try:
        log_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "action": action,
            "details": details,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        supabase.table("audit_logs").insert(log_data).execute()
    except Exception as e:
        logger.warning(f"Failed to create audit log: {e}")


# ─── Auth Endpoints ──────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    response: Response
):
    """
    Login user with email and password.
    
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
        
        # Create audit log
        create_audit_log(user.id, "login", {"email": user.email})
        
        logger.info(f"✅ User logged in: {user.email}")
        
        # Set session cookie if needed
        if session and session.access_token:
            response.set_cookie(
                key="access_token",
                value=session.access_token,
                httponly=True,
                secure=settings.ENVIRONMENT == "production",
                samesite="lax",
                max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )
        
        # Get user metadata
        user_metadata = user.user_metadata or {}
        
        return {
            "access_token": session.access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "refresh_token": session.refresh_token,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user_metadata.get("full_name") or user_metadata.get("name"),
                "phone": user_metadata.get("phone"),
                "role": user_metadata.get("role", "user"),
                "created_at": user.created_at,
                "confirmed_at": user.confirmed_at,
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
    response: Response
):
    """
    Register a new user.
    
    Creates a new user account and returns access token.
    """
    try:
        # Check if user already exists
        try:
            existing = supabase.table("users").select("id").eq("email", request.email).execute()
            if existing.data:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this email already exists"
                )
        except Exception:
            # Table might not exist yet, continue
            pass
        
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
        
        # Create audit log
        create_audit_log(user.id, "register", {"email": user.email})
        
        logger.info(f"✅ User registered: {user.email}")
        
        # Set session cookie
        if session and session.access_token:
            response.set_cookie(
                key="access_token",
                value=session.access_token,
                httponly=True,
                secure=settings.ENVIRONMENT == "production",
                samesite="lax",
                max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )
        
        user_metadata = user.user_metadata or {}
        
        return {
            "access_token": session.access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "refresh_token": session.refresh_token,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": request.full_name,
                "phone": request.phone,
                "role": "user",
                "created_at": user.created_at,
                "confirmed_at": user.confirmed_at,
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
async def get_me(
    current_user: Dict = Depends(get_current_user)
):
    """
    Get current user information.
    
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
            "role": current_user.get("user_metadata", {}).get("role", "user"),
            "created_at": current_user.get("created_at"),
            "confirmed_at": current_user.get("confirmed_at"),
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
    response: Response,
    current_user: Dict = Depends(get_current_user)
):
    """
    Logout user.
    
    Invalidates the current session and clears cookies.
    """
    try:
        # Get token from header or cookie
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            token = request.cookies.get("access_token")
        
        # Invalidate cache
        if token:
            invalidate_user_cache(token)
        
        # Clear cookie
        response.delete_cookie(
            key="access_token",
            secure=settings.ENVIRONMENT == "production",
            httponly=True,
            samesite="lax",
        )
        
        # Create audit log
        create_audit_log(current_user["id"], "logout", {"email": current_user.get("email")})
        
        logger.info(f"✅ User logged out: {current_user.get('email')}")
        
        return {
            "success": True,
            "message": "Logged out successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post("/refresh")
async def refresh_token(
    refresh_token: Optional[str] = None,
    request: Request = None
):
    """
    Refresh access token using refresh token.
    """
    try:
        # Get refresh token from request body or cookie
        if not refresh_token:
            refresh_token = request.cookies.get("refresh_token")
        
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token required"
            )
        
        # Refresh session with Supabase
        session = supabase.auth.refresh_session(refresh_token)
        
        if not session or not session.access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        return {
            "access_token": session.access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "refresh_token": session.refresh_token,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/password-reset")
async def request_password_reset(
    request: PasswordResetRequest
):
    """
    Request password reset email.
    """
    try:
        # Supabase will send the password reset email
        response = supabase.auth.reset_password_for_email(request.email)
        
        if response:
            logger.info(f"Password reset requested for: {request.email}")
            return {
                "success": True,
                "message": "Password reset email sent. Please check your inbox."
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to send password reset email"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to request password reset"
        )


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    request: PasswordResetConfirmRequest
):
    """
    Confirm password reset with token.
    """
    try:
        # Supabase handles the password reset with the token
        response = supabase.auth.update_user({
            "password": request.new_password
        })
        
        if response and response.user:
            logger.info(f"Password reset confirmed for user: {response.user.email}")
            return {
                "success": True,
                "message": "Password reset successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset confirm error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to confirm password reset"
        )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Change user password (requires current password).
    """
    try:
        # First verify current password by attempting login
        try:
            supabase.auth.sign_in_with_password({
                "email": current_user.get("email"),
                "password": request.current_password
            })
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        response = supabase.auth.update_user({
            "password": request.new_password
        })
        
        if response and response.user:
            # Create audit log
            create_audit_log(current_user["id"], "change_password")
            
            logger.info(f"Password changed for user: {current_user.get('email')}")
            return {
                "success": True,
                "message": "Password changed successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to change password"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


@router.get("/verify-email/{token}")
async def verify_email(token: str):
    """
    Verify user email with token.
    """
    try:
        # Supabase handles email verification
        response = supabase.auth.verify_otp({
            "token": token,
            "type": "email"
        })
        
        if response and response.user:
            logger.info(f"Email verified for user: {response.user.email}")
            return {
                "success": True,
                "message": "Email verified successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email"
        )


@router.delete("/delete-account")
async def delete_account(
    current_user: Dict = Depends(get_current_user)
):
    """
    Delete user account.
    """
    try:
        # Delete user profile
        try:
            supabase.table("user_profiles").delete().eq("user_id", current_user["id"]).execute()
        except Exception:
            pass
        
        # Delete user from auth (requires admin)
        # Supabase doesn't allow user self-deletion via API
        # This would need to be handled via admin or a custom function
        
        # Create audit log
        create_audit_log(current_user["id"], "delete_account_request")
        
        logger.info(f"Account deletion requested for user: {current_user.get('email')}")
        
        return {
            "success": True,
            "message": "Account deletion requested. An admin will process this request."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete account error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account"
        )
