"""
Mileage Service - Auto-D Kenya
API endpoints for mileage and running cost calculations
"""

from typing import Dict, Any
from flask import jsonify, request

from engines.running_cost_engine import RunningCostEngine


class MileageService:
    """Mileage and running cost service"""
    
    def __init__(self):
        self.engine = RunningCostEngine()
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate mileage cost"""
        distance_km = data.get("distance_km")
        if not distance_km:
            return {"error": "distance_km is required"}, 400
        
        try:
            distance_km = float(distance_km)
            if distance_km <= 0:
                raise ValueError
        except ValueError:
            return {"error": "distance_km must be a positive number"}, 400
        
        # Build vehicle data
        vehicle_data = {
            "fuel_type": data.get("fuel_type", "petrol"),
            "fuel_consumption": data.get("fuel_consumption", 8),
            "maintenance_per_km": data.get("maintenance_per_km", 0),
            "insurance_annual": data.get("insurance", 0),
            "tax_annual": data.get("tax", 0),
            "annual_km": data.get("annual_km", 20000),
            "purchase_price": data.get("purchase_price", 0),
            "tyre_size": data.get("tyre_size", ""),
            "vehicle_type": data.get("vehicle_type", "Car")
        }
        
        result = self.engine.calculate_trip_cost(
            distance_km=distance_km,
            vehicle_data=vehicle_data
        )
        
        return {
            "success": True,
            "data": {
                "total_cost": result.summary["total_cost"],
                "cost_per_km": result.summary["total_per_km"],
                "fuel_cost": result.summary["energy_cost"],
                "maintenance_cost": result.operating_costs.get("maintenance", 0),
                "insurance_cost": result.fixed_costs.get("insurance", 0),
                "tax_cost": result.fixed_costs.get("tax", 0),
                "tyre_cost": result.operating_costs.get("tyres", 0),
                "depreciation_cost": result.fixed_costs.get("depreciation", 0),
                "fixed_costs": result.fixed_costs,
                "operating_costs": result.operating_costs,
                "projection": result.projection,
                "recommendations": result.recommendations
            }
        }
