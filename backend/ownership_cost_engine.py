# ownership_cost_engine.py
# Auto-D Kenya - Ownership Cost Service Engine
# ================================================================
# TYPE: SERVICE - Core ownership cost calculation engine

import logging
import math
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from config import settings
from database import get_supabase
from utils.helpers import clamp

logger = logging.getLogger(__name__)


class OwnershipCostEngine:
    """
    Ownership Cost Calculation Engine.
    
    Calculates:
    - Total cost of ownership over loan term
    - Monthly payments
    - Total interest paid
    - Cost breakdown by component
    - Loan amortization schedule
    """
    
    def __init__(self):
        self.supabase = get_supabase()
        
        # Base rates
        self.base_rates = {
            "insurance_rate": 0.045,
            "maintenance_rate": 1.50,  # per km
            "tyre_rate": 0.80,  # per km
            "depreciation_rate": 0.15,
            "fuel_consumption": 10.0  # km/l
        }
    
    def calculate_loan_amortization(
        self,
        loan_amount: float,
        annual_interest_rate: float,
        loan_term_years: int
    ) -> Dict[str, Any]:
        """
        Calculate loan amortization schedule.
        
        Args:
            loan_amount: Principal loan amount
            annual_interest_rate: Annual interest rate (%)
            loan_term_years: Loan term in years
            
        Returns:
            Dictionary with amortization details
        """
        monthly_rate = (annual_interest_rate / 100) / 12
        num_payments = loan_term_years * 12
        
        if monthly_rate == 0:
            monthly_payment = loan_amount / num_payments
        else:
            monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
        
        # Build amortization schedule
        schedule = []
        remaining_balance = loan_amount
        total_interest = 0
        
        for month in range(1, num_payments + 1):
            interest_payment = remaining_balance * monthly_rate
            principal_payment = monthly_payment - interest_payment
            
            if remaining_balance < monthly_payment:
                principal_payment = remaining_balance
                monthly_payment = remaining_balance + interest_payment
            
            remaining_balance -= principal_payment
            total_interest += interest_payment
            
            schedule.append({
                "month": month,
                "payment": round(monthly_payment, 2),
                "principal": round(principal_payment, 2),
                "interest": round(interest_payment, 2),
                "balance": round(max(remaining_balance, 0), 2)
            })
            
            if remaining_balance <= 0:
                break
        
        return {
            "monthly_payment": round(monthly_payment, 2),
            "total_payment": round(monthly_payment * len(schedule), 2),
            "total_interest": round(total_interest, 2),
            "schedule": schedule,
            "num_payments": len(schedule)
        }
    
    def calculate_annual_costs(
        self,
        purchase_price: float,
        annual_mileage: float,
        fuel_price: float,
        fuel_consumption: float,
        insurance_rate: float,
        maintenance_per_km: float,
        tyre_per_km: float,
        depreciation_rate: float,
        include_insurance: bool = True,
        include_maintenance: bool = True,
        include_tyres: bool = True,
        include_depreciation: bool = True,
        year: int = 1,
        age: int = 0
    ) -> Dict[str, Any]:
        """
        Calculate annual ownership costs.
        
        Args:
            purchase_price: Vehicle purchase price
            annual_mileage: Annual mileage
            fuel_price: Fuel price per litre
            fuel_consumption: Fuel consumption in km/l
            insurance_rate: Insurance rate (% of value)
            maintenance_per_km: Maintenance cost per km
            tyre_per_km: Tyre cost per km
            depreciation_rate: Annual depreciation rate
            include_insurance: Include insurance
            include_maintenance: Include maintenance
            include_tyres: Include tyres
            include_depreciation: Include depreciation
            year: Current year of ownership
            age: Vehicle age
            
        Returns:
            Dictionary with annual costs
        """
        # Fuel cost
        fuel_cost = (annual_mileage / fuel_consumption) * fuel_price
        
        # Insurance cost (decreases with vehicle age)
        if include_insurance:
            insurance_value = purchase_price * (1 - (depreciation_rate * age))
            insurance_value = max(insurance_value, purchase_price * 0.10)
            insurance_cost = insurance_value * insurance_rate
        else:
            insurance_cost = 0
        
        # Maintenance cost
        if include_maintenance:
            maintenance_cost = annual_mileage * maintenance_per_km
        else:
            maintenance_cost = 0
        
        # Tyre cost
        if include_tyres:
            tyre_cost = annual_mileage * tyre_per_km
        else:
            tyre_cost = 0
        
        # Depreciation cost
        if include_depreciation:
            depreciation_cost = purchase_price * depreciation_rate
        else:
            depreciation_cost = 0
        
        total = fuel_cost + insurance_cost + maintenance_cost + tyre_cost + depreciation_cost
        
        return {
            "fuel": round(fuel_cost, 2),
            "insurance": round(insurance_cost, 2),
            "maintenance": round(maintenance_cost, 2),
            "tyres": round(tyre_cost, 2),
            "depreciation": round(depreciation_cost, 2),
            "total": round(total, 2)
        }
    
    def calculate_ownership_costs(
        self,
        variant_id: str,
        purchase_price: float,
        down_payment: float,
        loan_term_years: int,
        interest_rate: float,
        annual_mileage: float,
        fuel_price: float,
        insurance_rate: float,
        maintenance_cost_per_km: float,
        tyre_cost_per_km: float,
        include_depreciation: bool = True,
        include_insurance: bool = True,
        include_maintenance: bool = True,
        include_tyres: bool = True,
        variant_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete ownership cost calculation.
        
        Args:
            variant_id: Vehicle variant ID
            purchase_price: Vehicle purchase price
            down_payment: Down payment amount
            loan_term_years: Loan term in years
            interest_rate: Annual interest rate
            annual_mileage: Annual mileage
            fuel_price: Fuel price per litre
            insurance_rate: Insurance rate
            maintenance_cost_per_km: Maintenance cost per km
            tyre_cost_per_km: Tyre cost per km
            include_depreciation: Include depreciation
            include_insurance: Include insurance
            include_maintenance: Include maintenance
            include_tyres: Include tyres
            variant_data: Optional pre-fetched variant data
            
        Returns:
            Complete ownership cost result
        """
        try:
            # Get variant data if not provided
            if not variant_data:
                variant_result = self.supabase.table("vehicle_variants").select("*").eq("variant_id", variant_id).execute()
                variant_data = variant_result.data[0] if variant_result.data else {}
            
            # Get fuel consumption from variant
            fuel_consumption = variant_data.get("fuel_consumption_combined", self.base_rates["fuel_consumption"])
            fuel_type = variant_data.get("fuel_type_name", "petrol")
            
            # Calculate loan
            loan_amount = purchase_price - down_payment
            loan_details = self.calculate_loan_amortization(
                loan_amount, interest_rate, loan_term_years
            )
            
            # Calculate annual costs for each year
            yearly_costs = []
            total_cost = 0
            total_interest = loan_details["total_interest"]
            
            depreciation_rate = self.base_rates["depreciation_rate"]
            
            for year in range(1, loan_term_years + 1):
                annual_costs = self.calculate_annual_costs(
                    purchase_price=purchase_price,
                    annual_mileage=annual_mileage,
                    fuel_price=fuel_price,
                    fuel_consumption=fuel_consumption,
                    insurance_rate=insurance_rate,
                    maintenance_per_km=maintenance_cost_per_km,
                    tyre_per_km=tyre_cost_per_km,
                    depreciation_rate=depreciation_rate,
                    include_insurance=include_insurance,
                    include_maintenance=include_maintenance,
                    include_tyres=include_tyres,
                    include_depreciation=include_depreciation,
                    year=year,
                    age=year - 1
                )
                
                yearly_costs.append({
                    "year": year,
                    **annual_costs
                })
                
                total_cost += annual_costs["total"]
            
            # Add loan payments to total
            total_cost += loan_details["total_payment"]
            
            # Calculate monthly cost
            monthly_cost = total_cost / (loan_term_years * 12)
            
            # Build component breakdown
            components = []
            component_totals = {
                "Fuel": 0,
                "Insurance": 0,
                "Maintenance": 0,
                "Tyres": 0,
                "Depreciation": 0,
                "Loan Payment": loan_details["total_payment"]
            }
            
            for year in yearly_costs:
                component_totals["Fuel"] += year["fuel"]
                component_totals["Insurance"] += year["insurance"]
                component_totals["Maintenance"] += year["maintenance"]
                component_totals["Tyres"] += year["tyres"]
                component_totals["Depreciation"] += year["depreciation"]
            
            for name, amount in component_totals.items():
                if amount > 0:
                    percentage = (amount / total_cost) * 100 if total_cost > 0 else 0
                    components.append({
                        "name": name,
                        "amount": round(amount, 2),
                        "percentage": round(percentage, 1)
                    })
            
            return {
                "variant_id": variant_id,
                "purchase_price": purchase_price,
                "down_payment": down_payment,
                "loan_term_years": loan_term_years,
                "interest_rate": interest_rate,
                "annual_mileage": annual_mileage,
                "fuel_price": fuel_price,
                "fuel_consumption": fuel_consumption,
                "fuel_type": fuel_type,
                "total_cost": round(total_cost, 2),
                "monthly_cost": round(monthly_cost, 2),
                "monthly_payment": loan_details["monthly_payment"],
                "total_interest": round(total_interest, 2),
                "total_loan_payment": loan_details["total_payment"],
                "components": components,
                "yearly_costs": yearly_costs,
                "loan_details": {
                    "loan_amount": round(loan_amount, 2),
                    "monthly_payment": loan_details["monthly_payment"],
                    "total_payment": loan_details["total_payment"],
                    "total_interest": round(total_interest, 2),
                    "num_payments": loan_details["num_payments"]
                },
                "amortization_schedule": loan_details["schedule"][:12]  # First 12 months
            }
            
        except Exception as e:
            logger.error(f"Ownership cost calculation error: {str(e)}")
            raise
