# app/modules/admin/service.py
# Auto-D Kenya - Admin Service
# ================================================================
# TYPE: MODULE - Admin business logic

import logging
from typing import Dict, Any
from datetime import datetime

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class AdminService:
    """Admin service for administrative functions."""
    
    def __init__(self):
        self.supabase = get_supabase()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get admin statistics."""
        try:
            # Get user count
            users = self.supabase.auth.get_users()
            
            # Get vehicle count
            vehicles = self.supabase.table("vehicles").select("count", count="exact").execute()
            
            # Get payment count and total
            payments = self.supabase.table("mpesa_payments").select("*").execute()
            
            return {
                "total_users": len(users.data) if users else 0,
                "total_vehicles": vehicles.count if vehicles else 0,
                "total_payments": len(payments.data) if payments else 0,
                "total_revenue": sum(float(p.get("amount", 0)) for p in payments.data) if payments else 0,
                "updated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting admin stats: {str(e)}")
            return {"error": str(e)}
    
    async def get_users(self) -> list:
        """Get all users."""
        try:
            response = self.supabase.auth.get_users()
            return response.data if response else []
        except Exception as e:
            logger.error(f"Error getting users: {str(e)}")
            return []
    
    async def get_all_payments(self) -> list:
        """Get all payments."""
        try:
            response = self.supabase.table("mpesa_payments").select("*").order("created_at", desc=True).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting all payments: {str(e)}")
            return []
