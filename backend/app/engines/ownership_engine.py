# backend/app/engines/ownership_engine.py
"""
Ownership Engine - Total cost of ownership calculations
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from app.schemas.request import OwnershipCostRequest
from app.schemas.response import OwnershipCostResponse
from app.engines.running_cost_engine import RunningCostEngine
import logging

logger = logging.getLogger(__name__)


class OwnershipEngine:
    """Engine for calculating total cost of ownership over time"""
    
    def __init__(self):
        self.running_cost_engine = RunningCostEngine()
        
        # Depreciation rates by class (annual)
        self.depreciation_rates = {
            "SUV_A": 0.08,
            "SUV_B": 0.10,
            "SUV_C": 0.13,
            "SUV_D": 0.16,
            "SEDAN_A": 0.07,
            "SEDAN_B": 0.09,
            "SEDAN_C": 0.12,
            "SEDAN_D": 0.15,
            "PICKUP_A": 0.09,
            "PICKUP_B": 0.11,
            "PICKUP_C": 0.14,
            "LUXURY_A": 0.15,
            "LUXURY_B": 0.20,
            "LUXURY_C": 0.25,
            "DEFAULT": 0.12
        }
        
        # Insurance rates by type
        self.insurance_rates = {
            "comprehensive": 0.045,
            "third_party": 0.015,
            "third_party_fire": 0.025
        }
    
    def calculate(self, vehicle: Dict[str, Any], request: OwnershipCostRequest) -> OwnershipCostResponse:
        """
        Calculate total ownership cost over the ownership period
        
        Args:
            vehicle: Vehicle data dictionary
            request: Ownership cost request
        
        Returns:
            OwnershipCostResponse with cost breakdown
        """
        years = request.years_owned
        annual_mileage = request.annual_mileage
        total_cost = 0
        year_by_year = []
        breakdown = {
            "running_cost": 0,
            "depreciation": 0,
            "financing": 0,
            "insurance": 0,
            "fuel": 0,
            "maintenance": 0,
            "tyres": 0,
            "licensing": 0
        }
        
        # Get vehicle purchase price
        purchase_price = vehicle.get("market_value", 5000000)
        depreciation_class = vehicle.get("depreciation_class", "DEFAULT")
        fuel_type = vehicle.get("fuel_type", "petrol")
        
        # Calculate for each year
        for year in range(1, years + 1):
            # 1. Calculate running costs for this year
            running_cost = self._calculate_running_cost(vehicle, annual_mileage, request)
            
            # 2. Calculate depreciation for this year
            depreciation = self._calculate_depreciation(
                purchase_price, 
                depreciation_class, 
                year, 
                annual_mileage * year
            )
            
            # 3. Calculate financing cost if applicable
            financing = self._calculate_financing(
                purchase_price,
                request,
                year
            )
            
            # 4. Calculate insurance cost
            insurance = self._calculate_insurance(
                vehicle,
                purchase_price,
                depreciation,
                request,
                year
            )
            
            # 5. Calculate licensing fees
            licensing = self._calculate_licensing(year)
            
            # Sum yearly costs
            year_total = (
                running_cost.get("total", 0) +
                depreciation +
                financing +
                insurance +
                licensing
            )
            
            # Update breakdown
            breakdown["running_cost"] += running_cost.get("total", 0)
            breakdown["depreciation"] += depreciation
            breakdown["financing"] += financing
            breakdown["insurance"] += insurance
            breakdown["fuel"] += running_cost.get("fuel", 0)
            breakdown["maintenance"] += running_cost.get("maintenance", 0)
            breakdown["tyres"] += running_cost.get("tyres", 0)
            breakdown["licensing"] += licensing
            
            # Add to year_by_year
            year_by_year.append({
                "year": year,
                "running_cost": round(running_cost.get("total", 0), 2),
                "depreciation": round(depreciation, 2),
                "financing": round(financing, 2),
                "insurance": round(insurance, 2),
                "licensing": round(licensing, 2),
                "fuel": round(running_cost.get("fuel", 0), 2),
                "maintenance": round(running_cost.get("maintenance", 0), 2),
                "tyres": round(running_cost.get("tyres", 0), 2),
                "total": round(year_total, 2)
            })
            
            total_cost += year_total
        
        # Calculate final statistics
        total_km = annual_mileage * years
        cost_per_km = total_cost / total_km if total_km > 0 else 0
        cost_per_month = total_cost / (years * 12) if years > 0 else 0
        
        # Calculate resale value
        resale_value = self._calculate_resale_value(
            purchase_price,
            depreciation_class,
            years,
            annual_mileage * years
        )
        
        # Calculate value retained
        value_retained = (resale_value / purchase_price * 100) if purchase_price > 0 else 0
        
        return OwnershipCostResponse(
            total_cost=round(total_cost, 2),
            annual_cost=round(total_cost / years, 2) if years > 0 else 0,
            cost_per_km=round(cost_per_km, 2),
            breakdown={
                "running_cost": round(breakdown["running_cost"], 2),
                "depreciation": round(breakdown["depreciation"], 2),
                "financing": round(breakdown["financing"], 2),
                "insurance": round(breakdown["insurance"], 2),
                "fuel": round(breakdown["fuel"], 2),
                "maintenance": round(breakdown["maintenance"], 2),
                "tyres": round(breakdown["tyres"], 2),
                "licensing": round(breakdown["licensing"], 2),
                "purchase_price": round(purchase_price, 2),
                "resale_value": round(resale_value, 2),
                "value_retained": round(value_retained, 1)
            },
            year_by_year=year_by_year
        )
    
    def _calculate_running_cost(self, vehicle: Dict[str, Any], annual_mileage: float, request: OwnershipCostRequest) -> Dict[str, float]:
        """
        Calculate running costs for one year
        
        Returns:
            Dictionary with running cost breakdown
        """
        from app.schemas.request import RunningCostRequest
        
        # Create running cost request
        running_request = RunningCostRequest(
            variant_id=request.variant_id,
            distance=annual_mileage,
            trip_type="mixed",
            driving_style="normal"
        )
        
        # Calculate running cost
        try:
            result = self.running_cost_engine.calculate(vehicle, running_request)
            
            return {
                "total": result.total,
                "fuel": result.fuel,
                "service": result.service,
                "tyres": result.tyres,
                "insurance": result.insurance,
                "repairs": result.repairs,
                "depreciation": result.depreciation,
                "finance": result.finance,
                "misc": result.misc
            }
        except Exception as e:
            logger.error(f"Error calculating running cost: {e}")
            # Return fallback values
            return {
                "total": annual_mileage * 20,  # Fallback: KES 20/km
                "fuel": annual_mileage * 10,
                "service": annual_mileage * 3,
                "tyres": annual_mileage * 2,
                "insurance": annual_mileage * 2,
                "repairs": annual_mileage * 1.5,
                "depreciation": annual_mileage * 1.5,
                "finance": 0,
                "misc": annual_mileage * 0.5
            }
    
    def _calculate_depreciation(self, purchase_price: float, depreciation_class: str, year: int, total_mileage: float) -> float:
        """
        Calculate depreciation for a specific year
        
        Args:
            purchase_price: Initial purchase price
            depreciation_class: Vehicle depreciation class
            year: Current year of ownership (1-indexed)
            total_mileage: Total mileage accumulated
        
        Returns:
            Depreciation amount for this year
        """
        # Get base depreciation rate
        rate = self.depreciation_rates.get(depreciation_class, 0.12)
        
        # Depreciation decreases slightly each year (diminishing returns)
        year_factor = 1 - (year - 1) * 0.05
        year_factor = max(year_factor, 0.5)
        
        # Mileage impact - higher mileage = more depreciation
        expected_mileage = year * 20000
        mileage_factor = min(total_mileage / expected_mileage if expected_mileage > 0 else 1, 2.0)
        mileage_factor = 0.8 + (mileage_factor - 0.8) * 0.5  # Cap the impact
        
        # Calculate depreciation for this year
        adjusted_rate = rate * year_factor * mileage_factor
        
        # Apply to remaining value (not purchase price)
        remaining_value = purchase_price
        for y in range(1, year):
            # Calculate depreciation for previous years
            prev_rate = self.depreciation_rates.get(depreciation_class, 0.12)
            prev_factor = 1 - (y - 1) * 0.05
            prev_factor = max(prev_factor, 0.5)
            prev_mileage_factor = min((y * 20000) / (y * 20000) if (y * 20000) > 0 else 1, 2.0)
            prev_mileage_factor = 0.8 + (prev_mileage_factor - 0.8) * 0.5
            prev_adjusted_rate = prev_rate * prev_factor * prev_mileage_factor
            remaining_value -= remaining_value * min(prev_adjusted_rate, 0.30)
        
        # Depreciation for current year
        depreciation = remaining_value * min(adjusted_rate, 0.30)
        
        return max(depreciation, 0)
    
    def _calculate_financing(self, purchase_price: float, request: OwnershipCostRequest, year: int) -> float:
        """
        Calculate financing cost for a specific year
        
        Args:
            purchase_price: Initial purchase price
            request: Ownership cost request
            year: Current year of ownership
        
        Returns:
            Financing cost for this year
        """
        if not request.financed:
            return 0
        
        # Get financing parameters
        down_payment_percent = request.down_payment_percent or 20
        interest_rate = request.interest_rate or 14
        loan_term = request.loan_term or 4
        
        # Calculate loan amount
        down_payment = purchase_price * (down_payment_percent / 100)
        loan_amount = purchase_price - down_payment
        
        # Simple interest calculation (not amortized for simplicity)
        # In production, you might want to use an amortization schedule
        annual_interest = loan_amount * (interest_rate / 100)
        
        # Only pay interest during the loan term
        if year > loan_term:
            return 0
        
        return annual_interest
    
    def _calculate_insurance(self, vehicle: Dict[str, Any], purchase_price: float, depreciation: float, request: OwnershipCostRequest, year: int) -> float:
        """
        Calculate insurance cost for a specific year
        
        Args:
            vehicle: Vehicle data
            purchase_price: Initial purchase price
            depreciation: Depreciation for this year
            request: Ownership cost request
            year: Current year of ownership
        
        Returns:
            Insurance cost for this year
        """
        # Get current vehicle value (reduced by depreciation)
        current_value = purchase_price
        for y in range(1, year):
            current_value -= self._calculate_depreciation(purchase_price, vehicle.get("depreciation_class", "DEFAULT"), y, request.annual_mileage * y)
        current_value = max(current_value, purchase_price * 0.1)
        
        # Get insurance rate based on type
        insurance_type = getattr(request, 'insurance_type', 'comprehensive')
        rate = self.insurance_rates.get(insurance_type, 0.045)
        
        # Adjust for vehicle age (older vehicles = slightly higher rates)
        age_factor = 1 + (year - 1) * 0.02
        age_factor = min(age_factor, 1.3)
        
        # Adjust for usage type
        usage_factors = {
            "private": 1.0,
            "commercial": 1.3,
            "fleet": 1.2,
            "taxi": 1.5
        }
        usage_factor = usage_factors.get(request.usage_type, 1.0)
        
        # Calculate annual insurance premium
        annual_premium = current_value * rate * age_factor * usage_factor
        
        return max(annual_premium, 5000)  # Minimum insurance cost
    
    def _calculate_licensing(self, year: int) -> float:
        """
        Calculate licensing fees for a specific year
        
        Args:
            year: Current year of ownership
        
        Returns:
            Licensing fee for this year
        """
        # Base licensing fee
        base_fee = 5000
        
        # Increase slightly each year
        year_factor = 1 + (year - 1) * 0.05
        year_factor = min(year_factor, 1.5)
        
        return base_fee * year_factor
    
    def _calculate_resale_value(self, purchase_price: float, depreciation_class: str, years: int, total_mileage: float) -> float:
        """
        Calculate estimated resale value after ownership period
        
        Args:
            purchase_price: Initial purchase price
            depreciation_class: Vehicle depreciation class
            years: Years of ownership
            total_mileage: Total mileage accumulated
        
        Returns:
            Estimated resale value
        """
        # Get base depreciation rate
        rate = self.depreciation_rates.get(depreciation_class, 0.12)
        
        # Calculate remaining value
        remaining_value = purchase_price
        
        for year in range(1, years + 1):
            # Calculate depreciation for each year
            year_factor = 1 - (year - 1) * 0.05
            year_factor = max(year_factor, 0.5)
            
            # Mileage impact
            expected_mileage = year * 20000
            mileage_factor = min(total_mileage / expected_mileage if expected_mileage > 0 else 1, 2.0)
            mileage_factor = 0.8 + (mileage_factor - 0.8) * 0.5
            
            adjusted_rate = rate * year_factor * mileage_factor
            remaining_value -= remaining_value * min(adjusted_rate, 0.30)
        
        return max(remaining_value, purchase_price * 0.05)
