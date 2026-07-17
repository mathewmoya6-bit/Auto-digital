# backend/app/engines/mileage_rate_engine.py
from typing import Dict, Any
from app.engines.running_cost_engine import RunningCostEngine
from app.schemas.request import MileageRateRequest
from app.schemas.response import MileageRateResponse

class MileageRateEngine:
    def __init__(self):
        self.running_cost_engine = RunningCostEngine()
    
    def calculate(self, vehicle: Dict[str, Any], request: MileageRateRequest) -> MileageRateResponse:
        """Calculate mileage rate (cost per km)"""
        # Create running cost request
        running_cost_request = request.to_running_cost_request()
        
        # Calculate running costs
        running_cost = self.running_cost_engine.calculate(vehicle, running_cost_request)
        
        # The mileage rate is just the cost per km from running costs
        return MileageRateResponse(
            total_rate=running_cost.cost_per_km,
            fuel_rate=round(running_cost.fuel / request.distance, 2) if request.distance > 0 else 0,
            maintenance_rate=round((running_cost.service + running_cost.repairs) / request.distance, 2) if request.distance > 0 else 0,
            tyre_rate=round(running_cost.tyres / request.distance, 2) if request.distance > 0 else 0,
            insurance_rate=round(running_cost.insurance / request.distance, 2) if request.distance > 0 else 0,
            depreciation_rate=round(running_cost.depreciation / request.distance, 2) if request.distance > 0 else 0,
            finance_rate=round(running_cost.finance / request.distance, 2) if request.distance > 0 else 0,
            misc_rate=round(running_cost.misc / request.distance, 2) if request.distance > 0 else 0,
            total_running_cost=running_cost.total,
            distance=request.distance,
            vehicle_details=request.vehicle_details
        )
