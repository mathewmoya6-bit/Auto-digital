# backend/app/engines/running_cost_engine.py
from typing import Dict, Any
from app.engines.fuel_engine import FuelEngine
from app.engines.service_engine import ServiceEngine
from app.engines.tyre_engine import TyreEngine
from app.engines.insurance_engine import InsuranceEngine
from app.engines.depreciation_engine import DepreciationEngine
from app.engines.repair_engine import RepairEngine
from app.engines.finance_engine import FinanceEngine
from app.engines.miscellaneous_engine import MiscellaneousEngine
from app.schemas.request import RunningCostRequest, MileageRateRequest
from app.schemas.response import RunningCostResponse, CostComponent

class RunningCostEngine:
    def __init__(self):
        self.fuel_engine = FuelEngine()
        self.service_engine = ServiceEngine()
        self.tyre_engine = TyreEngine()
        self.insurance_engine = InsuranceEngine()
        self.depreciation_engine = DepreciationEngine()
        self.repair_engine = RepairEngine()
        self.finance_engine = FinanceEngine()
        self.misc_engine = MiscellaneousEngine()
    
    def calculate(self, vehicle: Dict[str, Any], request: RunningCostRequest) -> RunningCostResponse:
        """Calculate running costs for a vehicle"""
        
        # Get vehicle specifications
        vehicle_data = {
            "engine_cc": vehicle.get("engine_cc", 0),
            "fuel_type": vehicle.get("fuel_type", "petrol"),
            "transmission": vehicle.get("transmission", "automatic"),
            "fuel_consumption": vehicle.get("fuel_consumption", 10.0),
            "insurance_group": vehicle.get("insurance_group", 5),
            "service_interval": vehicle.get("service_interval", 10000),
            "tyre_size": vehicle.get("tyre_size", "225/65R17"),
            "market_value": vehicle.get("market_value", 5000000),
            "depreciation_class": vehicle.get("depreciation_class", "SUV_D"),
            "tyre_cost": vehicle.get("tyre_cost", 12000),
            "service_cost": vehicle.get("service_cost", 15000)
        }
        
        # Calculate each cost component
        fuel_cost = self.fuel_engine.calculate(
            vehicle_data, 
            request.distance,
            request.trip_type
        )
        
        service_cost = self.service_engine.calculate(
            vehicle_data,
            request.distance
        )
        
        tyre_cost = self.tyre_engine.calculate(
            vehicle_data,
            request.distance
        )
        
        insurance_cost = self.insurance_engine.calculate(
            vehicle_data,
            request.distance,
            request.driving_style
        )
        
        depreciation_cost = self.depreciation_engine.calculate(
            vehicle_data,
            request.distance,
            request.driving_style
        )
        
        repair_cost = self.repair_engine.calculate(
            vehicle_data,
            request.distance,
            request.driving_style
        )
        
        finance_cost = self.finance_engine.calculate(
            vehicle_data,
            request.distance
        )
        
        misc_cost = self.misc_engine.calculate(
            vehicle_data,
            request.distance,
            request.trip_type
        )
        
        # Combine all costs
        total_cost = sum([
            fuel_cost.amount,
            service_cost.amount,
            tyre_cost.amount,
            insurance_cost.amount,
            depreciation_cost.amount,
            repair_cost.amount,
            finance_cost.amount,
            misc_cost.amount
        ])
        
        cost_per_km = total_cost / request.distance if request.distance > 0 else 0
        
        return RunningCostResponse(
            fuel=fuel_cost.amount,
            service=service_cost.amount,
            tyres=tyre_cost.amount,
            insurance=insurance_cost.amount,
            repairs=repair_cost.amount,
            depreciation=depreciation_cost.amount,
            finance=finance_cost.amount,
            misc=misc_cost.amount,
            total=round(total_cost, 2),
            cost_per_km=round(cost_per_km, 2),
            components=[fuel_cost, service_cost, tyre_cost, insurance_cost, 
                       depreciation_cost, repair_cost, finance_cost, misc_cost]
        )
