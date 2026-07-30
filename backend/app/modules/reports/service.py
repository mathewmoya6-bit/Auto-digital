# app/modules/reports/service.py
# Auto-D Kenya - Reports Service
# ================================================================
# TYPE: MODULE - Reports business logic

import logging
from typing import Dict, Any
from datetime import datetime

from app.core.database import get_supabase
from app.core.exceptions import NotFoundException
from app.modules.valuation.service import ValuationService
from app.modules.valuation.engine import ValuationEngine

logger = logging.getLogger(__name__)


class ReportService:
    """Report service for generating and managing reports."""
    
    def __init__(self):
        self.supabase = get_supabase()
        self.valuation_service = ValuationService()
        self.valuation_engine = ValuationEngine()
    
    async def generate_valuation_report(self, vehicle_id: str, user_id: str) -> Dict[str, Any]:
        """Generate a valuation report for a vehicle."""
        # Get vehicle
        vehicle = self.supabase.table("vehicles").select("*").eq("id", vehicle_id).eq("user_id", user_id).execute()
        if not vehicle.data:
            raise NotFoundException("Vehicle not found")
        
        vehicle_data = vehicle.data[0]
        
        # Get valuation
        valuation = await self.valuation_service.calculate_valuation(
            variant_id="sample",  # Would need variant_id from vehicle
            year=vehicle_data.get("year", 2020),
            mileage=vehicle_data.get("mileage", 0),
            user_id=user_id
        )
        
        return {
            "vehicle": vehicle_data,
            "valuation": valuation,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def generate_running_cost_report(self, vehicle_id: str, user_id: str) -> Dict[str, Any]:
        """Generate a running cost report for a vehicle."""
        # Get vehicle
        vehicle = self.supabase.table("vehicles").select("*").eq("id", vehicle_id).eq("user_id", user_id).execute()
        if not vehicle.data:
            raise NotFoundException("Vehicle not found")
        
        vehicle_data = vehicle.data[0]
        
        # Calculate running costs
        annual_mileage = vehicle_data.get("annual_mileage", 20000)
        fuel_consumption = 10.0  # Would come from variant
        fuel_price = 200.0
        
        annual_fuel_cost = (annual_mileage / fuel_consumption) * fuel_price
        annual_maintenance = annual_mileage * 1.5
        annual_insurance = 50000
        
        total_cost = annual_fuel_cost + annual_maintenance + annual_insurance
        
        return {
            "vehicle": vehicle_data,
            "annual_fuel_cost": annual_fuel_cost,
            "annual_maintenance": annual_maintenance,
            "annual_insurance": annual_insurance,
            "total_annual_cost": total_cost,
            "cost_per_km": total_cost / annual_mileage if annual_mileage > 0 else 0,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def get_report_history(self, user_id: str) -> list:
        """Get report history for a user."""
        try:
            response = self.supabase.table("valuation_reports").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting report history: {str(e)}")
            return []
