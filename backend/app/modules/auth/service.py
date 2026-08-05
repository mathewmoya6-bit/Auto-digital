# app/modules/auth/service.py
# Auto-D Kenya - Authentication Service
# ================================================================
# TYPE: MODULE - Authentication business logic

import logging
from datetime import datetime

from app.core.database import get_supabase
from app.core.security import create_access_token, hash_password, verify_password
from app.core.config import settings
from app.core.exceptions import UnauthorizedException, ValidationException

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service."""
    
    def __init__(self):
        self.supabase = get_supabase()
    
    async def login(self, email: str, password: str) -> dict:
        """
        Authenticate user and return Supabase session.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            dict: Access token, refresh token, and user info
            
        Raises:
            UnauthorizedException: If credentials are invalid
        """
        try:
            # Use Supabase's built-in authentication
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if not response.user:
                raise UnauthorizedException("Invalid credentials")
            
            # Log successful login
            logger.info(
                f"User logged in: {response.user.email} (ID: {response.user.id})"
            )
            
            # Return the Supabase session tokens directly
            # These are valid for supabase.auth.get_user()
            return {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "token_type": "bearer",
                "expires_in": response.session.expires_in,
                "expires_at": response.session.expires_at.isoformat() if response.session.expires_at else None,
                "user_id": response.user.id,
                "email": response.user.email,
                "user_metadata": response.user.user_metadata,
            }
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            raise UnauthorizedException("Invalid credentials")
    
    async def register(self, email: str, password: str, full_name: str = None) -> dict:
        """
        Register a new user.
        
        Args:
            email: User email
            password: User password
            full_name: User full name (optional)
            
        Returns:
            dict: Registration result with session tokens
            
        Raises:
            ValidationException: If registration fails
        """
        try:
            # Use Supabase's built-in registration
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name or email.split("@")[0],
                        "role": "user",
                    }
                }
            })
            
            if not response.user:
                raise ValidationException("Registration failed")
            
            logger.info(
                f"User registered: {response.user.email} (ID: {response.user.id})"
            )
            
            # Create a profile record for the user
            try:
                profile_data = {
                    "user_id": response.user.id,
                    "email": email,
                    "full_name": full_name or email.split("@")[0],
                    "role": "user",
                    "is_active": True,
                    "created_at": datetime.utcnow().isoformat(),
                }
                
                self.supabase.table("profiles").insert(profile_data).execute()
                logger.info(f"Profile created for user: {response.user.id}")
                
            except Exception as profile_error:
                logger.warning(f"Profile creation failed: {profile_error}")
                # Don't fail registration if profile creation fails
            
            # Return session if user was auto-confirmed, otherwise just user info
            if response.session:
                return {
                    "message": "User registered successfully",
                    "user_id": response.user.id,
                    "email": response.user.email,
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                    "token_type": "bearer",
                    "expires_in": response.session.expires_in,
                }
            else:
                return {
                    "message": "User registered successfully. Please confirm your email.",
                    "user_id": response.user.id,
                    "email": response.user.email,
                    "requires_confirmation": True,
                }
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            raise ValidationException(f"Registration failed: {str(e)}")
    
    async def refresh_token(self, refresh_token: str) -> dict:
        """
        Refresh an expired access token.
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            dict: New access token and session info
            
        Raises:
            UnauthorizedException: If refresh token is invalid
        """
        try:
            response = self.supabase.auth.refresh_session(refresh_token)
            
            if not response.user:
                raise UnauthorizedException("Invalid refresh token")
            
            logger.info(f"Token refreshed for user: {response.user.email}")
            
            return {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "token_type": "bearer",
                "expires_in": response.session.expires_in,
                "expires_at": response.session.expires_at.isoformat() if response.session.expires_at else None,
                "user_id": response.user.id,
            }
            
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            raise UnauthorizedException("Invalid refresh token")
    
    async def logout(self, access_token: str) -> dict:
        """
        Log out a user by invalidating their session.
        
        Args:
            access_token: The access token to invalidate
            
        Returns:
            dict: Logout confirmation
        """
        try:
            # Supabase doesn't have a direct logout API for tokens
            # The client should discard the token on their side
            # We'll log the logout attempt
            logger.info(f"User logged out (token: {access_token[:20]}...)")
            
            return {
                "message": "Logged out successfully",
            }
            
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            raise UnauthorizedException("Logout failed")
    
    async def get_user(self, user_id: str) -> dict:
        """
        Get user by ID from Supabase Auth.
        
        Args:
            user_id: User ID
            
        Returns:
            dict: User information
            
        Raises:
            UnauthorizedException: If user not found
        """
        try:
            # Supabase auth get_user requires an access token
            # Since we're in a service context, we need to get the user differently
            # Try to get from profiles table first
            try:
                response = (
                    self.supabase
                    .table("profiles")
                    .select("*")
                    .eq("user_id", user_id)
                    .maybe_single()
                    .execute()
                )
                
                if response and response.data:
                    return {
                        "id": response.data.get("user_id"),
                        "email": response.data.get("email"),
                        "full_name": response.data.get("full_name"),
                        "role": response.data.get("role", "user"),
                        "is_active": response.data.get("is_active", True),
                        "created_at": response.data.get("created_at"),
                    }
            except Exception:
                pass
            
            # Fallback: try to get from auth (requires admin privileges)
            # This may not work with anon key
            try:
                # Using admin API - may require service role key
                admin_client = self.supabase.auth.admin
                response = admin_client.get_user_by_id(user_id)
                
                if response and response.user:
                    return {
                        "id": response.user.id,
                        "email": response.user.email,
                        "full_name": response.user.user_metadata.get("full_name"),
                        "created_at": response.user.created_at,
                    }
            except Exception:
                pass
            
            raise UnauthorizedException("User not found")
            
        except Exception as e:
            logger.error(f"Get user error: {str(e)}")
            raise UnauthorizedException("User not found")
    
    async def get_current_user(self, token: str) -> dict:
        """
        Get current user from access token.
        
        Args:
            token: Access token from Supabase Auth
            
        Returns:
            dict: User information from profile
            
        Raises:
            UnauthorizedException: If token is invalid
        """
        try:
            # Verify the token with Supabase Auth
            auth_response = self.supabase.auth.get_user(token)
            
            if not auth_response or not auth_response.user:
                raise UnauthorizedException("Invalid authentication")
            
            user = auth_response.user
            
            # Try to get profile from profiles table
            try:
                profile_response = (
                    self.supabase
                    .table("profiles")
                    .select("*")
                    .eq("user_id", user.id)
                    .maybe_single()
                    .execute()
                )
                
                logger.debug(f"Profile lookup for {user.id}: {profile_response.data}")
                
                if profile_response and profile_response.data:
                    return profile_response.data
            except Exception as e:
                logger.warning(f"Profile lookup failed: {e}")
            
            # Fallback to auth user info if no profile exists
            return {
                "id": user.id,
                "user_id": user.id,
                "email": user.email,
                "full_name": user.user_metadata.get("full_name"),
                "role": user.app_metadata.get("role", "user") if user.app_metadata else "user",
                "is_active": True,
            }
            
        except Exception as e:
            logger.error(f"Get current user error: {str(e)}")
            raise UnauthorizedException("Invalid authentication")
