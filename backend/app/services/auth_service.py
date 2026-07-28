"""
Auth Service - Business logic for authentication and authorization
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import bcrypt
import jwt
import os
import re

from app.core.config import settings
from app.core.database import supabase

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication and authorization"""
    
    def __init__(self):
        self.jwt_secret = settings.JWT_SECRET
        self.jwt_algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
    
    # ─── Password Management ──────────────────────────────────────────
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash"""
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """Validate password strength"""
        issues = []
        
        if len(password) < 8:
            issues.append("Password must be at least 8 characters long")
        if not re.search(r'[A-Z]', password):
            issues.append("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', password):
            issues.append("Password must contain at least one lowercase letter")
        if not re.search(r'\d', password):
            issues.append("Password must contain at least one number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            issues.append("Password must contain at least one special character")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "strength": "strong" if len(issues) == 0 else "medium" if len(issues) <= 2 else "weak"
        }
    
    # ─── JWT Token Management ─────────────────────────────────────────
    
    def create_access_token(self, user_id: str, email: str, extra_data: Optional[Dict] = None) -> str:
        """Create a JWT access token"""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        if extra_data:
            payload.update(extra_data)
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create a JWT refresh token"""
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def decode_token(self, token: str) -> Optional[Dict]:
        """Decode and validate a JWT token"""
        try:
            return jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict]:
        """Refresh an access token using a refresh token"""
        payload = self.decode_token(refresh_token)
        if not payload:
            return None
        
        if payload.get("type") != "refresh":
            logger.warning("Invalid token type for refresh")
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # Get user details
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        # Create new access token
        access_token = self.create_access_token(
            user_id=user_id,
            email=user.get("email", ""),
            extra_data={
                "role": user.get("role", "user"),
                "first_name": user.get("first_name", ""),
                "last_name": user.get("last_name", "")
            }
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,
            "user": user
        }
    
    # ─── User Management ──────────────────────────────────────────────
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        try:
            # Try Supabase auth users
            result = supabase.table("users").select("*").eq("id", user_id).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            # Try auth users table
            result = supabase.table("auth.users").select("*").eq("id", user_id).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        try:
            result = supabase.table("users").select("*").eq("email", email).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    def create_user(self, email: str, password: str, **kwargs) -> Optional[Dict]:
        """Create a new user"""
        try:
            # Validate password
            validation = self.validate_password_strength(password)
            if not validation["valid"]:
                logger.warning(f"Password validation failed: {validation['issues']}")
                return None
            
            # Hash password
            hashed_password = self.hash_password(password)
            
            # Create user in Supabase
            user_data = {
                "email": email,
                "password_hash": hashed_password,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "is_active": True,
                "is_verified": False,
                "role": kwargs.get("role", "user")
            }
            
            # Add optional fields
            if kwargs.get("first_name"):
                user_data["first_name"] = kwargs["first_name"]
            if kwargs.get("last_name"):
                user_data["last_name"] = kwargs["last_name"]
            if kwargs.get("phone"):
                user_data["phone"] = kwargs["phone"]
            
            result = supabase.table("users").insert(user_data).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            return None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate a user with email and password"""
        user = self.get_user_by_email(email)
        if not user:
            logger.warning(f"User not found: {email}")
            return None
        
        # Check password
        password_hash = user.get("password_hash")
        if not password_hash:
            logger.warning(f"No password hash for user: {email}")
            return None
        
        if not self.verify_password(password, password_hash):
            logger.warning(f"Invalid password for user: {email}")
            return None
        
        # Check if user is active
        if not user.get("is_active", True):
            logger.warning(f"Inactive user: {email}")
            return None
        
        # Create tokens
        user_id = user.get("id")
        access_token = self.create_access_token(
            user_id=user_id,
            email=email,
            extra_data={
                "role": user.get("role", "user"),
                "first_name": user.get("first_name", ""),
                "last_name": user.get("last_name", "")
            }
        )
        refresh_token = self.create_refresh_token(user_id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,
            "user": {
                "id": user_id,
                "email": email,
                "first_name": user.get("first_name", ""),
                "last_name": user.get("last_name", ""),
                "role": user.get("role", "user"),
                "is_verified": user.get("is_verified", False),
                "created_at": user.get("created_at")
            }
        }
    
    def logout_user(self, user_id: str) -> bool:
        """Logout a user (invalidate tokens)"""
        # In a production system, you would add the token to a blacklist
        # For now, we just return success
        logger.info(f"User logged out: {user_id}")
        return True
    
    # ─── Password Reset ──────────────────────────────────────────────
    
    def generate_password_reset_token(self, email: str) -> Optional[str]:
        """Generate a password reset token"""
        user = self.get_user_by_email(email)
        if not user:
            return None
        
        user_id = user.get("id")
        expire = datetime.utcnow() + timedelta(hours=settings.PASSWORD_RESET_EXPIRATION_HOURS)
        
        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "password_reset"
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def verify_password_reset_token(self, token: str) -> Optional[Dict]:
        """Verify a password reset token"""
        payload = self.decode_token(token)
        if not payload:
            return None
        
        if payload.get("type") != "password_reset":
            logger.warning("Invalid token type for password reset")
            return None
        
        return payload
    
    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset a user's password using a token"""
        payload = self.verify_password_reset_token(token)
        if not payload:
            return False
        
        # Validate new password
        validation = self.validate_password_strength(new_password)
        if not validation["valid"]:
            logger.warning(f"Password validation failed: {validation['issues']}")
            return False
        
        user_id = payload.get("sub")
        if not user_id:
            return False
        
        try:
            hashed_password = self.hash_password(new_password)
            result = supabase.table("users")\
                .update({
                    "password_hash": hashed_password,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", user_id)\
                .execute()
            
            if result.data and len(result.data) > 0:
                logger.info(f"Password reset for user: {user_id}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return False
    
    # ─── Role Management ──────────────────────────────────────────────
    
    def is_admin(self, user_id: str) -> bool:
        """Check if a user is an admin"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        return user.get("role") in ["admin", "super_admin"]
    
    def is_staff(self, user_id: str) -> bool:
        """Check if a user is staff"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        return user.get("role") in ["admin", "super_admin", "staff"]
    
    def is_verified(self, user_id: str) -> bool:
        """Check if a user is verified"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        return user.get("is_verified", False)
    
    def update_user_role(self, user_id: str, role: str) -> bool:
        """Update a user's role"""
        try:
            result = supabase.table("users")\
                .update({
                    "role": role,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", user_id)\
                .execute()
            
            if result.data and len(result.data) > 0:
                logger.info(f"Role updated for user: {user_id} to {role}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating user role: {e}")
            return False
    
    # ─── OAuth (Google) ──────────────────────────────────────────────
    
    def create_or_update_oauth_user(self, oauth_data: Dict) -> Optional[Dict]:
        """Create or update a user from OAuth data"""
        email = oauth_data.get("email")
        if not email:
            return None
        
        user = self.get_user_by_email(email)
        
        if user:
            # Update existing user
            update_data = {
                "updated_at": datetime.utcnow().isoformat(),
                "oauth_provider": oauth_data.get("provider", "google"),
                "oauth_id": oauth_data.get("sub") or oauth_data.get("id"),
                "is_verified": True
            }
            if oauth_data.get("given_name"):
                update_data["first_name"] = oauth_data["given_name"]
            if oauth_data.get("family_name"):
                update_data["last_name"] = oauth_data["family_name"]
            if oauth_data.get("picture"):
                update_data["avatar_url"] = oauth_data["picture"]
            
            try:
                result = supabase.table("users")\
                    .update(update_data)\
                    .eq("id", user.get("id"))\
                    .execute()
                if result.data and len(result.data) > 0:
                    user = result.data[0]
            except Exception as e:
                logger.error(f"Error updating OAuth user: {e}")
                return None
        else:
            # Create new user
            user_data = {
                "email": email,
                "first_name": oauth_data.get("given_name", ""),
                "last_name": oauth_data.get("family_name", ""),
                "avatar_url": oauth_data.get("picture", ""),
                "oauth_provider": oauth_data.get("provider", "google"),
                "oauth_id": oauth_data.get("sub") or oauth_data.get("id"),
                "is_verified": True,
                "is_active": True,
                "role": "user",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            try:
                result = supabase.table("users").insert(user_data).execute()
                if result.data and len(result.data) > 0:
                    user = result.data[0]
                else:
                    return None
            except Exception as e:
                logger.error(f"Error creating OAuth user: {e}")
                return None
        
        # Create tokens
        user_id = user.get("id")
        access_token = self.create_access_token(
            user_id=user_id,
            email=email,
            extra_data={
                "role": user.get("role", "user"),
                "first_name": user.get("first_name", ""),
                "last_name": user.get("last_name", "")
            }
        )
        refresh_token = self.create_refresh_token(user_id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,
            "user": user
        }
