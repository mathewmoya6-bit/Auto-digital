# backend/app/engines/service_engine.py
from typing import Dict, Any
from app.schemas.response import CostComponent

class ServiceEngine:
    def calculate(self, vehicle: Dict[str, Any], distance: float) -> CostComponent:
        """Calculate service cost"""
        service_interval = vehicle.get("service_interval", 10000)  # km
        service_cost = vehicle.get("service_cost", 15000)  # KES
        
        # Calculate number of services needed
        services_needed = distance / service_interval
        
        # Calculate cost
        total_service_cost = services_needed * service_cost
        
        return CostComponent(
            component="Service",
            amount=round(total_service_cost, 2),
            description=f"{services_needed:.1f} services at KES {service_cost} each"
        )
