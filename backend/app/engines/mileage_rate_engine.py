"""
Mileage Rate Engine - Calculate cost per kilometer using database and scraper data
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from app.schemas.request import MileageRateRequest
from app.schemas.response import MileageRateResponse
from app.services.data_service import DataService

logger = logging.getLogger(__name__)


class MileageRateEngine:
    """Engine for calculating cost per kilometer with database data"""
    
    def __init__(self):
        self.data_service = DataService()
    
    def calculate_mileage_rate(
        self,
        variant: Dict[str, Any],
        request: MileageRateRequest
    ) -> MileageRateResponse:
        """
        Calculate cost per kilometer for a vehicle using database data
        """
        
        # ─── Get data from database ──────────────────────────────────
        
        # 1. Get vehicle parameters
        vehicle_params = self.data_service.get_vehicle_parameters(variant.get("id"))
        
        # 2. Get market statistics
        market_stats = self.data_service.get_market_statistics(
            make=variant.get("make_name") or variant.get("make"),
            model=variant.get("model_name") or variant.get("model"),
            days=90
        )
        
        # 3. Get market value
        market_value = self._get_market_value(variant, market_stats)
        
        # 4. Get fuel prices
        fuel_type = variant.get("fuel_type", "petrol").lower()
        fuel_data = self.data_service.get_fuel_prices(fuel_type)
        fuel_price = fuel_data.get("price", 200)
        
        # 5. Get vehicle type parameters
        body_type = variant.get("body_type") or variant.get("body_type_name", "sedan").lower()
        type_params = self.data_service.get_vehicle_type_parameters(body_type)
        
        # 6. Get cost parameters
        fuel_consumption = variant.get("fuel_consumption_combined") or variant.get("fuel_consumption", 8.0)
        year = variant.get("year") or request.year or datetime.now().year
        current_year = datetime.now().year
        age = max(0, current_year - year)
        
        # 7. Get insurance rates
        insurance_data = self.data_service.get_insurance_rates(body_type)
        
        # 8. Get service intervals
        service_data = self.data_service.get_service_intervals(body_type)
        
        # 9. Get depreciation rates
        dep_class = variant.get("depreciation_class") or f"{body_type.upper()}_D"
        dep_data = self.data_service.get_depreciation_rates(dep_class)
        
        # 10. Get location factors
        location = request.location or "nairobi"
        location_data = self.data_service.get_location_factors(location)
        
        # ─── Calculate cost components ──────────────────────────────
        
        # Fuel cost
        fuel_cost_per_km = (fuel_consumption / 100) * fuel_price
        fuel_cost_per_km *= type_params.get("fuel_multiplier", 1.0)
        
        # Maintenance cost
        maintenance_per_km = self._calculate_maintenance_per_km(
            service_data=service_data,
            age=age,
            annual_mileage=request.annual_mileage,
            type_params=type_params
        )
        
        # Tyre cost
        tyre_per_km = self._calculate_tyre_per_km(
            variant=variant,
            type_params=type_params
        )
        
        # Insurance cost
        insurance_per_km = self._calculate_insurance_per_km(
            market_value=market_value,
            insurance_data=insurance_data,
            location_data=location_data,
            age=age,
            annual_mileage=request.annual_mileage
        )
        
        # Depreciation cost
        depreciation_per_km = self._calculate_depreciation_per_km(
            market_value=market_value,
            dep_data=dep_data,
            age=age,
            annual_mileage=request.annual_mileage
        )
        
        # Financing cost
        financing_per_km = 0
        if request.financed:
            financing_per_km = self._calculate_financing_per_km(
                market_value=market_value,
                annual_mileage=request.annual_mileage,
                down_payment=request.down_payment or 30,
                interest_rate=request.interest_rate or 16,
                loan_term=request.loan_term or 4
            )
        
        # Miscellaneous cost
        misc_per_km = self._calculate_misc_per_km(
            location_data=location_data,
            trip_type=request.trip_type or "mixed",
            type_params=type_params
        )
        
        # ─── Total cost ──────────────────────────────────────────────
        total_cost_per_km = (
            fuel_cost_per_km +
            maintenance_per_km +
            tyre_per_km +
            insurance_per_km +
            depreciation_per_km +
            financing_per_km +
            misc_per_km
        )
        
        # Apply market adjustment
        total_listings = market_stats.get("total_listings", 0)
        if total_listings > 50:
            market_adjustment = 1.02
        elif total_listings > 20:
            market_adjustment = 1.01
        elif total_listings > 5:
            market_adjustment = 1.0
        else:
            market_adjustment = 0.98
        
        total_cost_per_km *= market_adjustment
        
        # ─── Annual and monthly ──────────────────────────────────────
        total_annual_cost = total_cost_per_km * request.annual_mileage
        monthly_km = request.annual_mileage / 12
        monthly_cost = total_cost_per_km * monthly_km
        
        # ─── Breakdown ──────────────────────────────────────────────
        breakdown = {
            "fuel": round(fuel_cost_per_km * request.annual_mileage, 2),
            "maintenance": round(maintenance_per_km * request.annual_mileage, 2),
            "tyres": round(tyre_per_km * request.annual_mileage, 2),
            "insurance": round(insurance_per_km * request.annual_mileage, 2),
            "depreciation": round(depreciation_per_km * request.annual_mileage, 2),
            "financing": round(financing_per_km * request.annual_mileage, 2),
            "miscellaneous": round(misc_per_km * request.annual_mileage, 2)
        }
        
        # Remove zero values
        breakdown = {k: v for k, v in breakdown.items() if v > 0}
        
        # ─── Recommendations ──────────────────────────────────────────
        recommendations = self._generate_recommendations(
            fuel_cost_per_km=fuel_cost_per_km,
            total_cost_per_km=total_cost_per_km,
            maintenance_per_km=maintenance_per_km,
            insurance_per_km=insurance_per_km,
            depreciation_per_km=depreciation_per_km,
            market_stats=market_stats,
            age=age
        )
        
        # ─── Return response ──────────────────────────────────────────
        return MileageRateResponse(
            total_cost_per_km=round(total_cost_per_km, 2),
            total_annual_cost=round(total_annual_cost, 2),
            monthly_cost=round(monthly_cost, 2),
            breakdown=breakdown,
            fuel_cost_per_km=round(fuel_cost_per_km, 2),
            maintenance_per_km=round(maintenance_per_km, 2),
            tyre_per_km=round(tyre_per_km, 2),
            insurance_per_km=round(insurance_per_km, 2),
            depreciation_per_km=round(depreciation_per_km, 2),
            financing_per_km=round(financing_per_km, 2),
            misc_per_km=round(misc_per_km, 2),
            annual_mileage=request.annual_mileage,
            currency="KES",
            recommendations=recommendations,
            market_data={
                "market_value": round(market_value, 2),
                "listings_available": market_stats.get("total_listings", 0),
                "market_health": market_stats.get("market_health", "unknown"),
                "data_source": "scraper" if market_stats.get("total_listings", 0) > 0 else "database"
            }
        )
    
    def _get_market_value(self, variant: Dict, market_stats: Dict) -> float:
        """Get market value from database or scraper data"""
        # Prefer scraper data
        if market_stats.get("total_listings", 0) > 0:
            return market_stats.get("median_price", 0) or market_stats.get("average_price", 0)
        
        # Use variant stored value
        if variant.get("market_value"):
            return variant["market_value"]
        
        # Use base price
        if variant.get("base_price"):
            return variant["base_price"]
        
        # Estimate
        body_type = variant.get("body_type") or variant.get("body_type_name", "sedan").lower()
        year = variant.get("year") or datetime.now().year
        age = datetime.now().year - year
        
        base_values = {
            "suv": 4500000, "sedan": 3500000, "hatchback": 2500000,
            "pickup": 4000000, "van": 3800000, "luxury": 8000000,
            "crossover": 3800000, "coupe": 5000000, "convertible": 5500000
        }
        value = base_values.get(body_type, 3000000)
        value *= max(0.3, 1 - (age * 0.10))
        return max(value, 300000)
    
    def _calculate_maintenance_per_km(
        self,
        service_data: Dict,
        age: int,
        annual_mileage: float,
        type_params: Dict
    ) -> float:
        """Calculate maintenance cost per km from database"""
        interval_km = service_data.get("interval_km", 10000)
        base_cost = service_data.get("base_cost", 15000)
        major_interval = service_data.get("major_interval_km", 40000)
        major_cost = service_data.get("major_cost", 45000)
        
        # Regular service cost per km
        regular_per_km = base_cost / interval_km
        
        # Major service cost per km
        major_per_km = major_cost / major_interval
        
        # Total maintenance per km
        maintenance = regular_per_km + major_per_km
        
        # Apply age multiplier
        age_multiplier = 1 + (age * 0.05)  # 5% increase per year
        maintenance *= age_multiplier
        
        # Apply type multiplier
        maintenance *= type_params.get("maintenance_multiplier", 1.0)
        
        return maintenance
    
    def _calculate_tyre_per_km(self, variant: Dict, type_params: Dict) -> float:
        """Calculate tyre cost per km from database"""
        tyre_cost = variant.get("tyre_cost", 40000)
        tyre_lifespan = variant.get("tyre_lifespan", 45000)
        
        return (tyre_cost / tyre_lifespan) * type_params.get("tyre_multiplier", 1.0)
    
    def _calculate_insurance_per_km(
        self,
        market_value: float,
        insurance_data: Dict,
        location_data: Dict,
        age: int,
        annual_mileage: float
    ) -> float:
        """Calculate insurance cost per km from database"""
        rate = insurance_data.get("comprehensive_rate", 0.045)
        
        # Location multiplier
        location_multiplier = location_data.get("insurance_multiplier", 1.0)
        
        # Age factor
        age_factor = max(0.6, 1 - (age * 0.02))
        
        annual_insurance = market_value * rate * location_multiplier * age_factor
        return annual_insurance / annual_mileage
    
    def _calculate_depreciation_per_km(
        self,
        market_value: float,
        dep_data: Dict,
        age: int,
        annual_mileage: float
    ) -> float:
        """Calculate depreciation cost per km from database"""
        # Get rate based on age
        if age <= 1:
            rate = dep_data.get("year_1", 0.15)
        elif age <= 2:
            rate = dep_data.get("year_2", 0.12)
        elif age <= 3:
            rate = dep_data.get("year_3", 0.10)
        elif age <= 4:
            rate = dep_data.get("year_4", 0.08)
        elif age <= 5:
            rate = dep_data.get("year_5", 0.07)
        else:
            rate = dep_data.get("year_6_plus", 0.06)
        
        annual_depreciation = market_value * rate
        return annual_depreciation / annual_mileage
    
    def _calculate_financing_per_km(
        self,
        market_value: float,
        annual_mileage: float,
        down_payment: float,
        interest_rate: float,
        loan_term: int
    ) -> float:
        """Calculate financing cost per km"""
        loan_amount = market_value * (1 - down_payment / 100)
        monthly_rate = interest_rate / 100 / 12
        total_payments = loan_term * 12
        
        if monthly_rate > 0:
            monthly_payment = loan_amount * monthly_rate * (1 + monthly_rate) ** total_payments / ((1 + monthly_rate) ** total_payments - 1)
        else:
            monthly_payment = loan_amount / total_payments
        
        annual_payment = monthly_payment * 12
        return annual_payment / annual_mileage
    
    def _calculate_misc_per_km(
        self,
        location_data: Dict,
        trip_type: str,
        type_params: Dict
    ) -> float:
        """Calculate miscellaneous cost per km"""
        base = 2.0
        
        # Location factor
        location_factor = location_data.get("price_adjustment", 1.0)
        
        # Trip type factor
        trip_factors = {"urban": 1.3, "highway": 0.8, "mixed": 1.0, "offroad": 1.5}
        trip_factor = trip_factors.get(trip_type, 1.0)
        
        return base * location_factor * trip_factor
    
    def _generate_recommendations(
        self,
        fuel_cost_per_km: float,
        total_cost_per_km: float,
        maintenance_per_km: float,
        insurance_per_km: float,
        depreciation_per_km: float,
        market_stats: Dict,
        age: int
    ) -> List[str]:
        """Generate recommendations"""
        recommendations = []
        
        # Fuel recommendations
        fuel_percentage = (fuel_cost_per_km / total_cost_per_km) * 100 if total_cost_per_km > 0 else 0
        if fuel_percentage > 40:
            recommendations.append("⛽ Fuel costs are high. Consider eco-driving or a more fuel-efficient vehicle.")
        
        # Maintenance recommendations
        maintenance_percentage = (maintenance_per_km / total_cost_per_km) * 100 if total_cost_per_km > 0 else 0
        if maintenance_percentage > 20:
            recommendations.append("🔧 Maintenance costs are significant. Regular servicing can prevent costly repairs.")
        
        # Depreciation recommendations
        dep_percentage = (depreciation_per_km / total_cost_per_km) * 100 if total_cost_per_km > 0 else 0
        if dep_percentage > 25:
            recommendations.append("📉 Depreciation is high. Consider a used vehicle for better value retention.")
        
        # Age recommendations
        if age > 10:
            recommendations.append("🔧 Older vehicles may have higher maintenance costs. Consider newer models.")
        
        # Market recommendations
        total_listings = market_stats.get("total_listings", 0)
        health = market_stats.get("market_health", "unknown")
        if total_listings == 0:
            recommendations.append("📊 No market data available. Values are estimates based on database defaults.")
        elif health == "limited":
            recommendations.append("📊 Limited market data available. Consider professional advice for accurate valuation.")
        
        if not recommendations:
            recommendations.append("📊 Running costs are within expected range for this vehicle type.")
        
        return recommendations
