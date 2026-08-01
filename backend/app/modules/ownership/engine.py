# app/modules/ownership/engine.py
"""Ownership (TCO) Calculation Engine for Auto-D Kenya"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import math

from app.modules.ownership.schemas import TCORequest

logger = logging.getLogger(__name__)


class TCOEngine:
    """
    Total Cost of Ownership Calculation Engine.
    
    Calculates comprehensive TCO including:
    - Purchase price with condition adjustment
    - Loan financing (principal, interest, monthly payment)
    - Running costs (fuel, maintenance, tyres, insurance)
    - Depreciation with yearly rates
    - Inflation adjustment
    - Year-by-year breakdown
    - Cost per KM
    - Resale value
    - Component percentage breakdown
    """
    
    def __init__(self):
        # ─── Fuel Prices (KES/L) ──────────────────────────────────
        self.FUEL_PRICES = {
            "petrol": 200.00,
            "diesel": 190.00,
            "electric": 0.00,
            "hybrid": 180.00,
            "lpg": 150.00,
            "cng": 140.00
        }
        
        # ─── Maintenance Rates (KES/km) ──────────────────────────
        self.MAINTENANCE_RATES = {
            "petrol": 2.50,
            "diesel": 3.00,
            "electric": 1.50,
            "hybrid": 2.00,
            "lpg": 2.20,
            "cng": 2.00
        }
        
        # ─── Tyre Cost ────────────────────────────────────────────
        self.TYRE_COST_PER_KM = 0.80
        
        # ─── Insurance Rate ──────────────────────────────────────
        self.INSURANCE_RATE = 0.03
        
        # ─── Depreciation Rates (by age) ─────────────────────────
        self.DEPRECIATION_RATES = {
            0: 0.00, 1: 0.20, 2: 0.15, 3: 0.12,
            4: 0.10, 5: 0.08, 6: 0.07, 7: 0.06,
            8: 0.05, 9: 0.04, 10: 0.03, 11: 0.03,
            12: 0.03, 13: 0.02, 14: 0.02, 15: 0.02
        }
        
        # ─── Fuel Efficiency Base (km/L) ─────────────────────────
        self.BASE_FUEL_EFFICIENCY = {
            "petrol": 12.0,
            "diesel": 14.0,
            "electric": 6.0,
            "hybrid": 18.0,
            "lpg": 11.0,
            "cng": 10.0
        }
        
        # ─── Vehicle Condition Factors ───────────────────────────
        self.CONDITION_FACTORS = {
            "new": 1.00,
            "used": 0.85
        }
        
        # ─── Vehicle Type Factors ────────────────────────────────
        self.VEHICLE_TYPE_FACTORS = {
            "ice": 1.00,
            "hybrid": 0.95,
            "ev": 0.90
        }
        
        # ─── Inflation Rate ──────────────────────────────────────
        self.INFLATION_RATE = 0.02  # 2% annual
        
        # ─── Minimum Resale Value ────────────────────────────────
        self.MIN_RESALE_PERCENTAGE = 0.15  # 15% of purchase price
    
    def calculate(self, request: TCORequest, variant_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Total Cost of Ownership.
        
        Args:
            request: TCORequest with all input parameters
            variant_data: Vehicle variant data from database
            
        Returns:
            Dict with complete TCO breakdown
        """
        # ─── Extract and validate inputs ──────────────────────────
        fuel_type = request.fuel_type or variant_data.get("fuel_type_name", "petrol").lower()
        engine_size = variant_data.get("engine_size_cc", 1800)
        
        # Apply condition factor
        condition_factor = self.CONDITION_FACTORS.get(request.vehicle_condition, 1.00)
        adjusted_purchase_price = request.purchase_price * condition_factor
        
        # Apply vehicle type factor
        vehicle_type_factor = self.VEHICLE_TYPE_FACTORS.get(request.vehicle_type, 1.00)
        adjusted_purchase_price *= vehicle_type_factor
        
        # ─── Calculate fuel efficiency ────────────────────────────
        fuel_efficiency = self._calculate_fuel_efficiency(
            engine_size=engine_size / 1000,
            year=request.vehicle_year,
            fuel_type=fuel_type
        )
        
        # ─── Calculate annual costs ──────────────────────────────
        annual_fuel = self._calculate_annual_fuel(
            annual_mileage=request.annual_mileage,
            fuel_efficiency=fuel_efficiency,
            fuel_price=request.fuel_price
        )
        
        annual_maintenance = self._calculate_annual_maintenance(
            annual_mileage=request.annual_mileage,
            maintenance_rate=request.maintenance_cost_per_km,
            fuel_type=fuel_type
        )
        
        annual_tyres = self._calculate_annual_tyres(
            annual_mileage=request.annual_mileage,
            tyre_rate=request.tyre_cost_per_km
        )
        
        annual_insurance = self._calculate_annual_insurance(
            purchase_price=adjusted_purchase_price,
            insurance_rate=request.insurance_rate
        )
        
        annual_depreciation = self._calculate_annual_depreciation(
            purchase_price=adjusted_purchase_price,
            vehicle_year=request.vehicle_year,
            include_depreciation=request.include_depreciation
        )
        
        # ─── Calculate loan details ───────────────────────────────
        loan_details = self._calculate_loan(
            purchase_price=adjusted_purchase_price,
            down_payment=request.down_payment,
            loan_term_years=request.loan_term_years,
            interest_rate=request.interest_rate,
            purchase_type=request.purchase_type
        )
        
        # ─── Calculate yearly breakdown ────────────────────────────
        yearly_breakdown = self._calculate_yearly_breakdown(
            request=request,
            adjusted_purchase_price=adjusted_purchase_price,
            annual_fuel=annual_fuel,
            annual_maintenance=annual_maintenance,
            annual_tyres=annual_tyres,
            annual_insurance=annual_insurance,
            annual_depreciation=annual_depreciation,
            monthly_payment=loan_details["monthly_payment"],
            loan_principal=loan_details["principal"],
            include_depreciation=request.include_depreciation,
            include_inflation=request.include_inflation
        )
        
        # ─── Calculate totals ──────────────────────────────────────
        total_running_cost = sum(y["running_cost"] for y in yearly_breakdown)
        total_depreciation = sum(y["depreciation"] for y in yearly_breakdown) if request.include_depreciation else 0
        total_loan_payment = sum(y["loan_payment"] for y in yearly_breakdown)
        total_cost = sum(y["total_cost"] for y in yearly_breakdown)
        
        # Add down payment or full cash price
        if request.purchase_type == "finance":
            total_cost += request.down_payment
        else:
            total_cost += adjusted_purchase_price
        
        # ─── Calculate derived metrics ─────────────────────────────
        total_km = request.annual_mileage * request.loan_term_years
        cost_per_km = total_cost / total_km if total_km > 0 else 0
        
        monthly_cost = total_cost / (request.loan_term_years * 12) if request.loan_term_years > 0 else 0
        
        # Resale value
        resale_value = adjusted_purchase_price - total_depreciation
        resale_value = max(resale_value, adjusted_purchase_price * self.MIN_RESALE_PERCENTAGE)
        
        # ─── Build components breakdown ────────────────────────────
        components = self._build_components(
            adjusted_purchase_price=adjusted_purchase_price,
            total_interest=loan_details["total_interest"],
            total_running_cost=total_running_cost,
            total_depreciation=total_depreciation,
            total_cost=total_cost
        )
        
        # ─── Build vehicle details ─────────────────────────────────
        vehicle_details = {
            "variant_id": request.variant_id,
            "make": variant_data.get("make_name", ""),
            "model": variant_data.get("model_name", ""),
            "variant": variant_data.get("variant_name", ""),
            "fuel_type": fuel_type.capitalize(),
            "fuel_type_display": fuel_type.capitalize(),
            "vehicle_condition": request.vehicle_condition,
            "purchase_type": request.purchase_type,
            "vehicle_year": request.vehicle_year
        }
        
        # ─── Return complete response ─────────────────────────────
        return {
            # Summary
            "total_cost": round(total_cost, 2),
            "monthly_cost": round(monthly_cost, 2),
            "monthly_payment": round(loan_details["monthly_payment"], 2),
            "total_interest": round(loan_details["total_interest"], 2),
            "cost_per_km": round(cost_per_km, 2),
            "total_depreciation": round(total_depreciation, 2),
            "resale_value": round(resale_value, 2),
            
            # Components
            "components": components,
            
            # Yearly breakdown
            "yearly_breakdown": yearly_breakdown,
            
            # Loan details
            "loan_details": {
                "principal": round(loan_details["principal"], 2),
                "interest_rate": request.interest_rate,
                "term_years": request.loan_term_years,
                "term_months": loan_details["term_months"],
                "total_payment": round(loan_details["total_payment"], 2),
                "purchase_type": request.purchase_type
            },
            
            # Vehicle details
            "vehicle_details": vehicle_details,
            
            # Metadata
            "currency": "KES",
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    # ─── PRIVATE CALCULATION METHODS ──────────────────────────────
    
    def _calculate_fuel_efficiency(self, engine_size: float, year: int, fuel_type: str) -> float:
        """Calculate fuel efficiency in km/litre."""
        base = self.BASE_FUEL_EFFICIENCY.get(fuel_type, 12.0)
        
        # Engine size adjustment
        efficiency = base - max(0, (engine_size - 1.5) * 1.5)
        
        # Age adjustment
        age = datetime.now().year - year
        year_factor = max(0.75, 1 - age * 0.01)
        efficiency *= year_factor
        
        return max(efficiency, 5.0)
    
    def _calculate_annual_fuel(self, annual_mileage: float, fuel_efficiency: float, fuel_price: float) -> float:
        """Calculate annual fuel cost."""
        if fuel_efficiency <= 0:
            return 0
        return (annual_mileage / fuel_efficiency) * fuel_price
    
    def _calculate_annual_maintenance(self, annual_mileage: float, maintenance_rate: float, fuel_type: str) -> float:
        """Calculate annual maintenance cost."""
        # Use provided rate or fallback to default
        if maintenance_rate > 0:
            return maintenance_rate * annual_mileage
        return self.MAINTENANCE_RATES.get(fuel_type, 2.50) * annual_mileage
    
    def _calculate_annual_tyres(self, annual_mileage: float, tyre_rate: float) -> float:
        """Calculate annual tyre cost."""
        if tyre_rate > 0:
            return tyre_rate * annual_mileage
        return self.TYRE_COST_PER_KM * annual_mileage
    
    def _calculate_annual_insurance(self, purchase_price: float, insurance_rate: float) -> float:
        """Calculate annual insurance cost."""
        return purchase_price * (insurance_rate / 100)
    
    def _calculate_annual_depreciation(self, purchase_price: float, vehicle_year: int, include_depreciation: bool) -> float:
        """Calculate annual depreciation."""
        if not include_depreciation:
            return 0
        
        age = max(0, datetime.now().year - vehicle_year)
        dep_rate = self._get_depreciation_rate(age)
        return purchase_price * dep_rate
    
    def _get_depreciation_rate(self, age: int) -> float:
        """Get depreciation rate based on age."""
        clamped_age = min(age, 15)
        return self.DEPRECIATION_RATES.get(clamped_age, 0.08)
    
    def _calculate_loan(self, purchase_price: float, down_payment: float,
                       loan_term_years: int, interest_rate: float,
                       purchase_type: str) -> Dict[str, Any]:
        """Calculate loan details."""
        term_months = loan_term_years * 12
        
        if purchase_type == "finance":
            principal = max(0, purchase_price - down_payment)
            monthly_rate = interest_rate / 100 / 12
            
            if principal > 0 and monthly_rate > 0:
                monthly_payment = principal * (monthly_rate * (1 + monthly_rate) ** term_months) / \
                                ((1 + monthly_rate) ** term_months - 1)
                total_payment = monthly_payment * term_months
                total_interest = total_payment - principal
            else:
                monthly_payment = principal / term_months if term_months > 0 else 0
                total_payment = principal
                total_interest = 0
        else:
            # Cash purchase
            principal = 0
            monthly_payment = 0
            total_payment = 0
            total_interest = 0
        
        return {
            "principal": principal,
            "monthly_payment": monthly_payment,
            "total_payment": total_payment,
            "total_interest": total_interest,
            "term_months": term_months
        }
    
    def _calculate_yearly_breakdown(
        self,
        request: TCORequest,
        adjusted_purchase_price: float,
        annual_fuel: float,
        annual_maintenance: float,
        annual_tyres: float,
        annual_insurance: float,
        annual_depreciation: float,
        monthly_payment: float,
        loan_principal: float,
        include_depreciation: bool,
        include_inflation: bool
    ) -> List[Dict[str, Any]]:
        """Calculate yearly cost breakdown."""
        breakdown = []
        current_value = adjusted_purchase_price
        remaining_loan = loan_principal
        inflation_rate = self.INFLATION_RATE if include_inflation else 0
        
        for year in range(1, request.loan_term_years + 1):
            # Apply inflation (compounded)
            inflation_multiplier = (1 + inflation_rate) ** (year - 1)
            
            # Running costs with inflation
            yearly_fuel = annual_fuel * inflation_multiplier
            yearly_maintenance = annual_maintenance * inflation_multiplier
            yearly_tyres = annual_tyres * inflation_multiplier
            yearly_insurance = annual_insurance * inflation_multiplier
            
            # Depreciation
            age = request.vehicle_year + year - 1
            dep_rate = self._get_depreciation_rate(datetime.now().year - age)
            yearly_depreciation = current_value * dep_rate
            current_value -= yearly_depreciation
            
            # Loan payment
            if request.purchase_type == "finance" and year <= request.loan_term_years:
                yearly_loan_payment = monthly_payment * 12
                # Simple remaining balance (amortization)
                if remaining_loan > 0:
                    interest_for_year = remaining_loan * (request.interest_rate / 100)
                    principal_paid = yearly_loan_payment - interest_for_year
                    remaining_loan = max(0, remaining_loan - principal_paid)
            else:
                yearly_loan_payment = 0
            
            # Running costs total
            yearly_running = yearly_fuel + yearly_maintenance + yearly_tyres + yearly_insurance
            
            # Total for year
            total_year = yearly_loan_payment + yearly_running
            if include_depreciation:
                total_year += yearly_depreciation
            
            breakdown.append({
                "year": year,
                "total_cost": round(total_year, 2),
                "depreciation": round(yearly_depreciation, 2) if include_depreciation else 0,
                "running_cost": round(yearly_running, 2),
                "insurance": round(yearly_insurance, 2),
                "loan_payment": round(yearly_loan_payment, 2),
                "fuel": round(yearly_fuel, 2),
                "maintenance": round(yearly_maintenance, 2),
                "tyres": round(yearly_tyres, 2),
                "vehicle_value": round(max(current_value, 0), 2)
            })
        
        return breakdown
    
    def _build_components(
        self,
        adjusted_purchase_price: float,
        total_interest: float,
        total_running_cost: float,
        total_depreciation: float,
        total_cost: float
    ) -> List[Dict[str, Any]]:
        """Build cost components breakdown."""
        components = []
        
        # Purchase Price
        components.append({
            "name": "Purchase Price",
            "amount": round(adjusted_purchase_price, 2),
            "percentage": round((adjusted_purchase_price / total_cost) * 100, 1) if total_cost > 0 else 0
        })
        
        # Loan Interest (only if > 0)
        if total_interest > 0:
            components.append({
                "name": "Loan Interest",
                "amount": round(total_interest, 2),
                "percentage": round((total_interest / total_cost) * 100, 1) if total_cost > 0 else 0
            })
        
        # Running costs (approximate split - actual from yearly breakdown)
        # We'll split by rough percentages from the calculation
        components.append({
            "name": "Running Costs",
            "amount": round(total_running_cost, 2),
            "percentage": round((total_running_cost / total_cost) * 100, 1) if total_cost > 0 else 0
        })
        
        # Depreciation
        if total_depreciation > 0:
            components.append({
                "name": "Depreciation",
                "amount": round(total_depreciation, 2),
                "percentage": round((total_depreciation / total_cost) * 100, 1) if total_cost > 0 else 0
            })
        
        return components


# ─── FACTORY FUNCTION ──────────────────────────────────────────────

def get_tco_engine() -> TCOEngine:
    """Factory function to get TCO engine instance."""
    return TCOEngine()
