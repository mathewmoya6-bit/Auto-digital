"""
Auto-D Kenya
Vehicle Master Dashboard Service
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from app.modules.vehicle_master.repository import VehicleMasterRepository
from app.modules.vehicle_master.audit import AuditService

logger = logging.getLogger(__name__)


class VehicleDashboardService:
    """Enhanced dashboard service for vehicle master."""

    def __init__(self):
        self.repository = VehicleMasterRepository()
        self.audit = AuditService()

    async def get_overview(self) -> Dict[str, Any]:
        """Get comprehensive dashboard overview."""
        stats = await self.repository.statistics()
        
        # Get recent activity
        recent_activity = await self.audit.get_audit_logs(limit=10)
        
        # Get recent additions (last 30 days)
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        try:
            recent_vehicles_result = await self.repository.search()
            recent_vehicles = recent_vehicles_result.get("results", [])[:10]
        except Exception:
            recent_vehicles = []
        
        return {
            "stats": stats,
            "recent_activity": recent_activity,
            "recent_vehicles": recent_vehicles,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def get_make_breakdown(self) -> List[Dict[str, Any]]:
        """Get vehicle breakdown by make."""
        try:
            result = await self.repository.search()
            vehicles = result.get("results", [])
            
            make_counts = {}
            for v in vehicles:
                make = v.get("make_name", "Unknown")
                make_counts[make] = make_counts.get(make, 0) + 1
            
            return [
                {"make": make, "count": count}
                for make, count in sorted(
                    make_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
            ]
        except Exception as e:
            logger.error(f"Error getting make breakdown: {e}")
            return []

    async def get_fuel_breakdown(self) -> List[Dict[str, Any]]:
        """Get vehicle breakdown by fuel type."""
        try:
            result = await self.repository.search()
            vehicles = result.get("results", [])
            
            fuel_counts = {}
            for v in vehicles:
                fuel = v.get("fuel_type_name", "Unknown")
                fuel_counts[fuel] = fuel_counts.get(fuel, 0) + 1
            
            return [
                {"fuel_type": fuel, "count": count}
                for fuel, count in sorted(
                    fuel_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
            ]
        except Exception as e:
            logger.error(f"Error getting fuel breakdown: {e}")
            return []

    async def get_body_type_breakdown(self) -> List[Dict[str, Any]]:
        """Get vehicle breakdown by body type."""
        try:
            result = await self.repository.search()
            vehicles = result.get("results", [])
            
            body_counts = {}
            for v in vehicles:
                body = v.get("body_type_name", "Unknown")
                body_counts[body] = body_counts.get(body, 0) + 1
            
            return [
                {"body_type": body, "count": count}
                for body, count in sorted(
                    body_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
            ]
        except Exception as e:
            logger.error(f"Error getting body type breakdown: {e}")
            return []
