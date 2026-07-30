# app/modules/auth/repository.py
# Auto-D Kenya - Auth Repository
# ================================================================
# TYPE: MODULE - Auth database operations

import logging
from typing import Optional, Dict, Any

from app.core.database import get_supabase
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)


class AuthRepository:
    """Authentication repository for database operations."""
    
    def __init__(self):
        self.supabase = get_supabase()
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID from Supabase Auth."""
        try:
            response = self.supabase.auth.get_user(user_id)
            if response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "full_name": response.user.user_metadata.get("full_name"),
                    "created_at": response.user.created_at
                }
            return None
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            return None
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile from users table."""
        try:
            response = self.supabase.table("users").select("*").eq("id", user_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return None
    
    async def create_user_profile(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create user profile in users table."""
        try:
            response = self.supabase.table("users").insert({
                "id": user_id,
                **data
            }).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Error creating user profile: {str(e)}")
            raise
    
    async def update_user_profile(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user profile in users table."""
        try:
            response = self.supabase.table("users").update(data).eq("id", user_id).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            raise
    
    async def get_user_services(self, user_id: str) -> list:
        """Get user's purchased services."""
        try:
            response = self.supabase.table("user_services").select("*, services(*)").eq("user_id", user_id).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting user services: {str(e)}")
            return []
