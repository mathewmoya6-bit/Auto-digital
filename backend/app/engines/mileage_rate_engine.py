"""
Mileage Rate Engine - Calculate cost per kilometer
"""
from typing import Dict, Any
import logging

from app.schemas.request import MileageRateRequest
from app.schemas.response import MileageRateResponse

logger = logging.getLogger(__name__)


class MileageRateEngine:
    """Engine for calculating cost per kilometer"""
    
    def calculate_mileage_rate(
        self,
        variant: Dict[str, Any],
        request: MileageRateRequest
    ) -> MileageRateResponse:
        """
        Calculate cost per kilometer for a vehicle
        
        Args:
            variant: Vehicle variant data
            request: Mileage rate calculation request
        
        Returns:
            MileageRateResponse with mileage rate details
        """
        # Extract variant data
        fuel_consumption = variant.get("fuel_consumption", 8.0)  # L/100km
        market_value = variant.get("market_value", 0)
        
        # 1. Fuel cost per km
        fuel_cost_per_km = (fuel_consumption / 100) * request.fuel_price
        
        # 2. Annual fuel cost
        annual_fuel_cost = fuel_cost_per_km * request.annual_mileage
        
        # 3. Depreciation cost per km
        if request.include_depreciation:
            annual_depreciation = market_value * 0.12  # 12% annual depreciation
            depreciation_per_km = annual_depreciation / request.annual_mileage
        else:
            annual_depreciation = 0
            depreciation_per_km = 0
        
        # 4. Insurance cost per km
        if request.include_insurance:
            annual_insurance = request.insurance_cost_per_km * request.annual_mileage
            insurance_per_km = request.insurance_cost_per_km
        else:
            annual_insurance = 0
            insurance_per_km = 0
        
        # 5. Maintenance cost per km
        if request.include_maintenance:
            maintenance_per_km = request.maintenance_cost_per_km
            annual_maintenance = maintenance_per_km * request.annual_mileage
        else:
            maintenance_per_km = 0
            annual_maintenance = 0
        
        # 6. Tyre cost per km
        if request.include_tyres:
            tyre_per_km = request.tyre_cost_per_km
            annual_tyres = tyre_per_km * request.annual_mileage
        else:
            tyre_per_km = 0
            annual_tyres = 0
        
        # Calculate total cost per km
        total_cost_per_km = (
            fuel_cost_per_km +
            depreciation_per_km +
            insurance_per_km +
            maintenance_per_km +
            tyre_per_km
        )
        
        # Annual total cost
        total_annual_cost = total_cost_per_km * request.annual_mileage
        
        # Monthly cost
        monthly_km = request.annual_mileage / 12
        monthly_cost = total_cost_per_km * monthly_km
        
        # Breakdown
        breakdown = {
            "fuel": annual_fuel_cost,
            "depreciation": annual_depreciation,
            "insurance": annual_insurance,
            "maintenance": annual_maintenance,
            "tyres": annual_tyres
        }
        
        # Remove zero values
        breakdown = {k: v for k, v in breakdown.items() if v > 0}
        
        # Recommendations
        recommendations = []
        if fuel_cost_per_km > total_cost_per_km * 0.40:
            recommendations.append("Fuel cost is high. Consider a more fuel-efficient vehicle.")
        if depreciation_per_km > total_cost_per_km * 0.30:
            recommendations.append("Depreciation is significant. Consider a used vehicle for better value.")
        
        # Return response
        return MileageRateResponse(
            total_cost_per_km=round(total_cost_per_km, 2),
            total_annual_cost=round(total_annual_cost, 2),
            monthly_cost=round(monthly_cost, 2),
            breakdown=breakdown,
            fuel_cost_per_km=round(fuel_cost_per_km, 2),
            depreciation_per_km=round(depreciation_per_km, 2),
            insurance_per_km=round(insurance_per_km, 2),
            maintenance_per_km=round(maintenance_per_km, 2),
            tyre_per_km=round(tyre_per_km, 2),
            annual_mileage=request.annual_mileage,
            currency="KES",
            recommendations=recommendations
        )
