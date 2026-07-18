# backend/app/repositories/ownership_repository.py
"""
Ownership Repository - Data access layer for ownership calculations
"""

from typing import Optional, List, Dict, Any
from app.core.database import supabase
import logging

logger = logging.getLogger(__name__)


class OwnershipRepository:
    """Repository for ownership-related operations"""
    
    def __init__(self):
        self.table = "ownership_reports"
    
    def save_ownership_report(self, report_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Save an ownership report"""
        try:
            response = supabase.table(self.table)\
                .insert(report_data)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error saving ownership report: {e}")
            return None
    
    def get_ownership_reports(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get ownership reports for a user"""
        try:
            response = supabase.table(self.table)\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching ownership reports for {user_id}: {e}")
            return []
    
    def get_ownership_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific ownership report"""
        try:
            response = supabase.table(self.table)\
                .select("*")\
                .eq("id", report_id)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching ownership report {report_id}: {e}")
            return None
