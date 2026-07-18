# backend/app/services/report_service.py
"""
Report Service - Business logic for report generation
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from app.repositories.vehicle_repository import VehicleRepository
from app.repositories.mileage_repository import MileageRepository
from app.repositories.ownership_repository import OwnershipRepository
import logging

logger = logging.getLogger(__name__)


class ReportService:
    """Service for generating reports"""
    
    def __init__(self):
        self.vehicle_repository = VehicleRepository()
        self.mileage_repository = MileageRepository()
        self.ownership_repository = OwnershipRepository()
    
    def generate_mileage_report(self, user_id: str, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Generate mileage report for a user"""
        reports = self.mileage_repository.get_mileage_reports(user_id)
        
        # Filter by date if provided
        if start_date and end_date:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            reports = [r for r in reports if start <= datetime.fromisoformat(r['created_at']) <= end]
        
        total_distance = sum(r.get('trip_distance', 0) for r in reports)
        total_cost = sum(r.get('total_cost', 0) for r in reports)
        
        return {
            "report_type": "mileage",
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_reports": len(reports),
                "total_distance": total_distance,
                "total_cost": total_cost,
                "average_cost_per_km": total_cost / total_distance if total_distance > 0 else 0
            },
            "data": reports
        }
    
    def generate_ownership_report(self, user_id: str) -> Dict[str, Any]:
        """Generate ownership report for a user"""
        reports = self.ownership_repository.get_ownership_reports(user_id)
        
        total_cost = sum(r.get('total_cost', 0) for r in reports)
        
        return {
            "report_type": "ownership",
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_reports": len(reports),
                "total_cost": total_cost,
                "average_cost": total_cost / len(reports) if reports else 0
            },
            "data": reports
        }
    
    def generate_valuation_report(self, user_id: str, vehicle_ids: List[str] = None) -> Dict[str, Any]:
        """Generate valuation report for vehicles"""
        # This would typically pull from a valuations table
        # For now, return a placeholder
        return {
            "report_type": "valuation",
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_vehicles": len(vehicle_ids) if vehicle_ids else 0
            },
            "data": []
        }
