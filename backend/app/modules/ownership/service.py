# app/modules/ownership/service.py
"""Ownership (TCO) service for Auto-D Kenya"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import math
import secrets

from app.core.database import get_supabase
from app.modules.ownership.schemas import TCORequest

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
        
        # ─── Vehicle Type Factors ─────────────────────────────────
        self.VEHICLE_TYPE_FACTORS = {
            "ice": 1.00,
            "hybrid": 0.95,
            "ev": 0.90
        }
        
        # ─── Purchase Type Factors ───────────────────────────────
        self.PURCHASE_FACTORS = {
            "cash": 1.00,
            "finance": 1.00  # Interest handled separately
        }
        
        # ─── Trip Type Fuel Efficiency Multipliers ──────────────
        self.TRIP_TYPE_FACTORS = {
            "urban": 0.80,
            "highway": 1.20,
            "mixed": 1.00,
            "offroad": 0.70,
            "city": 0.80,
            "suburban": 0.90,
            "rural": 1.00
        }
        
        # ─── Driving Style Factors ──────────────────────────────
        self.DRIVING_STYLE_FACTORS = {
            "eco": 1.15,
            "normal": 1.00,
            "aggressive": 0.85
        }
        
        # ─── Usage Type Factors ──────────────────────────────────
        self.USAGE_TYPE_FACTORS = {
            "private": 1.00,
            "commercial": 1.20,
            "fleet": 0.90,
            "taxi": 1.30
        }
    
    async def get_crsp_data(self, crsp_id: int) -> Dict[str, Any]:
        """
        Get the vehicle's full record from vehicle_crsp_lookup.

        This view already carries make/model/trim_level/engine_capacity/
        fuel/transmission/body_type/crsp_kes — it IS the "variant" now,
        since the frontend selects vehicles from this view directly
        (same as the Instant Value Check tool) instead of a separate
        variant table.
        """
        try:
            result = self.supabase.table("vehicle_crsp_lookup")\
                .select("*")\
                .eq("crsp_id", crsp_id)\
                .execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            return {}
        except Exception as e:
            logger.error(f"Error getting CRSP data: {str(e)}")
            return {}
    
    async def calculate_tco(self, request: TCORequest, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculate Total Cost of Ownership

        Matches the HTML frontend with all options:
        - Vehicle Type (ICE, Hybrid, EV)
        - Fuel Type (Petrol, Diesel, Hybrid, LPG, Electric)
        - Vehicle Condition (New, Used)
        - Purchase Type (Cash, Financing)

        The vehicle is looked up once, by `vehicle_crsp_id`, straight
        from `vehicle_crsp_lookup` — there is no separate variant_id/
        variant-table lookup anymore.
        """
        # ─── Get vehicle (CRSP) data — the single source of truth ──
        crsp_data = await self.get_crsp_data(request.vehicle_crsp_id)
        if not crsp_data:
            raise ValueError(f"No vehicle found for vehicle_crsp_id={request.vehicle_crsp_id}")

        # ─── Determine fuel type ─────────────────────────────────
        fuel_type = (request.fuel_type or crsp_data.get("fuel", "petrol") or "petrol").lower()
        engine_size = crsp_data.get("engine_capacity") or 1800
        
        # ─── Apply vehicle condition factor ──────────────────────
        condition_factor = self.CONDITION_FACTORS.get(request.vehicle_condition, 1.00)
        adjusted_purchase_price = request.purchase_price * condition_factor
        
        # ─── Apply vehicle type factor ───────────────────────────
        vehicle_type_factor = self.VEHICLE_TYPE_FACTORS.get(request.vehicle_type, 1.00)
        adjusted_purchase_price *= vehicle_type_factor
        
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
            loan_principal = 0
            monthly_payment = 0
            total_payment = 0
            total_interest = 0
            term_months = request.loan_term_years * 12
        
        # ─── Calculate running costs ─────────────────────────────
        annual_mileage = request.annual_mileage
        
        # Fuel efficiency with all factors
        fuel_efficiency = self._calculate_fuel_efficiency(
            engine_size=engine_size / 1000,
            year=request.vehicle_year,
            trip_type="mixed",
            fuel_type=fuel_type,
            driving_style="normal"
        )
        
        # Annual costs
        annual_fuel = (annual_mileage / max(fuel_efficiency, 0.1)) * request.fuel_price
        annual_maintenance = request.maintenance_cost_per_km * annual_mileage
        annual_tyres = request.tyre_cost_per_km * annual_mileage
        annual_insurance = adjusted_purchase_price * (request.insurance_rate / 100)
        
        # Apply usage type factor (default: private)
        usage_factor = self.USAGE_TYPE_FACTORS.get("private", 1.00)
        annual_maintenance *= usage_factor
        annual_tyres *= usage_factor
        
        # ─── Annual depreciation ─────────────────────────────────
        annual_depreciation = 0
        if request.include_depreciation:
            age = max(0, datetime.now().year - request.vehicle_year)
            dep_rate = self._get_depreciation_rate(age)
            annual_depreciation = adjusted_purchase_price * dep_rate
        
        # ─── Apply inflation to running costs ────────────────────
        inflation_rate = 0.02
        if request.include_inflation:
            inflated_fuel = annual_fuel
            inflated_maintenance = annual_maintenance
            inflated_tyres = annual_tyres
            inflated_insurance = annual_insurance
            for _ in range(1, request.loan_term_years + 1):
                inflated_fuel *= (1 + inflation_rate)
                inflated_maintenance *= (1 + inflation_rate)
                inflated_tyres *= (1 + inflation_rate)
                inflated_insurance *= (1 + inflation_rate)
            annual_fuel = inflated_fuel
            annual_maintenance = inflated_maintenance
            annual_tyres = inflated_tyres
            annual_insurance = inflated_insurance
        
        # ─── Total annual running cost ────────────────────────────
        total_annual_running = annual_fuel + annual_maintenance + annual_tyres + annual_insurance
        
        # ─── Calculate total ownership cost ───────────────────────
        down_payment = request.down_payment if request.purchase_type == "finance" else adjusted_purchase_price
        
        total_ownership_cost = (
            down_payment +
            total_payment +
            (total_annual_running * request.loan_term_years)
        )
        
        if request.include_depreciation:
            total_ownership_cost += annual_depreciation * request.loan_term_years
        
        monthly_total = total_ownership_cost / term_months if term_months > 0 else total_ownership_cost / 12
        
        # ─── Cost per KM ──────────────────────────────────────────
        total_km = annual_mileage * request.loan_term_years
        cost_per_km = total_ownership_cost / total_km if total_km > 0 else 0
        
        # ─── Resale value ─────────────────────────────────────────
        total_depreciation = annual_depreciation * request.loan_term_years
        resale_value = adjusted_purchase_price - total_depreciation
        resale_value = max(resale_value, adjusted_purchase_price * 0.15)
        
        # ─── Monthly breakdown ────────────────────────────────────
        monthly_loan = monthly_payment
        monthly_fuel = annual_fuel / 12
        monthly_maintenance = annual_maintenance / 12
        monthly_tyres = annual_tyres / 12
        monthly_insurance = annual_insurance / 12
        monthly_running_total = monthly_fuel + monthly_maintenance + monthly_tyres + monthly_insurance
        
        # ─── Components breakdown ──────────────────────────────────
        components = []
        total = total_ownership_cost
        
        if adjusted_purchase_price > 0:
            components.append({
                "name": "Purchase Price",
                "amount": round(adjusted_purchase_price, 2),
                "percentage": round((adjusted_purchase_price / total) * 100, 1) if total > 0 else 0
            })
        
        if request.purchase_type == "finance" and total_interest > 0:
            components.append({
                "name": "Loan Interest",
                "amount": round(total_interest, 2),
                "percentage": round((total_interest / total) * 100, 1) if total > 0 else 0
            })
        
        fuel_total = annual_fuel * request.loan_term_years
        components.append({
            "name": "Fuel",
            "amount": round(fuel_total, 2),
            "percentage": round((fuel_total / total) * 100, 1) if total > 0 else 0
        })
        
        maintenance_total = annual_maintenance * request.loan_term_years
        components.append({
            "name": "Maintenance",
            "amount": round(maintenance_total, 2),
            "percentage": round((maintenance_total / total) * 100, 1) if total > 0 else 0
        })
        
        tyres_total = annual_tyres * request.loan_term_years
        components.append({
            "name": "Tyres",
            "amount": round(tyres_total, 2),
            "percentage": round((tyres_total / total) * 100, 1) if total > 0 else 0
        })
        
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
        
        components.sort(key=lambda x: x["amount"], reverse=True)
        
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
        
        # ─── Running Cost Index ──────────────────────────────────
        rci = self._calculate_rci(cost_per_km)
        
        # ─── Build response ──────────────────────────────────────
        return {
            "total_cost": round(total_ownership_cost, 2),
            "monthly_cost": round(monthly_total, 2),
            "monthly_payment": round(monthly_payment, 2),
            "total_interest": round(total_interest, 2),
            "cost_per_km": round(cost_per_km, 2),
            "total_depreciation": round(total_depreciation, 2),
            "resale_value": round(resale_value, 2),
            
            "monthly_breakdown": {
                "loan_payment": round(monthly_loan, 2),
                "fuel": round(monthly_fuel, 2),
                "maintenance": round(monthly_maintenance, 2),
                "tyres": round(monthly_tyres, 2),
                "insurance": round(monthly_insurance, 2),
                "total": round(monthly_running_total, 2)
            },
            
            "components": components,
            "yearly_breakdown": yearly_breakdown,
            
            "rci": {
                "value": round(rci, 2),
                "label": self._get_rci_label(rci),
                "stars": self._get_rci_stars(rci),
                "class": self._get_rci_class(rci)
            },
            
            "loan_details": {
                "principal": round(loan_principal, 2),
                "interest_rate": request.interest_rate,
                "term_years": request.loan_term_years,
                "term_months": term_months,
                "total_payment": round(total_payment, 2),
                "purchase_type": request.purchase_type
            },
            
            "vehicle_details": {
                "vehicle_crsp_id": request.vehicle_crsp_id,
                "make": crsp_data.get("make", ""),
                "model": crsp_data.get("model", ""),
                "variant": crsp_data.get("trim_level", ""),
                "fuel_type": fuel_type.capitalize(),
                "fuel_type_display": fuel_type.capitalize(),
                "vehicle_condition": request.vehicle_condition,
                "purchase_type": request.purchase_type,
                "vehicle_year": request.vehicle_year,
                "vehicle_type": request.vehicle_type,
                "engine_capacity": crsp_data.get("engine_capacity", engine_size),
                "transmission": crsp_data.get("transmission", ""),
                "body_type": crsp_data.get("body_type", "")
            },
            
            "crsp_reference": {
                "crsp_kes": crsp_data.get("crsp_kes"),
                "crsp_year": crsp_data.get("crsp_year"),
                "manufacture_year": crsp_data.get("manufacture_year"),
                "is_matched": bool(crsp_data)
            },
            
            "currency": "KES",
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    def _calculate_fuel_efficiency(self, engine_size: float, year: int, 
                                   trip_type: str, fuel_type: str,
                                   driving_style: str = "normal") -> float:
        """Calculate fuel efficiency in km/litre with all factors"""
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
        
        efficiency *= self.TRIP_TYPE_FACTORS.get(trip_type, 1.0)
        efficiency *= self.DRIVING_STYLE_FACTORS.get(driving_style, 1.0)
        
        return max(efficiency, 4.0)
    
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
        """Calculate yearly cost breakdown with inflation"""
        breakdown = []
        current_value = purchase_price
        remaining_loan = loan_principal
        
        for year in range(1, request.loan_term_years + 1):
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
            
            if include_depreciation:
                age = request.vehicle_year + year - 1
                current_age = datetime.now().year - age
                dep_rate = self._get_depreciation_rate(current_age)
                yearly_depreciation = current_value * dep_rate
                current_value -= yearly_depreciation
            else:
                yearly_depreciation = 0
                current_value = purchase_price - (purchase_price * (year / request.loan_term_years))
            
            if request.purchase_type == "finance" and year <= request.loan_term_years:
                yearly_loan_payment = monthly_payment * 12
                if year == 1:
                    remaining_loan = loan_principal
                annual_interest = remaining_loan * (request.interest_rate / 100)
                annual_principal = yearly_loan_payment - annual_interest
                remaining_loan -= annual_principal
                remaining_loan = max(0, remaining_loan)
            else:
                yearly_loan_payment = 0
            
            yearly_running = yearly_fuel + yearly_maintenance + yearly_tyres + yearly_insurance
            
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
    
    def _calculate_rci(self, cost_per_km: float) -> float:
        """Calculate Running Cost Index (RCI)"""
        if cost_per_km <= 0:
            return 0
        rci = (cost_per_km / 50) * 100
        return min(rci, 200)
    
    def _get_rci_label(self, rci: float) -> str:
        """Get RCI label based on value"""
        if rci <= 40:
            return "Excellent"
        elif rci <= 70:
            return "Good"
        elif rci <= 100:
            return "Average"
        elif rci <= 140:
            return "Expensive"
        else:
            return "Very Expensive"
    
    def _get_rci_stars(self, rci: float) -> str:
        """Get RCI stars based on value"""
        if rci <= 40:
            return "★★★★★"
        elif rci <= 70:
            return "★★★★"
        elif rci <= 100:
            return "★★★"
        elif rci <= 140:
            return "★★"
        else:
            return "★"
    
    def _get_rci_class(self, rci: float) -> str:
        """Get RCI CSS class based on value"""
        if rci <= 40:
            return "excellent"
        elif rci <= 70:
            return "good"
        elif rci <= 100:
            return "average"
        elif rci <= 140:
            return "expensive"
        else:
            return "very-expensive"
