# app/modules/ownership/service.py
"""Ownership (TCO) service for Auto-D Kenya"""
import logging
from typing import Dict, Any, List
from datetime import datetime
import math

from app.core.database import get_supabase
from app.modules.ownership.router import TCORequest, TCOResponse, TCOComponent

logger = logging.getLogger(__name__)

class OwnershipService:
    """Service for Total Cost of Ownership calculations"""
    
    def __init__(self):
        self.supabase = get_supabase()
        
        # Base rates
        self.FUEL_PRICES = {
            "petrol": 193.00,
            "diesel": 180.00,
            "electric": 20.00,
            "hybrid": 193.00
        }
        
        self.MAINTENANCE_RATES = {
            "petrol": 2.50,
            "diesel": 3.00,
            "electric": 1.50,
            "hybrid": 2.00
        }
        
        self.TYRE_COST_PER_KM = 0.80
        self.INSURANCE_RATE = 0.03
        
        self.DEPRECIATION_RATES = {
            0: 0.00, 1: 0.20, 2: 0.15, 3: 0.12,
            4: 0.10, 5: 0.08, 6: 0.07, 7: 0.06,
            8: 0.05, 9: 0.04, 10: 0.03
        }
    
    async def get_variant_data(self, variant_id: int) -> Dict[str, Any]:
        """Get variant data from database"""
        try:
            result = self.supabase.table("vehicle_master_specs")\
                .select("*")\
                .eq("variant_id", variant_id)\
                .execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            return {}
        except Exception as e:
            logger.error(f"Error getting variant data: {str(e)}")
            return {}
    
    async def calculate_tco(self, request: TCORequest, user_id: int) -> Dict[str, Any]:
        """Calculate Total Cost of Ownership"""
        # Get variant data
        variant = await self.get_variant_data(request.variant_id)
        if not variant:
            raise ValueError("Variant not found")
        
        fuel_type = variant.get("fuel_type_name", "petrol").lower()
        engine_size = variant.get("engine_size_cc", 1800)
        
        # Calculate loan details
        loan_principal = request.purchase_price - request.down_payment
        monthly_rate = request.interest_rate / 100 / 12
        term_months = request.loan_term_years * 12
        
        if loan_principal > 0 and monthly_rate > 0:
            monthly_payment = loan_principal * (monthly_rate * (1 + monthly_rate) ** term_months) / \
                            ((1 + monthly_rate) ** term_months - 1)
            total_payment = monthly_payment * term_months
            total_interest = total_payment - loan_principal
        else:
            monthly_payment = loan_principal / term_months if term_months > 0 else 0
            total_payment = loan_principal
            total_interest = 0
        
        # Calculate running costs
        annual_mileage = request.annual_mileage
        fuel_efficiency = self._calculate_fuel_efficiency(
            engine_size / 1000, 2024, "mixed", fuel_type
        )
        
        annual_fuel = (annual_mileage / fuel_efficiency) * request.fuel_price
        annual_maintenance = request.maintenance_cost_per_km * annual_mileage
        annual_tyres = request.tyre_cost_per_km * annual_mileage
        annual_insurance = request.purchase_price * (request.insurance_rate / 100)
        
        annual_depreciation = 0
        if request.include_depreciation:
            annual_depreciation = request.purchase_price * 0.12  # Average depreciation
        
        # Total annual running cost
        total_annual_running = annual_fuel + annual_maintenance + annual_tyres + annual_insurance
        
        # Loan term costs
        loan_term_total = total_payment  # This includes principal + interest
        monthly_loan_payment = monthly_payment
        
        # Calculate total ownership cost over loan term
        total_ownership_cost = (
            request.down_payment +  # Down payment
            total_payment +          # Total loan payments
            (total_annual_running * request.loan_term_years)  # Running costs during loan period
        )
        
        if request.include_depreciation:
            total_ownership_cost += annual_depreciation * request.loan_term_years
        
        monthly_total = total_ownership_cost / term_months
        
        # Components breakdown
        components = []
        components.append(TCOComponent(
            name="Purchase Price",
            amount=request.purchase_price,
            percentage=(request.purchase_price / total_ownership_cost) * 100
        ))
        components.append(TCOComponent(
            name="Loan Interest",
            amount=total_interest,
            percentage=(total_interest / total_ownership_cost) * 100
        ))
        components.append(TCOComponent(
            name="Fuel",
            amount=annual_fuel * request.loan_term_years,
            percentage=(annual_fuel * request.loan_term_years / total_ownership_cost) * 100
        ))
        components.append(TCOComponent(
            name="Maintenance",
            amount=annual_maintenance * request.loan_term_years,
            percentage=(annual_maintenance * request.loan_term_years / total_ownership_cost) * 100
        ))
        components.append(TCOComponent(
            name="Tyres",
            amount=annual_tyres * request.loan_term_years,
            percentage=(annual_tyres * request.loan_term_years / total_ownership_cost) * 100
        ))
        components.append(TCOComponent(
            name="Insurance",
            amount=annual_insurance * request.loan_term_years,
            percentage=(annual_insurance * request.loan_term_years / total_ownership_cost) * 100
        ))
        
        if request.include_depreciation:
            components.append(TCOComponent(
                name="Depreciation",
                amount=annual_depreciation * request.loan_term_years,
                percentage=(annual_depreciation * request.loan_term_years / total_ownership_cost) * 100
            ))
        
        # Yearly breakdown
        yearly_breakdown = self._calculate_yearly_breakdown(
            request, fuel_type, annual_fuel, annual_maintenance,
            annual_tyres, annual_insurance, annual_depreciation,
            request.purchase_price, loan_principal, monthly_payment
        )
        
        return {
            "total_cost": round(total_ownership_cost, 2),
            "monthly_cost": round(monthly_total, 2),
            "monthly_payment": round(monthly_loan_payment, 2),
            "total_interest": round(total_interest, 2),
            "components": [c.dict() for c in components],
            "yearly_breakdown": yearly_breakdown,
            "loan_details": {
                "principal": round(loan_principal, 2),
                "interest_rate": request.interest_rate,
                "term_years": request.loan_term_years,
                "term_months": term_months,
                "total_payment": round(total_payment, 2)
            },
            "vehicle_details": {
                "variant_id": request.variant_id,
                "make": variant.get("make_name", ""),
                "model": variant.get("model_name", ""),
                "variant": variant.get("variant_name", ""),
                "fuel_type": fuel_type.capitalize()
            },
            "currency": "KES",
            "calculated_at": datetime.utcnow()
        }
    
    def _calculate_fuel_efficiency(self, engine_size: float, year: int, 
                                   trip_type: str, fuel_type: str) -> float:
        """Calculate fuel efficiency in km/litre"""
        base_efficiency = {
            "petrol": 12.0,
            "diesel": 14.0,
            "electric": 6.0,
            "hybrid": 18.0
        }
        
        efficiency = base_efficiency.get(fuel_type, 12.0)
        efficiency -= (engine_size - 1.5) * 1.5
        year_factor = 1 + ((datetime.now().year - year) * 0.005)
        efficiency *= year_factor
        
        pattern_factors = {
            "urban": 0.8,
            "highway": 1.2,
            "mixed": 1.0,
            "offroad": 0.7
        }
        efficiency *= pattern_factors.get(trip_type, 1.0)
        
        return max(efficiency, 5.0)
    
    def _get_depreciation_rate(self, age: int) -> float:
        """Get depreciation rate based on age"""
        return self.DEPRECIATION_RATES.get(age, 0.08)
    
    def _calculate_yearly_breakdown(self, request: TCORequest, fuel_type: str,
                                   annual_fuel: float, annual_maintenance: float,
                                   annual_tyres: float, annual_insurance: float,
                                   annual_depreciation: float, purchase_price: float,
                                   loan_principal: float, monthly_payment: float) -> List[Dict]:
        """Calculate yearly cost breakdown"""
        breakdown = []
        current_value = purchase_price
        
        for year in range(1, request.loan_term_years + 1):
            age = year
            dep_rate = self._get_depreciation_rate(age)
            yearly_depreciation = current_value * dep_rate
            current_value -= yearly_depreciation
            
            yearly_loan_payment = monthly_payment * 12
            yearly_running = annual_fuel + annual_maintenance + annual_tyres + annual_insurance
            
            total_year = yearly_loan_payment + yearly_running
            
            breakdown.append({
                "year": year,
                "loan_payment": round(yearly_loan_payment, 2),
                "fuel": round(annual_fuel, 2),
                "maintenance": round(annual_maintenance, 2),
                "tyres": round(annual_tyres, 2),
                "insurance": round(annual_insurance, 2),
                "depreciation": round(yearly_depreciation, 2),
                "total": round(total_year, 2),
                "vehicle_value": round(current_value, 2)
            })
        
        return breakdown
