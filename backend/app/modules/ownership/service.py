# app/modules/ownership/service.py
"""Ownership (TCO) service for Auto-D Kenya"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import math
import secrets

from app.core.database import get_supabase
from app.modules.ownership.schemas import TCORequest, TCOResponse

logger = logging.getLogger(__name__)


class OwnershipService:
    """Service for Total Cost of Ownership calculations"""
    
    def __init__(self):
        self.supabase = get_supabase()
        
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
        
        # ─── Depreciation Rates ──────────────────────────────────
        self.DEPRECIATION_RATES = {
            0: 0.00, 1: 0.20, 2: 0.15, 3: 0.12,
            4: 0.10, 5: 0.08, 6: 0.07, 7: 0.06,
            8: 0.05, 9: 0.04, 10: 0.03, 11: 0.03,
            12: 0.03, 13: 0.02, 14: 0.02, 15: 0.02
        }
        
        # ─── Fuel Descriptions ────────────────────────────────────
        self.FUEL_DESCRIPTIONS = {
            "petrol": "Petrol: Standard fuel for most vehicles",
            "diesel": "Diesel: More efficient, higher torque",
            "hybrid": "Hybrid: Combined petrol + electric",
            "lpg": "LPG: Liquefied Petroleum Gas",
            "electric": "Electric: Zero emissions, low running cost",
            "cng": "CNG: Compressed Natural Gas"
        }
        
        # ─── Vehicle Condition Factors ───────────────────────────
        self.CONDITION_FACTORS = {
            "new": 1.00,
            "used": 0.85
        }
        
        # ─── Purchase Type Factors ───────────────────────────────
        self.PURCHASE_FACTORS = {
            "cash": 1.00,
            "finance": 1.00  # Interest handled separately
        }
    
    async def get_variant_data(self, variant_id: int) -> Dict[str, Any]:
        """Get variant data from database"""
        try:
            # Try vehicle_master_specs view first
            result = self.supabase.table("vehicle_master_specs")\
                .select("*")\
                .eq("variant_id", variant_id)\
                .execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            # Fallback to vehicle_variants
            result = self.supabase.table("vehicle_variants")\
                .select("*")\
                .eq("id", variant_id)\
                .execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            return {}
        except Exception as e:
            logger.error(f"Error getting variant data: {str(e)}")
            return {}
    
    async def calculate_tco(self, request: TCORequest, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculate Total Cost of Ownership
        
        Matches the HTML frontend with all options:
        - Vehicle Type (ICE, Hybrid, EV)
        - Fuel Type (Petrol, Diesel, Hybrid, LPG, Electric)
        - Vehicle Condition (New, Used)
        - Purchase Type (Cash, Financing)
        """
        # ─── Get variant data ────────────────────────────────────
        variant = await self.get_variant_data(request.variant_id)
        if not variant:
            raise ValueError("Variant not found")
        
        fuel_type = request.fuel_type or variant.get("fuel_type_name", "petrol").lower()
        engine_size = variant.get("engine_size_cc", 1800)
        
        # ─── Apply vehicle condition factor ──────────────────────
        condition_factor = self.CONDITION_FACTORS.get(request.vehicle_condition, 1.00)
        adjusted_purchase_price = request.purchase_price * condition_factor
        
        # ─── Calculate loan details ──────────────────────────────
        if request.purchase_type == "finance":
            loan_principal = adjusted_purchase_price - request.down_payment
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
        else:
            # Cash purchase
            loan_principal = 0
            monthly_payment = 0
            total_payment = 0
            total_interest = 0
            term_months = request.loan_term_years * 12
        
        # ─── Calculate running costs ─────────────────────────────
        annual_mileage = request.annual_mileage
        
        # Fuel efficiency
        fuel_efficiency = self._calculate_fuel_efficiency(
            engine_size / 1000, 
            request.vehicle_year, 
            "mixed", 
            fuel_type
        )
        
        # Annual costs
        annual_fuel = (annual_mileage / max(fuel_efficiency, 0.1)) * request.fuel_price
        annual_maintenance = request.maintenance_cost_per_km * annual_mileage
        annual_tyres = request.tyre_cost_per_km * annual_mileage
        annual_insurance = adjusted_purchase_price * (request.insurance_rate / 100)
        
        # Annual depreciation
        annual_depreciation = 0
        if request.include_depreciation:
            # Use depreciation rate based on vehicle age
            age = max(0, datetime.now().year - request.vehicle_year)
            dep_rate = self._get_depreciation_rate(age)
            annual_depreciation = adjusted_purchase_price * dep_rate
        
        # ─── Apply inflation ──────────────────────────────────────
        inflation_rate = 0.02  # 2% default
        if request.include_inflation:
            # Apply inflation to running costs
            for year in range(1, request.loan_term_years + 1):
                annual_fuel *= (1 + inflation_rate)
                annual_maintenance *= (1 + inflation_rate)
                annual_tyres *= (1 + inflation_rate)
                annual_insurance *= (1 + inflation_rate)
        
        # ─── Total annual running cost ────────────────────────────
        total_annual_running = annual_fuel + annual_maintenance + annual_tyres + annual_insurance
        
        # ─── Calculate total ownership cost ───────────────────────
        down_payment = request.down_payment if request.purchase_type == "finance" else adjusted_purchase_price
        
        total_ownership_cost = (
            down_payment +  # Down payment or full cash price
            total_payment +  # Total loan payments (0 for cash)
            (total_annual_running * request.loan_term_years)  # Running costs during ownership
        )
        
        if request.include_depreciation:
            total_ownership_cost += annual_depreciation * request.loan_term_years
        
        monthly_total = total_ownership_cost / term_months if term_months > 0 else total_ownership_cost / 12
        
        # ─── Cost per KM ──────────────────────────────────────────
        total_km = annual_mileage * request.loan_term_years
        cost_per_km = total_ownership_cost / total_km if total_km > 0 else 0
        
        # ─── Resale value ─────────────────────────────────────────
        resale_value = adjusted_purchase_price - (annual_depreciation * request.loan_term_years)
        resale_value = max(resale_value, adjusted_purchase_price * 0.15)  # Minimum 15% value
        
        # ─── Components breakdown ──────────────────────────────────
        components = []
        total = total_ownership_cost
        
        # Purchase Price component
        components.append({
            "name": "Purchase Price",
            "amount": round(adjusted_purchase_price, 2),
            "percentage": round((adjusted_purchase_price / total) * 100, 1) if total > 0 else 0
        })
        
        # Loan Interest component (only if financed)
        if request.purchase_type == "finance" and total_interest > 0:
            components.append({
                "name": "Loan Interest",
                "amount": round(total_interest, 2),
                "percentage": round((total_interest / total) * 100, 1) if total > 0 else 0
            })
        
        # Fuel component
        fuel_total = annual_fuel * request.loan_term_years
        components.append({
            "name": "Fuel",
            "amount": round(fuel_total, 2),
            "percentage": round((fuel_total / total) * 100, 1) if total > 0 else 0
        })
        
        # Maintenance component
        maintenance_total = annual_maintenance * request.loan_term_years
        components.append({
            "name": "Maintenance",
            "amount": round(maintenance_total, 2),
            "percentage": round((maintenance_total / total) * 100, 1) if total > 0 else 0
        })
        
        # Tyres component
        tyres_total = annual_tyres * request.loan_term_years
        components.append({
            "name": "Tyres",
            "amount": round(tyres_total, 2),
            "percentage": round((tyres_total / total) * 100, 1) if total > 0 else 0
        })
        
        # Insurance component
        insurance_total = annual_insurance * request.loan_term_years
        components.append({
            "name": "Insurance",
            "amount": round(insurance_total, 2),
            "percentage": round((insurance_total / total) * 100, 1) if total > 0 else 0
        })
        
        if request.include_depreciation:
            depreciation_total = annual_depreciation * request.loan_term_years
            components.append({
                "name": "Depreciation",
                "amount": round(depreciation_total, 2),
                "percentage": round((depreciation_total / total) * 100, 1) if total > 0 else 0
            })
        
        # ─── Yearly breakdown ─────────────────────────────────────
        yearly_breakdown = self._calculate_yearly_breakdown(
            request=request,
            fuel_type=fuel_type,
            annual_fuel=annual_fuel,
            annual_maintenance=annual_maintenance,
            annual_tyres=annual_tyres,
            annual_insurance=annual_insurance,
            annual_depreciation=annual_depreciation,
            purchase_price=adjusted_purchase_price,
            loan_principal=loan_principal,
            monthly_payment=monthly_payment,
            total_interest=total_interest,
            include_depreciation=request.include_depreciation,
            include_inflation=request.include_inflation,
            inflation_rate=inflation_rate
        )
        
        # ─── Build response ──────────────────────────────────────
        return {
            # Summary
            "total_cost": round(total_ownership_cost, 2),
            "monthly_cost": round(monthly_total, 2),
            "monthly_payment": round(monthly_payment, 2),
            "total_interest": round(total_interest, 2),
            "cost_per_km": round(cost_per_km, 2),
            "total_depreciation": round(annual_depreciation * request.loan_term_years, 2),
            "resale_value": round(resale_value, 2),
            
            # Components
            "components": components,
            
            # Yearly breakdown
            "yearly_breakdown": yearly_breakdown,
            
            # Loan details
            "loan_details": {
                "principal": round(loan_principal, 2),
                "interest_rate": request.interest_rate,
                "term_years": request.loan_term_years,
                "term_months": term_months,
                "total_payment": round(total_payment, 2),
                "purchase_type": request.purchase_type
            },
            
            # Vehicle details
            "vehicle_details": {
                "variant_id": request.variant_id,
                "make": variant.get("make_name", ""),
                "model": variant.get("model_name", ""),
                "variant": variant.get("variant_name", ""),
                "fuel_type": fuel_type.capitalize(),
                "fuel_type_display": fuel_type.capitalize(),
                "vehicle_condition": request.vehicle_condition,
                "purchase_type": request.purchase_type,
                "vehicle_year": request.vehicle_year
            },
            
            "currency": "KES",
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    def _calculate_fuel_efficiency(self, engine_size: float, year: int, 
                                   trip_type: str, fuel_type: str) -> float:
        """Calculate fuel efficiency in km/litre"""
        base_efficiency = {
            "petrol": 12.0,
            "diesel": 14.0,
            "electric": 6.0,
            "hybrid": 18.0,
            "lpg": 11.0,
            "cng": 10.0
        }
        
        efficiency = base_efficiency.get(fuel_type, 12.0)
        efficiency -= max(0, (engine_size - 1.5) * 1.5)
        
        age = datetime.now().year - year
        year_factor = max(0.75, 1 - age * 0.01)
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
        clamped_age = min(age, 15)
        return self.DEPRECIATION_RATES.get(clamped_age, 0.08)
    
    def _calculate_yearly_breakdown(
        self,
        request: TCORequest,
        fuel_type: str,
        annual_fuel: float,
        annual_maintenance: float,
        annual_tyres: float,
        annual_insurance: float,
        annual_depreciation: float,
        purchase_price: float,
        loan_principal: float,
        monthly_payment: float,
        total_interest: float,
        include_depreciation: bool,
        include_inflation: bool,
        inflation_rate: float
    ) -> List[Dict]:
        """Calculate yearly cost breakdown"""
        breakdown = []
        current_value = purchase_price
        remaining_loan = loan_principal
        
        for year in range(1, request.loan_term_years + 1):
            # Apply inflation to running costs
            if include_inflation and year > 1:
                inflation_multiplier = (1 + inflation_rate) ** (year - 1)
                yearly_fuel = annual_fuel * inflation_multiplier
                yearly_maintenance = annual_maintenance * inflation_multiplier
                yearly_tyres = annual_tyres * inflation_multiplier
                yearly_insurance = annual_insurance * inflation_multiplier
            else:
                yearly_fuel = annual_fuel
                yearly_maintenance = annual_maintenance
                yearly_tyres = annual_tyres
                yearly_insurance = annual_insurance
            
            # Depreciation
            age = request.vehicle_year + year - 1
            dep_rate = self._get_depreciation_rate(datetime.now().year - age)
            yearly_depreciation = current_value * dep_rate
            current_value -= yearly_depreciation
            
            # Loan payment
            if request.purchase_type == "finance" and year <= request.loan_term_years:
                yearly_loan_payment = monthly_payment * 12
                # Calculate remaining balance (simplified)
                remaining_loan -= (yearly_loan_payment - (remaining_loan * (request.interest_rate / 100)))
                remaining_loan = max(0, remaining_loan)
            else:
                yearly_loan_payment = 0
            
            # Running costs
            yearly_running = yearly_fuel + yearly_maintenance + yearly_tyres + yearly_insurance
            
            # Total
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
                "vehicle_value": round(current_value, 2)
            })
        
        return breakdown
