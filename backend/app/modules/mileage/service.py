"""
Mileage Service
===============

Business logic for mileage operations.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import logging

from .repository import MileageRepository
from .schemas import (
    MileageCreate,
    MileageUpdate,
    MileageAnalytics,
    MileageValidationResponse,
    MileageAlertResponse,
)

logger = logging.getLogger(__name__)


class MileageService:
    """Service for mileage business logic."""
    
    def __init__(self):
        self.repository = MileageRepository()
    
    async def create_mileage(
        self,
        data: MileageCreate,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Create a new mileage record.
        
        Args:
            data: Mileage creation data
            user_id: User ID creating the record
        
        Returns:
            Created record
        """
        # Validate mileage
        await self.validate_mileage(data.vehicle_id, data.mileage)
        
        # Prepare data
        record_data = data.dict()
        record_data["user_id"] = user_id
        record_data["date_recorded"] = datetime.utcnow().isoformat()
        
        # Create record
        record = await self.repository.create(record_data)
        
        # Check if service is due
        service_alert = await self.check_service_due(
            data.vehicle_id,
            data.mileage
        )
        
        return {
            "record": record,
            "service_alert": service_alert
        }
    
    async def get_vehicle_mileage(
        self,
        vehicle_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get mileage records for a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
            limit: Number of records to return
            offset: Number of records to skip
        
        Returns:
            Paginated records with statistics
        """
        records = await self.repository.get_by_vehicle(vehicle_id, limit, offset)
        stats = await self.repository.get_statistics(vehicle_id)
        total = len(records)
        
        return {
            "items": records,
            "statistics": stats,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    async def get_latest_mileage(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest mileage record for a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
        
        Returns:
            Latest record or None
        """
        return await self.repository.get_latest_for_vehicle(vehicle_id)
    
    async def update_mileage(
        self,
        record_id: str,
        data: MileageUpdate,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Update a mileage record.
        
        Args:
            record_id: Record ID
            data: Update data
            user_id: User ID performing update
        
        Returns:
            Updated record or None
        """
        # Get existing record
        existing = await self.repository.get_by_id(record_id)
        if not existing:
            return None
        
        # Check if user owns this record or is admin
        if existing["user_id"] != user_id:
            # TODO: Check if user is admin
            pass
        
        # Prepare update data
        update_data = data.dict(exclude_unset=True)
        
        # Update record
        return await self.repository.update(record_id, update_data)
    
    async def delete_mileage(self, record_id: str, user_id: str) -> bool:
        """
        Delete a mileage record.
        
        Args:
            record_id: Record ID
            user_id: User ID performing deletion
        
        Returns:
            True if deleted successfully
        """
        # Get existing record
        existing = await self.repository.get_by_id(record_id)
        if not existing:
            return False
        
        # Check if user owns this record or is admin
        if existing["user_id"] != user_id:
            # TODO: Check if user is admin
            pass
        
        return await self.repository.delete(record_id)
    
    async def verify_mileage(
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
            Verified record or None
        """
        return await self.repository.verify_record(record_id, verified_by)
    
    async def validate_mileage(
        self,
        vehicle_id: str,
        mileage: int,
        previous_mileage: Optional[int] = None
    ) -> MileageValidationResponse:
        """
        Validate mileage data.
        
        Args:
            vehicle_id: Vehicle ID
            mileage: Mileage to validate
            previous_mileage: Previous mileage for comparison
        
        Returns:
            Validation response
        """
        issues = []
        suggestions = []
        anomaly_detected = False
        anomaly_score = 0.0
        
        # Check if mileage is positive
        if mileage < 0:
            issues.append("Mileage cannot be negative")
        
        # Get latest record
        latest = await self.repository.get_latest_for_vehicle(vehicle_id)
        if latest:
            latest_mileage = latest.get("mileage", 0)
            
            # Check if mileage is decreasing
            if mileage < latest_mileage:
                issues.append(f"Mileage decreased from {latest_mileage} to {mileage}")
                suggestions.append("This might be a data entry error. Please verify.")
                anomaly_detected = True
                anomaly_score = 0.8
            
            # Check for unrealistic jump
            mileage_diff = mileage - latest_mileage
            if mileage_diff > 100000:
                issues.append(f"Unrealistic mileage jump of {mileage_diff} km")
                suggestions.append("Please verify this mileage with supporting documents")
                anomaly_detected = True
                anomaly_score = 0.6
            
            # Check for normal usage
            if mileage_diff > 5000 and mileage_diff < 100000:
                suggestions.append(
                    f"Consider providing service records for the {mileage_diff} km increase"
                )
        
        return MileageValidationResponse(
            is_valid=len(issues) == 0,
            message="Mileage is valid" if len(issues) == 0 else "; ".join(issues),
            expected_range=None,
            anomaly_detected=anomaly_detected,
            anomaly_score=anomaly_score if anomaly_detected else None,
            suggestions=suggestions
        )
    
    async def get_analytics(
        self,
        vehicle_id: str,
        period: str = "month"
    ) -> Dict[str, Any]:
        """
        Get mileage analytics for a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
            period: Analysis period (day, week, month, year)
        
        Returns:
            Analytics data
        """
        records = await self.repository.get_by_vehicle(vehicle_id, limit=1000)
        
        if not records:
            return {
                "vehicle_id": vehicle_id,
                "total_mileage": 0,
                "average_mileage": 0,
                "max_mileage": 0,
                "min_mileage": 0,
                "mileage_count": 0,
                "daily_average": 0,
                "weekly_average": 0,
                "monthly_average": 0,
                "yearly_average": 0,
                "mileage_growth_rate": 0,
                "service_alerts": [],
                "mileage_by_period": []
            }
        
        # Calculate statistics
        mileages = [r["mileage"] for r in records]
        total_mileage = sum(mileages)
        avg_mileage = total_mileage / len(mileages)
        
        # Check service alerts
        service_alerts = await self.check_service_alerts(vehicle_id)
        
        # Group by period
        mileage_by_period = await self.group_mileage_by_period(records, period)
        
        return {
            "vehicle_id": vehicle_id,
            "total_mileage": total_mileage,
            "average_mileage": avg_mileage,
            "max_mileage": max(mileages) if mileages else 0,
            "min_mileage": min(mileages) if mileages else 0,
            "mileage_count": len(records),
            "daily_average": avg_mileage / 365 if len(records) > 0 else 0,
            "weekly_average": avg_mileage / 52 if len(records) > 0 else 0,
            "monthly_average": avg_mileage / 12 if len(records) > 0 else 0,
            "yearly_average": avg_mileage if len(records) > 0 else 0,
            "mileage_growth_rate": self.calculate_growth_rate(records),
            "service_alerts": service_alerts,
            "mileage_by_period": mileage_by_period
        }
    
    async def check_service_due(
        self,
        vehicle_id: str,
        current_mileage: int,
        service_interval: int = 15000
    ) -> Optional[MileageAlertResponse]:
        """
        Check if a vehicle is due for service.
        
        Args:
            vehicle_id: Vehicle ID
            current_mileage: Current mileage
            service_interval: Service interval in kilometers
        
        Returns:
            Service alert or None
        """
        # Get latest mileage
        latest = await self.repository.get_latest_for_vehicle(vehicle_id)
        if not latest:
            return None
        
        last_mileage = latest.get("mileage", 0)
        distance_since = current_mileage - last_mileage
        
        # Calculate when next service is due
        next_service = (last_mileage // service_interval + 1) * service_interval
        km_to_service = next_service - current_mileage
        
        if km_to_service <= 0:
            alert_level = "critical" if km_to_service < -1000 else "warning"
            message = f"Service is overdue by {-km_to_service} km"
        elif km_to_service <= 1000:
            alert_level = "warning"
            message = f"Service is due in {km_to_service} km"
        else:
            alert_level = "ok"
            message = f"Next service in {km_to_service} km"
        
        return MileageAlertResponse(
            vehicle_id=vehicle_id,
            current_mileage=current_mileage,
            next_service_mileage=next_service,
            kilometers_to_service=max(0, km_to_service),
            service_due=km_to_service <= 0,
            alert_level=alert_level,
            message=message,
            estimated_service_date=None
        )
    
    async def check_service_alerts(
        self,
        vehicle_id: str
    ) -> List[Dict[str, Any]]:
        """
        Check for service alerts for a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
        
        Returns:
            List of alerts
        """
        alerts = []
        latest = await self.repository.get_latest_for_vehicle(vehicle_id)
        
        if latest:
            current_mileage = latest.get("mileage", 0)
            
            # Check service due
            service_alert = await self.check_service_due(vehicle_id, current_mileage)
            if service_alert and service_alert.alert_level != "ok":
                alerts.append({
                    "type": "service_due",
                    "severity": service_alert.alert_level,
                    "message": service_alert.message,
                    "data": service_alert.dict()
                })
        
        return alerts
    
    def calculate_growth_rate(self, records: List[Dict[str, Any]]) -> float:
        """
        Calculate mileage growth rate.
        
        Args:
            records: List of mileage records
        
        Returns:
            Growth rate percentage
        """
        if len(records) < 2:
            return 0
        
        first = records[-1].get("mileage", 0)
        last = records[0].get("mileage", 0)
        
        if first == 0:
            return 0
        
        growth = ((last - first) / first) * 100
        return round(growth, 2)
    
    async def group_mileage_by_period(
        self,
        records: List[Dict[str, Any]],
        period: str
    ) -> List[Dict[str, Any]]:
        """
        Group mileage records by period.
        
        Args:
            records: List of records
            period: Period to group by (day, week, month, year)
        
        Returns:
            Grouped mileage data
        """
        # TODO: Implement proper grouping
        return []
    
    async def compare_mileage_with_vehicles(
        self,
        vehicle_id: str,
        make: str,
        model: str,
        year: int
    ) -> Dict[str, Any]:
        """
        Compare mileage with similar vehicles.
        
        Args:
            vehicle_id: Vehicle ID
            make: Vehicle make
            model: Vehicle model
            year: Vehicle year
        
        Returns:
            Comparison data
        """
        # TODO: Implement comparison logic
        return {
            "current_mileage": 0,
            "average_for_model": 0,
            "percentile": 50,
            "comparison": "average",
            "suggestions": []
        }
