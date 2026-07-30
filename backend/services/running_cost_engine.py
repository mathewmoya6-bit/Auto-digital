# running_cost_engine.py
# Auto-D Kenya - Running Cost Service Engine
# ================================================================
# TYPE: SERVICE - Core running cost calculation engine

import logging
import math
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from config import settings
from database import get_supabase
from utils.helpers import clamp

logger = logging.getLogger(__name__)


class RunningCostEngine:
    """
    Running Cost Calculation Engine.
    
    Calculates:
    - Trip running costs (fuel, service, tyres, insurance, depreciation)
    - Cost per kilometer
    - 5-year cost projections
    - Monthly and annual costs
    - Environmental impact (CO2 emissions)
    """
    
    def __init__(self):
        self.supabase = get_supabase()
        
        # Base rates (can be overridden by database values)
        self.base_rates = {
            "service_per_km": 1.50,
            "tyre_per_km": 0.80,
            "insurance_rate": 0.045,
            "depreciation_rate": 0.15,
            "fuel_consumption_urban": 1.15,
            "fuel_consumption_highway": 0.85,
            "fuel_consumption_mixed": 1.00,
            "co2_per_litre": 2.31  # kg CO2 per litre of petrol
        }
        
        # Driving style factors
        self.driving_factors = {
            "eco": 0.90,
            "normal": 1.00,
            "aggressive": 1.15
        }
        
        # Usage type factors
        self.usage_factors = {
            "private": 1.00,
            "commercial": 1.25,
            "fleet": 0.90,
            "taxi": 1.35
        }
    
    async def get_fuel_price(self, fuel_type: str = "petrol", location: str = "nairobi") -> float:
        """
        Get current fuel price.
        
        Args:
            fuel_type: Type of fuel (petrol, diesel, electric)
            location: Location for price
            
        Returns:
            Fuel price per litre
        """
        try:
            # Try to get from database
            response = self.supabase.table("fuel_prices").select("*").eq("fuel_type", fuel_type).eq("location", location).order("effective_date", desc=True).limit(1).execute()
            
            if response.data and response.data[0].get("price"):
                return float(response.data[0]["price"])
            
            # Fallback to defaults
            defaults = {
                "petrol": settings.DEFAULT_FUEL_PRICE_PETROL,
                "diesel": settings.DEFAULT_FUEL_PRICE_DIESEL,
                "electric": settings.DEFAULT_FUEL_PRICE_ELECTRIC
            }
            return defaults.get(fuel_type.lower(), 200.0)
            
        except Exception as e:
            logger.warning(f"Error getting fuel price: {str(e)}")
            return 200.0
    
    def calculate_fuel_consumption(
        self,
        variant: Dict[str, Any],
        trip_type: str = "mixed",
        driving_style: str = "normal"
    ) -> float:
        """
        Calculate fuel consumption in km/l.
        
        Args:
            variant: Vehicle variant data
            trip_type: urban, highway, mixed, offroad
            driving_style: eco, normal, aggressive
            
        Returns:
            Fuel consumption in km/l
        """
        # Get base consumption from variant
        base_consumption = variant.get("fuel_consumption_combined", 10.0)
        
        # Apply trip type factor
        type_factors = {
            "urban": self.base_rates["fuel_consumption_urban"],
            "highway": self.base_rates["fuel_consumption_highway"],
            "mixed": self.base_rates["fuel_consumption_mixed"],
            "offroad": 1.20
        }
        type_factor = type_factors.get(trip_type, 1.0)
        
        # Apply driving style factor
        style_factor = self.driving_factors.get(driving_style, 1.0)
        
        # Calculate effective consumption
        effective_consumption = base_consumption / (type_factor * style_factor)
        
        return max(effective_consumption, 1.0)
    
    def calculate_fuel_cost(
        self,
        distance: float,
        fuel_consumption: float,
        fuel_price: float
    ) -> float:
        """Calculate fuel cost for a trip."""
        if fuel_consumption <= 0:
            return 0
        fuel_needed = distance / fuel_consumption
        return fuel_needed * fuel_price
    
    def calculate_service_cost(
        self,
        distance: float,
        service_rate: float = None
    ) -> float:
        """Calculate service cost for a trip."""
        rate = service_rate or self.base_rates["service_per_km"]
        return distance * rate
    
    def calculate_tyre_cost(
        self,
        distance: float,
        tyre_rate: float = None
    ) -> float:
        """Calculate tyre cost for a trip."""
        rate = tyre_rate or self.base_rates["tyre_per_km"]
        return distance * rate
    
    def calculate_insurance_cost(
        self,
        purchase_price: float,
        annual_mileage: float,
        distance: float,
        insurance_rate: float = None
    ) -> float:
        """
        Calculate insurance cost for a trip.
        
        Args:
            purchase_price: Vehicle purchase price
            annual_mileage: Annual mileage
            distance: Trip distance
            insurance_rate: Insurance rate (percentage of value)
            
        Returns:
            Insurance cost for the trip
        """
        if annual_mileage <= 0:
            return 0
        
        rate = insurance_rate or self.base_rates["insurance_rate"]
        annual_insurance = purchase_price * rate
        return (annual_insurance / annual_mileage) * distance
    
    def calculate_depreciation_cost(
        self,
        purchase_price: float,
        age: int,
        annual_mileage: float,
        distance: float,
        depreciation_rate: float = None
    ) -> Dict[str, Any]:
        """
        Calculate depreciation cost for a trip.
        
        Returns:
            Dictionary with depreciation cost and remaining value
        """
        if annual_mileage <= 0:
            return {"cost": 0, "remaining_value": purchase_price}
        
        rate = depreciation_rate or self.base_rates["depreciation_rate"]
        
        # Calculate annual depreciation
        annual_depreciation = purchase_price * rate
        
        # Calculate per-km depreciation
        depreciation_per_km = annual_depreciation / annual_mileage
        
        # Calculate trip depreciation
        trip_depreciation = depreciation_per_km * distance
        
        # Calculate remaining value
        remaining_value = purchase_price - (annual_depreciation * age)
        remaining_value = max(remaining_value, purchase_price * 0.10)  # Minimum 10% of original
        
        return {
            "cost": trip_depreciation,
            "remaining_value": remaining_value,
            "annual_depreciation": annual_depreciation,
            "depreciation_per_km": depreciation_per_km
        }
    
    def calculate_loan_payment(
        self,
        purchase_price: float,
        down_payment: float,
        interest_rate: float,
        loan_term: int
    ) -> Dict[str, Any]:
        """
        Calculate loan payments.
        
        Args:
            purchase_price: Vehicle purchase price
            down_payment: Down payment amount
            interest_rate: Annual interest rate (%)
            loan_term: Loan term in years
            
        Returns:
            Dictionary with payment details
        """
        loan_amount = purchase_price - down_payment
        monthly_rate = (interest_rate / 100) / 12
        num_payments = loan_term * 12
        
        if monthly_rate == 0:
            monthly_payment = loan_amount / num_payments
        else:
            monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
        
        total_payment = monthly_payment * num_payments
        total_interest = total_payment - loan_amount
        
        return {
            "loan_amount": loan_amount,
            "monthly_payment": monthly_payment,
            "total_payment": total_payment,
            "total_interest": total_interest,
            "num_payments": num_payments
        }
    
    def calculate_co2_emissions(
        self,
        distance: float,
        fuel_consumption: float,
        fuel_type: str = "petrol"
    ) -> float:
        """
        Calculate CO2 emissions for a trip.
        
        Args:
            distance: Trip distance in km
            fuel_consumption: Fuel consumption in km/l
            fuel_type: Type of fuel
            
        Returns:
            CO2 emissions in kg
        """
        if fuel_type.lower() == "electric":
            return 0
        
        # CO2 per litre for different fuels
        co2_per_litre = {
            "petrol": 2.31,
            "diesel": 2.68,
            "lpg": 1.50,
            "cng": 1.70
        }
        
        co2_factor = co2_per_litre.get(fuel_type.lower(), 2.31)
        
        if fuel_consumption <= 0:
            return 0
        
        fuel_needed = distance / fuel_consumption
        return fuel_needed * co2_factor
    
    async def calculate_running_cost(
        self,
        variant_id: str,
        distance: float,
        annual_mileage: float,
        fuel_price: float,
        trip_type: str = "mixed",
        driving_style: str = "normal",
        usage_type: str = "private",
        location: str = "nairobi",
        condition: str = "good",
        year: int = 2024,
        financed: bool = False,
        down_payment_percent: float = 30,
        interest_rate: float = 16,
        loan_term: int = 4,
        years: int = 5,
        include_insurance: bool = True,
        include_maintenance: bool = True,
        include_tyres: bool = True,
        include_depreciation: bool = True,
        variant_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete running cost calculation.
        
        Args:
            variant_id: Vehicle variant ID
            distance: Trip distance in km
            annual_mileage: Annual mileage in km
            fuel_price: Fuel price per litre
            trip_type: urban, highway, mixed, offroad
            driving_style: eco, normal, aggressive
            usage_type: private, commercial, fleet, taxi
            location: Vehicle location
            condition: Vehicle condition
            year: Year of manufacture
            financed: Whether vehicle is financed
            down_payment_percent: Down payment percentage
            interest_rate: Annual interest rate
            loan_term: Loan term in years
            years: Number of years for projection
            include_insurance: Include insurance in calculation
            include_maintenance: Include maintenance in calculation
            include_tyres: Include tyres in calculation
            include_depreciation: Include depreciation in calculation
            variant_data: Optional pre-fetched variant data
            
        Returns:
            Complete running cost result
        """
        try:
            # Get variant data if not provided
            if not variant_data:
                variant_result = self.supabase.table("vehicle_variants").select("*").eq("variant_id", variant_id).execute()
                variant_data = variant_result.data[0] if variant_result.data else {}
            
            # Get purchase price (from variant or default)
            purchase_price = variant_data.get("base_price", 4500000)
            if not purchase_price or purchase_price <= 0:
                purchase_price = 4500000
            
            # Calculate fuel consumption
            fuel_consumption = self.calculate_fuel_consumption(
                variant_data, trip_type, driving_style
            )
            
            # Get fuel type
            fuel_type = variant_data.get("fuel_type_name", "petrol")
            
            # Calculate individual costs
            fuel_cost_trip = self.calculate_fuel_cost(distance, fuel_consumption, fuel_price)
            service_cost_trip = self.calculate_service_cost(distance) if include_maintenance else 0
            tyre_cost_trip = self.calculate_tyre_cost(distance) if include_tyres else 0
            
            insurance_cost_trip = 0
            if include_insurance:
                insurance_cost_trip = self.calculate_insurance_cost(
                    purchase_price, annual_mileage, distance
                )
            
            depreciation_result = {"cost": 0, "remaining_value": purchase_price}
            if include_depreciation:
                age = datetime.now().year - year
                depreciation_result = self.calculate_depreciation_cost(
                    purchase_price, age, annual_mileage, distance
                )
            
            # Calculate total trip cost
            trip_total = (
                fuel_cost_trip +
                service_cost_trip +
                tyre_cost_trip +
                insurance_cost_trip +
                depreciation_result["cost"]
            )
            
            # Apply usage type factor
            usage_factor = self.usage_factors.get(usage_type, 1.0)
            trip_total *= usage_factor
            
            # Calculate cost per km
            trip_cost_per_km = trip_total / distance if distance > 0 else 0
            
            # Calculate per-km breakdown
            fuel_per_km = fuel_cost_trip / distance if distance > 0 else 0
            service_per_km = service_cost_trip / distance if distance > 0 else 0
            tyre_per_km = tyre_cost_trip / distance if distance > 0 else 0
            insurance_per_km = insurance_cost_trip / distance if distance > 0 else 0
            depreciation_per_km = depreciation_result["cost"] / distance if distance > 0 else 0
            
            # Calculate 5-year projection
            five_year_data = await self.calculate_five_year_projection(
                purchase_price=purchase_price,
                annual_mileage=annual_mileage,
                fuel_price=fuel_price,
                fuel_consumption=fuel_consumption,
                service_rate=self.base_rates["service_per_km"],
                tyre_rate=self.base_rates["tyre_per_km"],
                insurance_rate=self.base_rates["insurance_rate"],
                depreciation_rate=self.base_rates["depreciation_rate"],
                include_insurance=include_insurance,
                include_maintenance=include_maintenance,
                include_tyres=include_tyres,
                include_depreciation=include_depreciation,
                usage_factor=usage_factor,
                financed=financed,
                down_payment_percent=down_payment_percent,
                interest_rate=interest_rate,
                loan_term=loan_term,
                years=years
            )
            
            # Calculate monthly and annual costs
            monthly_fuel = (fuel_cost_trip / distance) * (annual_mileage / 12) if distance > 0 else 0
            monthly_service = service_per_km * (annual_mileage / 12) if include_maintenance else 0
            monthly_tyre = tyre_per_km * (annual_mileage / 12) if include_tyres else 0
            monthly_insurance = insurance_per_km * (annual_mileage / 12) if include_insurance else 0
            monthly_depreciation = depreciation_per_km * (annual_mileage / 12) if include_depreciation else 0
            
            annual_fuel = monthly_fuel * 12
            annual_service = monthly_service * 12
            annual_tyre = monthly_tyre * 12
            annual_insurance = monthly_insurance * 12
            annual_depreciation = monthly_depreciation * 12
            
            # Calculate CO2 emissions
            co2_emissions = self.calculate_co2_emissions(distance, fuel_consumption, fuel_type)
            
            return {
                "variant_id": variant_id,
                "distance": distance,
                "annual_mileage": annual_mileage,
                "fuel_price": fuel_price,
                "fuel_consumption": fuel_consumption,
                "fuel_type": fuel_type,
                "tripTotal": round(trip_total, 2),
                "tripCostPerKm": round(trip_cost_per_km, 2),
                "fuelCostTrip": round(fuel_cost_trip, 2),
                "serviceTrip": round(service_cost_trip, 2),
                "tyreTrip": round(tyre_cost_trip, 2),
                "insuranceTrip": round(insurance_cost_trip, 2),
                "depreciationTrip": round(depreciation_result["cost"], 2),
                "fuelCostPerKm": round(fuel_per_km, 2),
                "servicePerKm": round(service_per_km, 2),
                "tyrePerKm": round(tyre_per_km, 2),
                "insurancePerKm": round(insurance_per_km, 2),
                "depreciationPerKm": round(depreciation_per_km, 2),
                "fiveYearData": five_year_data["yearly_data"],
                "total5YearCost": five_year_data["total_cost"],
                "remainingValue": five_year_data["remaining_value"],
                "ageAdjustedCost": five_year_data["age_adjusted_cost"],
                "monthlyFuel": round(monthly_fuel, 2),
                "monthlyService": round(monthly_service, 2),
                "monthlyInsurance": round(monthly_insurance, 2),
                "monthlyTyre": round(monthly_tyre, 2),
                "monthlyDepreciation": round(monthly_depreciation, 2),
                "annualFuel": round(annual_fuel, 2),
                "annualService": round(annual_service, 2),
                "annualInsurance": round(annual_insurance, 2),
                "annualTyre": round(annual_tyre, 2),
                "annualDepreciation": round(annual_depreciation, 2),
                "co2_emissions": round(co2_emissions, 2),
                "loan_details": five_year_data.get("loan_details", {})
            }
            
        except Exception as e:
            logger.error(f"Running cost calculation error: {str(e)}")
            raise
    
    async def calculate_five_year_projection(
        self,
        purchase_price: float,
        annual_mileage: float,
        fuel_price: float,
        fuel_consumption: float,
        service_rate: float,
        tyre_rate: float,
        insurance_rate: float,
        depreciation_rate: float,
        include_insurance: bool = True,
        include_maintenance: bool = True,
        include_tyres: bool = True,
        include_depreciation: bool = True,
        usage_factor: float = 1.0,
        financed: bool = False,
        down_payment_percent: float = 30,
        interest_rate: float = 16,
        loan_term: int = 4,
        years: int = 5
    ) -> Dict[str, Any]:
        """
        Calculate 5-year cost projection.
        
        Returns:
            Dictionary with yearly data and totals
        """
        yearly_data = []
        total_cost = 0
        current_value = purchase_price
        
        # Calculate loan payments if financed
        loan_details = {}
        if financed:
            down_payment = purchase_price * (down_payment_percent / 100)
            loan_details = self.calculate_loan_payment(
                purchase_price, down_payment, interest_rate, loan_term
            )
            monthly_payment = loan_details["monthly_payment"]
        else:
            monthly_payment = 0
        
        for year in range(1, years + 1):
            # Calculate annual costs
            annual_fuel = (annual_mileage / fuel_consumption) * fuel_price
            annual_service = annual_mileage * service_rate if include_maintenance else 0
            annual_tyre = annual_mileage * tyre_rate if include_tyres else 0
            annual_insurance = purchase_price * insurance_rate if include_insurance else 0
            annual_depreciation = purchase_price * depreciation_rate if include_depreciation else 0
            
            # Apply usage factor
            annual_fuel *= usage_factor
            annual_service *= usage_factor
            annual_tyre *= usage_factor
            
            # Add loan payments if financed
            annual_loan_payment = monthly_payment * 12 if financed and year <= loan_term else 0
            
            # Calculate total for year
            year_total = (
                annual_fuel +
                annual_service +
                annual_tyre +
                annual_insurance +
                annual_depreciation +
                annual_loan_payment
            )
            
            # Update current value
            if include_depreciation:
                current_value -= annual_depreciation
                current_value = max(current_value, purchase_price * 0.10)
            else:
                current_value = purchase_price
            
            yearly_data.append({
                "year": year,
                "fuel": round(annual_fuel, 2),
                "service": round(annual_service, 2),
                "tyres": round(annual_tyre, 2),
                "insurance": round(annual_insurance, 2),
                "depreciation": round(annual_depreciation, 2),
                "loan_payment": round(annual_loan_payment, 2),
                "total": round(year_total, 2),
                "value": round(current_value, 2)
            })
            
            total_cost += year_total
        
        return {
            "yearly_data": yearly_data,
            "total_cost": round(total_cost, 2),
            "remaining_value": round(current_value, 2),
            "age_adjusted_cost": round(total_cost / years, 2),
            "loan_details": loan_details
        }
