# backend/app/repositories/user_repository.py
"""
User Repository - Data access layer for user operations
"""

from typing import Optional, List, Dict, Any
from app.core.database import supabase
import logging

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user operations"""
    
    def __init__(self):
        self.table = "user_profiles"
        self.auth_table = "users"
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile by user ID"""
        try:
            response = supabase.table(self.table)\
                .select("*")\
                .eq("user_id", user_id)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching user profile {user_id}: {e}")
            return None
    
    def create_user_profile(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new user profile"""
        try:
            response = supabase.table(self.table)\
                .insert({
                    "user_id": user_data.get("user_id"),
                    "full_name": user_data.get("full_name"),
                    "email": user_data.get("email"),
                    "phone_number": user_data.get("phone_number"),
                    "company": user_data.get("company"),
                    "location": user_data.get("location"),
                    "created_at": "now()"
                })\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating user profile: {e}")
            return None
    
    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a user profile"""
        try:
            updates["updated_at"] = "now()"
            response = supabase.table(self.table)\
                .update(updates)\
                .eq("user_id", user_id)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating user profile {user_id}: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            response = supabase.table(self.table)\
                .select("*")\
                .eq("email", email)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching user by email {email}: {e}")
            return None
    
    def list_users(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List all users"""
        try:
            response = supabase.table(self.table)\
                .select("*")\
                .order("created_at", desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics"""
        try:
            stats = {
                "total_valuations": 0,
                "total_reports": 0,
                "total_vehicles": 0
            }
            
            # Get valuations count
            response = supabase.table("valuation_reports")\
                .select("*", count="exact")\
                .eq("user_id", user_id)\
                .execute()
            stats["total_valuations"] = response.count or 0
            
            # Get reports count
            response = supabase.table("mileage_reports")\
                .select("*", count="exact")\
                .eq("user_id", user_id)\
                .execute()
            stats["total_reports"] = response.count or 0
            
            # Get vehicles count
            response = supabase.table("user_vehicles")\
                .select("*", count="exact")\
                .eq("user_id", user_id)\
                .execute()
            stats["total_vehicles"] = response.count or 0
            
            return stats
        except Exception as e:
            logger.error(f"Error fetching user stats for {user_id}: {e}")
            return {
                "total_valuations": 0,
                "total_reports": 0,
                "total_vehicles": 0
            }
    
    def is_admin(self, user_id: str) -> bool:
        """Check if a user is an admin"""
        try:
            response = supabase.table("admin_users")\
                .select("role")\
                .eq("user_id", user_id)\
                .execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error checking admin status for {user_id}: {e}")
            return False
