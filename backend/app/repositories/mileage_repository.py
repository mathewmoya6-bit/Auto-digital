# backend/app/repositories/mileage_repository.py
"""
Mileage Repository - Data access layer for mileage calculations
"""

from typing import Optional, List, Dict, Any
from app.core.database import supabase
import logging

logger = logging.getLogger(__name__)


class MileageRepository:
    """Repository for mileage-related operations"""
    
    def __init__(self):
        self.table = "mileage_reports"
    
    def save_mileage_report(self, report_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Save a mileage report"""
        try:
            response = supabase.table(self.table)\
                .insert(report_data)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error saving mileage report: {e}")
            return None
    
    def get_mileage_reports(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get mileage reports for a user"""
        try:
            response = supabase.table(self.table)\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching mileage reports for {user_id}: {e}")
            return []
