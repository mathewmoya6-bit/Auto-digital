# app/modules/mileage/repository.py

"""
Mileage Repository
==================

Database operations for mileage records.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class MileageRepository:
    """Repository for mileage database operations."""
    
    def __init__(self):
        self.supabase = get_supabase()
        self.table = "mileage_records"
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new mileage record.
        
        Args:
            data: Mileage record data
        
        Returns:
            Created record
        """
        try:
            # Add timestamp
            data["created_at"] = datetime.utcnow().isoformat()
            data["updated_at"] = datetime.utcnow().isoformat()
            
            # Get previous mileage for this vehicle
            previous = await self.get_latest_for_vehicle(data["vehicle_id"])
            if previous:
                data["previous_mileage"] = previous["mileage"]
            
            # Insert
            response = self.supabase.table(self.table).insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating mileage record: {e}")
            raise
    
    async def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a mileage record by ID.
        
        Args:
            record_id: Record ID
        
        Returns:
            Record data or None
        """
        try:
            response = self.supabase.table(self.table).select("*").eq("id", record_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting mileage record: {e}")
            return None
    
    async def get_by_vehicle(
        self,
        vehicle_id: str,
        limit: int = 50,
        offset: int = 0,
        sort_order: str = "desc"
    ) -> List[Dict[str, Any]]:
        """
        Get mileage records for a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
            limit: Number of records to return
            offset: Number of records to skip
            sort_order: Sort order ('asc' or 'desc')
        
        Returns:
            List of records
        """
        try:
            query = self.supabase.table(self.table).select("*").eq("vehicle_id", vehicle_id)
            
            if sort_order == "desc":
                query = query.order("date_recorded", desc=True)
            else:
                query = query.order("date_recorded", desc=False)
            
            response = query.limit(limit).offset(offset).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting vehicle mileage: {e}")
            return []
    
    async def get_latest_for_vehicle(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest mileage record for a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
        
        Returns:
            Latest record or None
        """
        try:
            response = (
                self.supabase.table(self.table)
                .select("*")
                .eq("vehicle_id", vehicle_id)
                .order("date_recorded", desc=True)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting latest mileage: {e}")
            return None
    
    async def get_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get mileage records by user.
        
        Args:
            user_id: User ID
            limit: Number of records to return
            offset: Number of records to skip
        
        Returns:
            List of records
        """
        try:
            response = (
                self.supabase.table(self.table)
                .select("*")
                .eq("user_id", user_id)
                .order("date_recorded", desc=True)
                .limit(limit)
                .offset(offset)
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Error getting user mileage: {e}")
            return []
    
    async def update(
        self,
        record_id: str,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a mileage record.
        
        Args:
            record_id: Record ID
            data: Update data
        
        Returns:
            Updated record or None
        """
        try:
            data["updated_at"] = datetime.utcnow().isoformat()
            response = self.supabase.table(self.table).update(data).eq("id", record_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating mileage record: {e}")
            return None
    
    async def delete(self, record_id: str) -> bool:
        """
        Delete a mileage record.
        
        Args:
            record_id: Record ID
        
        Returns:
            True if deleted successfully
        """
        try:
            response = self.supabase.table(self.table).delete().eq("id", record_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error deleting mileage record: {e}")
            return False
    
    async def verify_record(
        self,
        record_id: str,
        verified_by: str
    ) -> Optional[Dict[str, Any]]:
        """
        Verify a mileage record.
        
        Args:
            record_id: Record ID
            verified_by: User ID of verifier
        
        Returns:
            Updated record or None
        """
        try:
            data = {
                "is_verified": True,
                "verified_by": verified_by,
                "verified_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            response = self.supabase.table(self.table).update(data).eq("id", record_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error verifying mileage record: {e}")
            return None
    
    async def get_statistics(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get mileage statistics for a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
        
        Returns:
            Statistics dictionary
        """
        try:
            records = await self.get_by_vehicle(vehicle_id, limit=1000)
            
            if not records:
                return {
                    "total_mileage": 0,
                    "avg_mileage": 0,
                    "count": 0,
                    "min": 0,
                    "max": 0
                }
            
            mileages = [r["mileage"] for r in records]
            
            return {
                "total_mileage": sum(mileages),
                "avg_mileage": sum(mileages) / len(mileages),
                "count": len(records),
                "min": min(mileages),
                "max": max(mileages),
                "first_record": records[-1] if records else None,
                "last_record": records[0] if records else None
            }
        except Exception as e:
            logger.error(f"Error getting mileage statistics: {e}")
            return {}
    
    async def get_mileage_history(
        self,
        vehicle_id: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get mileage history for a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
            days: Number of days of history
        
        Returns:
            List of history records
        """
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            response = (
                self.supabase.table(self.table)
                .select("*")
                .eq("vehicle_id", vehicle_id)
                .gte("date_recorded", cutoff_date)
                .order("date_recorded", desc=True)
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Error getting mileage history: {e}")
            return []
