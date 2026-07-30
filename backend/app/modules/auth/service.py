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
        Authenticate user and create access token.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            dict: Access token and expiry
            
        Raises:
            UnauthorizedException: If credentials are invalid
        """
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if not response.user:
                raise UnauthorizedException("Invalid credentials")
            
            access_token = create_access_token(
                data={"sub": response.user.id, "email": response.user.email}
            )
            
            return {
                "access_token": access_token,
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user_id": response.user.id,
                "email": response.user.email
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
            dict: Registration result
            
        Raises:
            ValidationException: If registration fails
        """
        try:
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {"full_name": full_name or email.split("@")[0]}
                }
            })
            
            if not response.user:
                raise ValidationException("Registration failed")
            
            return {
                "message": "User registered successfully",
                "user_id": response.user.id,
                "email": response.user.email
            }
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            raise ValidationException(f"Registration failed: {str(e)}")
    
    async def get_user(self, user_id: str) -> dict:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            dict: User information
            
        Raises:
            UnauthorizedException: If user not found
        """
        try:
            response = self.supabase.auth.get_user(user_id)
            
            if not response.user:
                raise UnauthorizedException("User not found")
            
            return {
                "id": response.user.id,
                "email": response.user.email,
                "full_name": response.user.user_metadata.get("full_name"),
                "created_at": response.user.created_at
            }
            
        except Exception as e:
            logger.error(f"Get user error: {str(e)}")
            raise UnauthorizedException("User not found")
