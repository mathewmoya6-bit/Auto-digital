"""
Cost Calculator Service
Calculates running costs, ownership costs, and mileage rates
"""

from __future__ import annotations

import logging
import random
from typing import Optional, Dict, List, Any
from datetime import datetime

from app.core.database import supabase
from app.core.config import settings

logger = logging.getLogger(__name__)


class CostCalculator:
    """Service for calculating vehicle costs"""
    
    def __init__(self):
        self.annual_mileage = settings.DEFAULT_ANNUAL_MILEAGE
        self.depreciation_rate = settings.DEFAULT_DEPRECIATION_RATE
        self.insurance_rate = settings.DEFAULT_INSURANCE_RATE
        self.tyre_lifespan = settings.DEFAULT_TYRE_LIFESPAN
        self.service_interval = settings.DEFAULT_SERVICE_INTERVAL
        
        # Cost parameters
        self.fuel_consumption_factors = {
            "urban": settings.FUEL_CONSUMPTION_FACTOR_URBAN,
            "highway": settings.FUEL_CONSUMPTION_FACTOR_HIGHWAY,
            "mixed": settings.FUEL_CONSUMPTION_FACTOR_MIXED
        }
        
        self.depreciation_rates = {
            "suv_a": settings.DEPRECIATION_RATE_SUV_A,
            "suv_b": settings.DEPRECIATION_RATE_SUV_B,
            "suv_c": settings.DEPRECIATION_RATE_SUV_C,
            "suv_d": settings.DEPRECIATION_RATE_SUV_D,
            "sedan_a": settings.DEPRECIATION_RATE_SEDAN_A,
            "sedan_b": settings.DEPRECIATION_RATE_SEDAN_B,
            "sedan_c": settings.DEPRECIATION_RATE_SEDAN_C,
            "sedan_d": settings.DEPRECIATION_RATE_SEDAN_D,
            "pickup_a": settings.DEPRECIATION_RATE_PICKUP_A,
            "pickup_b": settings.DEPRECIATION_RATE_PICKUP_B,
            "pickup_c": settings.DEPRECIATION_RATE_PICKUP_C,
            "luxury_a": settings.DEPRECIATION_RATE_LUXURY_A,
            "luxury_b": settings.DEPRECIATION_RATE_LUXURY_B,
            "luxury_c": settings.DEPRECIATION_RATE_LUXURY_C
        }
    
    def _get_vehicle_details(self, variant_id: str) -> Optional[Dict]:
        """Get vehicle details from database"""
        try:
            result = supabase.table(settings.TABLE_VEHICLE_VARIANTS)\
                .select("*")\
                .eq("id", variant_id)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting vehicle details: {e}")
            return None
    
    def _get_fuel_consumption(self, vehicle: Optional[Dict], driving_style: str = "normal", trip_type: str = "mixed") -> float:
        """Get fuel consumption in L/100km"""
        if not vehicle:
            return 8.0  # Default
        
        # Base consumption from vehicle data
        base_consumption = vehicle.get("fuel_consumption_combined") or vehicle.get("fuel_consumption") or 8.0
        
        # Apply driving style factor
        style_factors = {
            "eco": 0.85,
            "normal": 1.0,
            "aggressive": 1.15
        }
        style_factor = style_factors.get(driving_style, 1.0)
        
        # Apply trip type factor
        trip_factors = {
            "urban": self.fuel_consumption_factors.get("urban", 1.15),
            "highway": self.fuel_consumption_factors.get("highway", 0.85),
            "mixed": self.fuel_consumption_factors.get("mixed", 1.0)
        }
        trip_factor = trip_factors.get(trip_type, 1.0)
        
        return base_consumption * style_factor * trip_factor
    
    def _get_base_price(self, vehicle: Dict) -> float:
        """Get base price for vehicle"""
        # Try to get from database
        if vehicle.get("base_price"):
            return float(vehicle["base_price"])
        if vehicle.get("market_value"):
            return float(vehicle["market_value"])
        if vehicle.get("price"):
            return float(vehicle["price"])
        
        # Estimate based on make
        base_estimates = {
            "Toyota": 3500000,
            "Honda": 3000000,
            "Nissan": 2800000,
            "Mazda": 2700000,
            "Subaru": 3200000,
            "Mercedes": 6000000,
            "BMW": 5500000,
            "Audi": 5000000,
            "Volkswagen": 3500000,
            "Ford": 3000000,
            "Hyundai": 2500000,
            "Kia": 2400000,
            "Suzuki": 1500000,
            "Mitsubishi": 2800000,
            "Land Rover": 7000000,
            "Lexus": 5000000,
            "Porsche": 8000000,
            "Volvo": 4500000,
            "Jeep": 4000000,
            "Chevrolet": 2800000,
            "default": 2500000
        }
        
        make = vehicle.get("make") or vehicle.get("make_name") or "default"
        return base_estimates.get(make, base_estimates["default"])
    
    def _get_depreciation_rate(self, vehicle: Optional[Dict], is_new: bool = True, year: int = 1) -> float:
        """Get depreciation rate based on vehicle type and age"""
        if not vehicle:
            return self.depreciation_rate
        
        body_type = (vehicle.get("body_type") or vehicle.get("body_type_name") or "sedan").lower()
        segment = "A"  # Default segment
        
        # Determine segment based on price or category
        price = self._get_base_price(vehicle)
        if price > 8000000:
            segment = "C"
        elif price > 5000000:
            segment = "B"
        
        # Get rate based on vehicle type and segment
        if body_type in ["suv", "crossover"]:
            rates = {
                "A": self.depreciation_rates.get("suv_a", 0.12),
                "B": self.depreciation_rates.get("suv_b", 0.15),
                "C": self.depreciation_rates.get("suv_c", 0.18),
                "D": self.depreciation_rates.get("suv_d", 0.20)
            }
        elif body_type in ["sedan", "hatchback"]:
            rates = {
                "A": self.depreciation_rates.get("sedan_a", 0.10),
                "B": self.depreciation_rates.get("sedan_b", 0.13),
                "C": self.depreciation_rates.get("sedan_c", 0.16),
                "D": self.depreciation_rates.get("sedan_d", 0.19)
            }
        elif body_type in ["pickup", "truck"]:
            rates = {
                "A": self.depreciation_rates.get("pickup_a", 0.11),
                "B": self.depreciation_rates.get("pickup_b", 0.14),
                "C": self.depreciation_rates.get("pickup_c", 0.17)
            }
        elif body_type in ["luxury", "convertible", "coupe"]:
            rates = {
                "A": self.depreciation_rates.get("luxury_a", 0.20),
                "B": self.depreciation_rates.get("luxury_b", 0.25),
                "C": self.depreciation_rates.get("luxury_c", 0.30)
            }
        else:
            return self.depreciation_rate
        
        base_rate = rates.get(segment, self.depreciation_rate)
        
        # Adjust for new/used
        if not is_new:
            base_rate *= 0.8
        
        # Adjust for age (depreciation slows over time)
        if year > 3:
            base_rate *= 0.9
        if year > 5:
            base_rate *= 0.85
        
        return max(0.05, min(0.35, base_rate))
    
    def _get_vehicle_age(self, year: int) -> int:
        """Calculate vehicle age"""
        current_year = datetime.now().year
        return max(0, current_year - year)
    
    # ─── Cost Calculation Methods ─────────────────────────────────────
    
    def _calculate_fuel_cost(self, distance: float, fuel_consumption: float, fuel_price: float) -> float:
        """Calculate fuel cost for a trip"""
        # fuel_consumption is in L/100km
        # distance is in km
        litres_needed = (distance / 100) * fuel_consumption
        return litres_needed * fuel_price
    
    def _calculate_service_cost(self, distance: float, vehicle: Optional[Dict] = None) -> float:
        """Calculate service cost for a trip"""
        # Service cost per km
        service_cost_per_km = 1.5  # Base rate
        
        if vehicle:
            # Adjust based on vehicle type
            body_type = (vehicle.get("body_type") or vehicle.get("body_type_name") or "").lower()
            if body_type in ["suv", "luxury"]:
                service_cost_per_km = 2.5
            elif body_type in ["pickup", "truck"]:
                service_cost_per_km = 2.0
            elif body_type in ["hatchback", "sedan"]:
                service_cost_per_km = 1.2
            
            # Adjust based on age
            if vehicle.get("year"):
                age = self._get_vehicle_age(vehicle["year"])
                if age > 10:
                    service_cost_per_km *= 1.5
                elif age > 5:
                    service_cost_per_km *= 1.2
        
        return distance * service_cost_per_km
    
    def _calculate_tyre_cost(self, distance: float, vehicle: Optional[Dict] = None) -> float:
        """Calculate tyre cost for a trip"""
        tyre_cost_per_km = 1.0  # Base rate
        
        if vehicle:
            # Adjust based on tyre size
            tyre_size = vehicle.get("tyre_size") or ""
            if tyre_size:
                # Larger tyres cost more
                if "18" in tyre_size or "19" in tyre_size or "20" in tyre_size:
                    tyre_cost_per_km = 1.5
                elif "16" in tyre_size or "17" in tyre_size:
                    tyre_cost_per_km = 1.2
            
            # SUV tyres cost more
            body_type = (vehicle.get("body_type") or vehicle.get("body_type_name") or "").lower()
            if body_type in ["suv", "pickup", "truck"]:
                tyre_cost_per_km *= 1.3
        
        return distance * tyre_cost_per_km
    
    def _calculate_insurance_cost(self, distance: float, annual_km: float, base_price: float, year: int) -> float:
        """Calculate insurance cost for a trip"""
        age = self._get_vehicle_age(year)
        
        # Insurance rate based on vehicle age
        if age < 3:
            rate = 0.045
        elif age < 7:
            rate = 0.04
        else:
            rate = 0.035
        
        annual_insurance = base_price * rate
        insurance_per_km = annual_insurance / annual_km if annual_km > 0 else 0
        
        return distance * insurance_per_km
    
    def _calculate_depreciation_cost(self, distance: float, annual_km: float, base_price: float, year: int, vehicle: Optional[Dict] = None) -> float:
        """Calculate depreciation cost for a trip"""
        dep_rate = self._get_depreciation_rate(vehicle, year=1)
        annual_depreciation = base_price * dep_rate
        depreciation_per_km = annual_depreciation / annual_km if annual_km > 0 else 0
        
        return distance * depreciation_per_km
    
    def _calculate_financing_cost(self, base_price: float, down_payment_percent: float, interest_rate: float, loan_term: int, annual_km: float, distance: float) -> float:
        """Calculate financing cost per trip"""
        loan_amount = base_price * (1 - down_payment_percent / 100)
        monthly_rate = interest_rate / 100 / 12
        total_payments = loan_term * 12
        
        # Calculate monthly payment (simple loan)
        monthly_payment = loan_amount * monthly_rate / (1 - (1 + monthly_rate) ** -total_payments) if monthly_rate > 0 else loan_amount / total_payments
        
        annual_payment = monthly_payment * 12
        payment_per_km = annual_payment / annual_km if annual_km > 0 else 0
        
        return distance * payment_per_km
    
    def _calculate_insurance_cost_for_year(self, value: float, rate: float, insurance_type: str) -> float:
        """Calculate insurance cost for a year"""
        if insurance_type == "third_party":
            return 7000
        elif insurance_type == "third_party_fire":
            return 15000
        else:  # comprehensive
            return value * rate
    
    def _calculate_maintenance_cost(self, annual_mileage: float, age: int, vehicle: Optional[Dict] = None) -> float:
        """Calculate maintenance cost for a year"""
        base_maintenance = 15000
        
        if vehicle:
            body_type = (vehicle.get("body_type") or vehicle.get("body_type_name") or "").lower()
            if body_type in ["suv", "luxury"]:
                base_maintenance *= 1.4
            elif body_type in ["pickup", "truck"]:
                base_maintenance *= 1.2
        
        # Age factor
        age_factor = 1 + (age - 1) * 0.08
        base_maintenance *= age_factor
        
        # Mileage factor
        mileage_factor = annual_mileage / 20000
        base_maintenance *= mileage_factor
        
        return base_maintenance
    
    def _calculate_tyre_cost_per_year(self, annual_mileage: float, vehicle: Optional[Dict] = None) -> float:
        """Calculate tyre cost for a year"""
        tyre_lifespan = self.tyre_lifespan
        tyre_cost = 40000
        
        if vehicle:
            tyre_size = vehicle.get("tyre_size") or ""
            if tyre_size:
                if "18" in tyre_size or "19" in tyre_size or "20" in tyre_size:
                    tyre_cost = 60000
                elif "16" in tyre_size or "17" in tyre_size:
                    tyre_cost = 50000
        
        return (annual_mileage / tyre_lifespan) * tyre_cost
    
    def _calculate_financing_cost_for_year(self, base_price: float, down_payment_percent: float, interest_rate: float, loan_term: int, year: int) -> float:
        """Calculate financing cost for a specific year"""
        if year > loan_term:
            return 0
        
        loan_amount = base_price * (1 - down_payment_percent / 100)
        total_interest = loan_amount * (interest_rate / 100) * loan_term
        annual_interest = total_interest / loan_term
        
        return annual_interest + (loan_amount / loan_term)
    
    def _calculate_five_year_projection(self, base_price: float, annual_km: float, fuel_price: float, fuel_consumption: float, vehicle: Optional[Dict] = None, year: int = 2020) -> List[Dict]:
        """Calculate 5-year cost projection"""
        years_data = []
        current_value = base_price
        
        for i in range(1, 6):
            dep_rate = self._get_depreciation_rate(vehicle, year=1)
            depreciation = current_value * dep_rate
            current_value -= depreciation
            
            # Inflation factor
            inflation = 1 + (i - 1) * 0.04
            
            yearly_fuel = (annual_km / 100) * fuel_consumption * fuel_price * inflation
            yearly_service = self._calculate_maintenance_cost(annual_km, i, vehicle) * (1 + (i - 1) * 0.05)
            yearly_insurance = self._calculate_insurance_cost_for_year(current_value, self.insurance_rate, "comprehensive") * (1 + (i - 1) * 0.03)
            yearly_tyres = self._calculate_tyre_cost_per_year(annual_km, vehicle) * (1 + (i - 1) * 0.04)
            
            yearly_total = depreciation + yearly_fuel + yearly_service + yearly_insurance + yearly_tyres
            
            years_data.append({
                "year": i,
                "depreciation": round(depreciation, 2),
                "fuel": round(yearly_fuel, 2),
                "service": round(yearly_service, 2),
                "insurance": round(yearly_insurance, 2),
                "tyres": round(yearly_tyres, 2),
                "total": round(yearly_total, 2),
                "value": round(current_value, 2)
            })
        
        return years_data
    
    # ─── Public Methods ───────────────────────────────────────────────
    
    def calculate_running_cost(
        self,
        variant_id: str,
        year: int,
        mileage: float,
        annual_km: float,
        fuel_price: float,
        driving_style: str = "normal",
        trip_type: str = "mixed",
        usage_type: str = "private",
        location: str = "nairobi",
        distance: float = 150,
        financed: bool = False,
        down_payment_percent: float = 30,
        interest_rate: float = 16,
        loan_term: int = 4
    ) -> Dict:
        """Calculate running cost for a trip"""
        
        # Get vehicle details
        vehicle = self._get_vehicle_details(variant_id)
        
        # Get base cost parameters
        fuel_consumption = self._get_fuel_consumption(vehicle, driving_style, trip_type)
        base_price = self._get_base_price(vehicle) if vehicle else 3000000
        
        # Calculate per-trip costs
        fuel_cost = self._calculate_fuel_cost(
            distance=distance,
            fuel_consumption=fuel_consumption,
            fuel_price=fuel_price
        )
        
        service_cost = self._calculate_service_cost(
            distance=distance,
            vehicle=vehicle
        )
        
        tyre_cost = self._calculate_tyre_cost(
            distance=distance,
            vehicle=vehicle
        )
        
        insurance_cost = self._calculate_insurance_cost(
            distance=distance,
            annual_km=annual_km,
            base_price=base_price,
            year=year
        )
        
        depreciation_cost = self._calculate_depreciation_cost(
            distance=distance,
            annual_km=annual_km,
            base_price=base_price,
            year=year,
            vehicle=vehicle
        )
        
        # Financing cost (if applicable)
        financing_cost = 0
        if financed:
            financing_cost = self._calculate_financing_cost(
                base_price=base_price,
                down_payment_percent=down_payment_percent,
                interest_rate=interest_rate,
                loan_term=loan_term,
                annual_km=annual_km,
                distance=distance
            )
        
        # Total cost
        total_cost = fuel_cost + service_cost + tyre_cost + insurance_cost + depreciation_cost + financing_cost
        cost_per_km = total_cost / distance if distance > 0 else 0
        
        # Monthly and annual projections
        monthly_km = annual_km / 12
        monthly_cost = cost_per_km * monthly_km
        annual_cost = cost_per_km * annual_km
        
        # 5-year projection
        five_year_data = self._calculate_five_year_projection(
            base_price=base_price,
            annual_km=annual_km,
            fuel_price=fuel_price,
            fuel_consumption=fuel_consumption,
            vehicle=vehicle,
            year=year
        )
        
        return {
            "trip": {
                "distance": distance,
                "total_cost": round(total_cost, 2),
                "cost_per_km": round(cost_per_km, 2)
            },
            "breakdown": {
                "fuel": round(fuel_cost, 2),
                "service": round(service_cost, 2),
                "tyres": round(tyre_cost, 2),
                "insurance": round(insurance_cost, 2),
                "depreciation": round(depreciation_cost, 2),
                "financing": round(financing_cost, 2)
            },
            "monthly": {
                "fuel": round(fuel_cost * monthly_km / distance, 2) if distance > 0 else 0,
                "service": round(service_cost * monthly_km / distance, 2) if distance > 0 else 0,
                "tyres": round(tyre_cost * monthly_km / distance, 2) if distance > 0 else 0,
                "insurance": round(insurance_cost * monthly_km / distance, 2) if distance > 0 else 0,
                "depreciation": round(depreciation_cost * monthly_km / distance, 2) if distance > 0 else 0,
                "financing": round(financing_cost * monthly_km / distance, 2) if distance > 0 else 0,
                "total": round(monthly_cost, 2)
            },
            "annual": {
                "fuel": round(fuel_cost * annual_km / distance, 2) if distance > 0 else 0,
                "service": round(service_cost * annual_km / distance, 2) if distance > 0 else 0,
                "tyres": round(tyre_cost * annual_km / distance, 2) if distance > 0 else 0,
                "insurance": round(insurance_cost * annual_km / distance, 2) if distance > 0 else 0,
                "depreciation": round(depreciation_cost * annual_km / distance, 2) if distance > 0 else 0,
                "financing": round(financing_cost * annual_km / distance, 2) if distance > 0 else 0,
                "total": round(annual_cost, 2)
            },
            "five_year": five_year_data,
            "vehicle": {
                "make": vehicle.get("make") if vehicle else "Unknown",
                "model": vehicle.get("model") if vehicle else "Unknown",
                "variant": vehicle.get("variant") if vehicle else "Unknown",
                "fuel_type": vehicle.get("fuel_type") if vehicle else "Unknown",
                "fuel_consumption": round(fuel_consumption, 2)
            } if vehicle else None,
            "parameters": {
                "annual_km": annual_km,
                "fuel_price": fuel_price,
                "driving_style": driving_style,
                "trip_type": trip_type,
                "usage_type": usage_type,
                "location": location,
                "financed": financed
            }
        }
    
    def calculate_ownership_cost(
        self,
        variant_id: str,
        year: int,
        initial_value: float,
        current_value: float,
        annual_mileage: float,
        ownership_years: int,
        insurance_rate: float,
        insurance_type: str = "comprehensive",
        fuel_price: float = 200,
        location: str = "nairobi",
        is_new: bool = True,
        is_financed: bool = False,
        down_payment_percent: float = 30,
        interest_rate: float = 16,
        loan_term: int = 4
    ) -> Dict:
        """Calculate total cost of ownership"""
        
        # Get vehicle details
        vehicle = self._get_vehicle_details(variant_id)
        
        # Get fuel consumption
        fuel_consumption = self._get_fuel_consumption(vehicle) if vehicle else 8
        
        # Calculate yearly breakdown
        years_data = []
        total_cost = 0
        current_value_remaining = current_value
        
        for i in range(ownership_years):
            year_num = i + 1
            
            # Depreciation
            dep_rate = self._get_depreciation_rate(vehicle, is_new, year_num)
            depreciation = current_value_remaining * dep_rate
            current_value_remaining -= depreciation
            
            # Fuel cost
            fuel_cost = (annual_mileage / 100) * fuel_consumption * fuel_price * (1 + i * 0.04)
            
            # Insurance cost
            insurance = self._calculate_insurance_cost_for_year(
                value=current_value_remaining,
                rate=insurance_rate,
                insurance_type=insurance_type
            ) * (1 + i * 0.03)
            
            # Maintenance cost
            maintenance = self._calculate_maintenance_cost(
                annual_mileage=annual_mileage,
                age=year_num,
                vehicle=vehicle
            )
            
            # Tyre cost
            tyre_cost = self._calculate_tyre_cost_per_year(
                annual_mileage=annual_mileage,
                vehicle=vehicle
            ) * (1 + i * 0.04)
            
            # Licensing cost
            licensing = current_value_remaining * 0.01
            
            # Financing cost (if applicable)
            financing = 0
            if is_financed and i < loan_term:
                financing = self._calculate_financing_cost_for_year(
                    base_price=initial_value,
                    down_payment_percent=down_payment_percent,
                    interest_rate=interest_rate,
                    loan_term=loan_term,
                    year=year_num
                )
            
            # Year total
            year_total = depreciation + fuel_cost + insurance + maintenance + tyre_cost + licensing + financing
            total_cost += year_total
            
            years_data.append({
                "year": year_num,
                "depreciation": round(depreciation, 2),
                "fuel": round(fuel_cost, 2),
                "insurance": round(insurance, 2),
                "maintenance": round(maintenance, 2),
                "tyres": round(tyre_cost, 2),
                "licensing": round(licensing, 2),
                "financing": round(financing, 2),
                "total": round(year_total, 2),
                "value": round(current_value_remaining, 2)
            })
        
        # Summary
        average_monthly = total_cost / (ownership_years * 12)
        cost_per_km = total_cost / (annual_mileage * ownership_years) if annual_mileage > 0 else 0
        
        return {
            "total_cost": round(total_cost, 2),
            "average_monthly": round(average_monthly, 2),
            "cost_per_km": round(cost_per_km, 2),
            "resale_value": round(current_value_remaining, 2),
            "years": years_data,
            "vehicle": {
                "make": vehicle.get("make") if vehicle else "Unknown",
                "model": vehicle.get("model") if vehicle else "Unknown",
                "variant": vehicle.get("variant") if vehicle else "Unknown"
            } if vehicle else None,
            "parameters": {
                "annual_mileage": annual_mileage,
                "ownership_years": ownership_years,
                "insurance_rate": insurance_rate,
                "insurance_type": insurance_type,
                "fuel_price": fuel_price,
                "is_new": is_new,
                "is_financed": is_financed
            }
        }
    
    def calculate_mileage_rate(
        self,
        variant_id: str,
        year: int,
        fuel_price: float,
        annual_km: float = 20000,
        driving_style: str = "normal"
    ) -> Dict:
        """Calculate mileage rate per km"""
        
        vehicle = self._get_vehicle_details(variant_id)
        fuel_consumption = self._get_fuel_consumption(vehicle, driving_style)
        base_price = self._get_base_price(vehicle) if vehicle else 3000000
        
        # Fuel cost per km
        fuel_cost_per_km = (fuel_consumption / 100) * fuel_price
        
        # Service cost per km
        service_cost_per_km = self._calculate_service_cost(distance=1, vehicle=vehicle)
        
        # Tyre cost per km
        tyre_cost_per_km = self._calculate_tyre_cost(distance=1, vehicle=vehicle)
        
        # Insurance cost per km
        insurance_per_km = self._calculate_insurance_cost(
            distance=1,
            annual_km=annual_km,
            base_price=base_price,
            year=year
        )
        
        # Depreciation per km
        dep_per_km = self._calculate_depreciation_cost(
            distance=1,
            annual_km=annual_km,
            base_price=base_price,
            year=year,
            vehicle=vehicle
        )
        
        total_per_km = fuel_cost_per_km + service_cost_per_km + tyre_cost_per_km + insurance_per_km + dep_per_km
        
        return {
            "cost_per_km": round(total_per_km, 2),
            "breakdown": {
                "fuel": round(fuel_cost_per_km, 2),
                "service": round(service_cost_per_km, 2),
                "tyres": round(tyre_cost_per_km, 2),
                "insurance": round(insurance_per_km, 2),
                "depreciation": round(dep_per_km, 2)
            },
            "annual_cost": round(total_per_km * annual_km, 2),
            "monthly_cost": round(total_per_km * annual_km / 12, 2),
            "fuel_consumption": round(fuel_consumption, 2),
            "vehicle": {
                "make": vehicle.get("make") if vehicle else "Unknown",
                "model": vehicle.get("model") if vehicle else "Unknown"
            } if vehicle else None
        }
    
    def _fallback_calculation(self, distance: float, fuel_price: float, annual_km: float) -> Dict:
        """Fallback calculation when vehicle not found"""
        fuel_consumption = 8.0
        fuel_cost = (distance / 100) * fuel_consumption * fuel_price
        service_cost = distance * 1.5
        tyre_cost = distance * 1.0
        insurance_cost = distance * 2.0
        depreciation_cost = distance * 3.0
        
        total = fuel_cost + service_cost + tyre_cost + insurance_cost + depreciation_cost
        
        return {
            "trip": {
                "distance": distance,
                "total_cost": round(total, 2),
                "cost_per_km": round(total / distance, 2) if distance > 0 else 0
            },
            "breakdown": {
                "fuel": round(fuel_cost, 2),
                "service": round(service_cost, 2),
                "tyres": round(tyre_cost, 2),
                "insurance": round(insurance_cost, 2),
                "depreciation": round(depreciation_cost, 2)
            },
            "vehicle": None,
            "parameters": {
                "annual_km": annual_km,
                "fuel_price": fuel_price,
                "note": "Using default values (vehicle not found)"
            }
        }
