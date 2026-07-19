"""
Ownership Engine - Calculate total cost of vehicle ownership
"""
from typing import Dict, Any, List
import logging
from datetime import datetime

from app.schemas.request import OwnershipCostRequest
from app.schemas.response import OwnershipResponse

logger = logging.getLogger(__name__)


class OwnershipEngine:
    """Engine for calculating total cost of vehicle ownership"""
    
    def calculate_ownership_cost(
        self,
        variant: Dict[str, Any],
        request: OwnershipCostRequest
    ) -> OwnershipResponse:
        """
        Calculate total cost of vehicle ownership
        
        Args:
            variant: Vehicle variant data
            request: Ownership cost calculation request
        
        Returns:
            OwnershipResponse with ownership cost details
        """
        # Extract variant data
        fuel_consumption = variant.get("fuel_consumption", 8.0)  # L/100km
        market_value = variant.get("market_value", request.purchase_price)
        
        # 1. Loan calculation
        loan_amount = max(0, request.purchase_price - request.down_payment)
        monthly_interest_rate = (request.interest_rate / 100) / 12
        total_months = request.loan_term_years * 12
        
        if loan_amount > 0 and monthly_interest_rate > 0:
            monthly_payment = loan_amount * (
                monthly_interest_rate * (1 + monthly_interest_rate) ** total_months
            ) / ((1 + monthly_interest_rate) ** total_months - 1)
            total_interest = (monthly_payment * total_months) - loan_amount
        else:
            monthly_payment = loan_amount / total_months if total_months > 0 else 0
            total_interest = 0
        
        total_loan_cost = monthly_payment * total_months
        
        # 2. Fuel cost
        annual_mileage = request.annual_mileage
        monthly_km = annual_mileage / 12
        fuel_cost_per_km = (fuel_consumption / 100) * request.fuel_price
        annual_fuel_cost = fuel_cost_per_km * annual_mileage
        
        # 3. Insurance cost
        annual_insurance = (request.insurance_rate / 100) * request.purchase_price if request.include_insurance else 0
        
        # 4. Maintenance cost
        annual_maintenance = request.maintenance_cost_per_km * annual_mileage if request.include_maintenance else 0
        
        # 5. Tyre cost
        annual_tyres = request.tyre_cost_per_km * annual_mileage if request.include_tyres else 0
        
        # 6. Depreciation
        if request.include_depreciation:
            # Depreciate 12% annually for the loan term
            annual_depreciation = request.purchase_price * 0.12
            total_depreciation = annual_depreciation * request.loan_term_years
        else:
            annual_depreciation = 0
            total_depreciation = 0
        
        # Total annual running costs
        total_annual_running = annual_fuel_cost + annual_insurance + annual_maintenance + annual_tyres
        
        # Total cost over loan term
        total_running_cost = total_annual_running * request.loan_term_years
        total_cost = total_loan_cost + total_running_cost + request.down_payment
        
        # Affordability score (0-100)
        monthly_income_estimate = (monthly_payment + (total_annual_running / 12)) * 3  # Assumes 33% of income
        affordability_score = min(100, max(0, int(100 - (monthly_payment / monthly_income_estimate * 100))))
        
        # Breakdown
        breakdown = {
            "down_payment": request.down_payment,
            "loan_principal": loan_amount,
            "loan_interest": total_interest,
            "total_loan_payments": total_loan_cost,
            "fuel": total_running_cost * (annual_fuel_cost / total_annual_running) if total_annual_running > 0 else 0,
            "insurance": total_running_cost * (annual_insurance / total_annual_running) if total_annual_running > 0 else 0,
            "maintenance": total_running_cost * (annual_maintenance / total_annual_running) if total_annual_running > 0 else 0,
            "tyres": total_running_cost * (annual_tyres / total_annual_running) if total_annual_running > 0 else 0,
            "depreciation": total_depreciation
        }
        
        # Remove zero values
        breakdown = {k: v for k, v in breakdown.items() if v > 0}
        
        # Recommendations
        recommendations = []
        if monthly_payment > (request.purchase_price * 0.05):
            recommendations.append("Monthly payment is high. Consider a larger down payment or longer loan term.")
        if annual_fuel_cost > total_annual_running * 0.40:
            recommendations.append("Fuel cost is significant. Consider a more fuel-efficient vehicle.")
        if annual_insurance > total_annual_running * 0.20:
            recommendations.append("Insurance cost is high. Shop around for better rates.")
        if affordability_score < 60:
            recommendations.append("Affordability score is low. Consider a less expensive vehicle or better financing terms.")
        else:
            recommendations.append("This vehicle appears to be within affordable range.")
        
        return OwnershipResponse(
            total_cost=round(total_cost, 2),
            monthly_payment=round(monthly_payment, 2),
            total_interest=round(total_interest, 2),
            breakdown=breakdown,
            affordability_score=affordability_score,
            recommendations=recommendations
        )
