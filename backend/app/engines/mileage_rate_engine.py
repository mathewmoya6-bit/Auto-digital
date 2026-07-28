"""
Mileage Rate Engine - Calculate cost per kilometer using database and scraper data
FIXED: Realistic depreciation for Toyota SUVs, consistent fuel consumption, operating vs total cost
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
    ) -> Dict[str, Any]:
        """
        Calculate cost per kilometer for a vehicle using database data.
        
        Returns a dictionary matching the frontend expectations.
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
        
        # 6. Get fuel consumption (FIXED: consistent value)
        fuel_consumption = self._get_fuel_consumption(variant)
        year = variant.get("year") or datetime.now().year
        current_year = datetime.now().year
        age = max(0, current_year - year)
        
        # 7. Get insurance rates
        insurance_data = self.data_service.get_insurance_rates(body_type)
        
        # 8. Get service intervals
        service_data = self.data_service.get_service_intervals(body_type)
        
        # 9. Get depreciation rates (FIXED: realistic for Toyota SUVs)
        make = variant.get("make_name") or variant.get("make") or ""
        dep_data = self._get_depreciation_rates(body_type, make)
        
        # 10. Get location factors
        location = request.location or "nairobi"
        location_data = self.data_service.get_location_factors(location)
        
        # ─── Calculate cost components ──────────────────────────────
        
        # Fuel cost
        fuel_cost_per_km = (fuel_consumption / 100) * fuel_price
        fuel_cost_per_km *= type_params.get("fuel_multiplier", 1.0)
        
        # Maintenance cost (from request or default)
        maintenance_per_km = request.maintenance_cost_per_km or self._calculate_maintenance_per_km(
            service_data=service_data,
            age=age,
            annual_mileage=request.annual_mileage,
            type_params=type_params
        )
        
        # Tyre cost (from request or default)
        tyre_per_km = request.tyre_cost_per_km or self._calculate_tyre_per_km(
            variant=variant,
            type_params=type_params
        )
        
        # Insurance cost (from request or default)
        insurance_per_km = request.insurance_cost_per_km or self._calculate_insurance_per_km(
            market_value=market_value,
            insurance_data=insurance_data,
            location_data=location_data,
            age=age,
            annual_mileage=request.annual_mileage
        )
        
        # Depreciation cost (from request or default)
        if request.include_depreciation:
            depreciation_per_km = self._calculate_depreciation_per_km(
                market_value=market_value,
                dep_data=dep_data,
                age=age,
                annual_mileage=request.annual_mileage
            )
        else:
            depreciation_per_km = 0
        
        # ─── Calculate total cost per km ──────────────────────────────
        total_cost_per_km = fuel_cost_per_km + maintenance_per_km + tyre_per_km + insurance_per_km
        
        if request.include_depreciation:
            total_cost_per_km += depreciation_per_km
        
        # Apply market adjustment
        total_listings = market_stats.get("total_listings", 0)
        market_adjustment = self._get_market_adjustment(total_listings)
        total_cost_per_km *= market_adjustment
        
        # ─── Annual and monthly costs ──────────────────────────────
        total_annual_cost = total_cost_per_km * request.annual_mileage
        monthly_cost = total_annual_cost / 12
        
        # ─── Breakdown ──────────────────────────────────────────────
        breakdown = {
            "fuel": round(fuel_cost_per_km * request.annual_mileage, 2),
            "maintenance": round(maintenance_per_km * request.annual_mileage, 2),
            "tyres": round(tyre_per_km * request.annual_mileage, 2),
            "insurance": round(insurance_per_km * request.annual_mileage, 2),
        }
        
        if request.include_depreciation:
            breakdown["depreciation"] = round(depreciation_per_km * request.annual_mileage, 2)
        
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
            age=age,
            make=make,
            body_type=body_type,
            include_depreciation=request.include_depreciation
        )
        
        # ─── Return response matching frontend expectations ──────────
        return {
            "total_cost_per_km": round(total_cost_per_km, 2),
            "total_annual_cost": round(total_annual_cost, 2),
            "monthly_cost": round(monthly_cost, 2),
            "breakdown": breakdown,
            "fuel_cost_per_km": round(fuel_cost_per_km, 2),
            "depreciation_per_km": round(depreciation_per_km, 2) if request.include_depreciation else 0,
            "insurance_per_km": round(insurance_per_km, 2),
            "maintenance_per_km": round(maintenance_per_km, 2),
            "tyre_per_km": round(tyre_per_km, 2),
            "annual_mileage": request.annual_mileage,
            "currency": "KES",
            "confidence_score": self._calculate_confidence_score(
                market_stats=market_stats,
                age=age,
                total_listings=total_listings
            ),
            "recommendations": recommendations,
            "market_data": {
                "market_value": round(market_value, 2),
                "listings_available": market_stats.get("total_listings", 0),
                "market_health": market_stats.get("market_health", "unknown"),
                "data_source": "scraper" if market_stats.get("total_listings", 0) > 0 else "database"
            },
            "fuel_consumption": round(fuel_consumption, 2),
            "fuel_price": fuel_price
        }
    
    def _get_fuel_consumption(self, variant: Dict) -> float:
        """Get fuel consumption in L/100km (FIXED: consistent value)"""
        fuel_consumption = variant.get("fuel_consumption_combined") or variant.get("fuel_consumption", 9.0)
        
        # If value is in km/L (e.g., 10.0 km/L), convert to L/100km
        if fuel_consumption > 5 and fuel_consumption < 50:
            if fuel_consumption < 20:  # km/L is typically 5-20
                return round(100 / fuel_consumption, 1)
        
        # If it's already L/100km (5-20 L/100km)
        if 5 <= fuel_consumption <= 20:
            return round(fuel_consumption, 1)
        
        return 11.1  # ~9 km/L
    
    def _get_depreciation_rates(self, body_type: str, make: str) -> Dict:
        """Get realistic depreciation rates based on vehicle type and make"""
        
        # Toyota/Lexus hold value very well in Kenya
        if make.lower() in ["toyota", "lexus"]:
            if "prado" in body_type.lower() or "land cruiser" in body_type.lower():
                return {
                    "year_1": 0.08,
                    "year_2": 0.07,
                    "year_3": 0.06,
                    "year_4": 0.05,
                    "year_5": 0.05,
                    "year_6_plus": 0.04
                }
            elif "hilux" in body_type.lower():
                return {
                    "year_1": 0.09,
                    "year_2": 0.08,
                    "year_3": 0.07,
                    "year_4": 0.06,
                    "year_5": 0.05,
                    "year_6_plus": 0.04
                }
            else:
                return {
                    "year_1": 0.10,
                    "year_2": 0.09,
                    "year_3": 0.08,
                    "year_4": 0.07,
                    "year_5": 0.06,
                    "year_6_plus": 0.05
                }
        
        # German luxury (Mercedes, BMW, Audi)
        if make.lower() in ["mercedes", "bmw", "audi", "porsche"]:
            return {
                "year_1": 0.15,
                "year_2": 0.13,
                "year_3": 0.11,
                "year_4": 0.09,
                "year_5": 0.08,
                "year_6_plus": 0.06
            }
        
        # Default rates for other makes
        return {
            "year_1": 0.12,
            "year_2": 0.10,
            "year_3": 0.08,
            "year_4": 0.07,
            "year_5": 0.06,
            "year_6_plus": 0.05
        }
    
    def _get_market_value(self, variant: Dict, market_stats: Dict) -> float:
        """Get market value from database or scraper data"""
        if market_stats.get("total_listings", 0) > 0:
            return market_stats.get("median_price", 0) or market_stats.get("average_price", 0)
        
        if variant.get("market_value"):
            return variant["market_value"]
        
        if variant.get("base_price"):
            return variant["base_price"]
        
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
    
    def _get_market_adjustment(self, total_listings: int) -> float:
        """Get market adjustment based on available listings"""
        if total_listings > 50:
            return 1.02
        elif total_listings > 20:
            return 1.01
        elif total_listings > 5:
            return 1.0
        else:
            return 0.98
    
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
        
        regular_per_km = base_cost / interval_km
        major_per_km = major_cost / major_interval
        maintenance = regular_per_km + major_per_km
        
        age_multiplier = 1 + (age * 0.05)
        maintenance *= age_multiplier
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
        location_multiplier = location_data.get("insurance_multiplier", 1.0)
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
    
    def _calculate_confidence_score(
        self,
        market_stats: Dict,
        age: int,
        total_listings: int
    ) -> int:
        """Calculate confidence score"""
        confidence = 50
        
        if total_listings > 50:
            confidence += 30
        elif total_listings > 20:
            confidence += 25
        elif total_listings > 10:
            confidence += 20
        elif total_listings > 5:
            confidence += 15
        elif total_listings > 0:
            confidence += 10
        
        if age <= 3:
            confidence += 10
        elif age <= 5:
            confidence += 5
        elif age > 10:
            confidence -= 5
        
        health = market_stats.get("market_health", "unknown")
        if health == "good":
            confidence += 5
        elif health == "limited":
            confidence -= 5
        
        return min(98, max(50, confidence))
    
    def _generate_recommendations(
        self,
        fuel_cost_per_km: float,
        total_cost_per_km: float,
        maintenance_per_km: float,
        insurance_per_km: float,
        depreciation_per_km: float,
        market_stats: Dict,
        age: int,
        make: str,
        body_type: str,
        include_depreciation: bool
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if total_cost_per_km <= 0:
            return ["📊 Running costs within expected range for this vehicle type."]
        
        # Fuel recommendations
        fuel_percentage = (fuel_cost_per_km / total_cost_per_km) * 100
        if fuel_percentage > 40:
            savings = round((fuel_cost_per_km * 5000) / 100, 0)
            recommendations.append(
                f"⛽ Fuel accounts for {fuel_percentage:.0f}% of your running costs. "
                f"Reducing annual mileage by 5,000 km would save approximately KES {savings:,.0f} per year."
            )
        elif fuel_percentage > 30:
            recommendations.append(
                f"⛽ Fuel is {fuel_percentage:.0f}% of costs. Consider eco-driving techniques."
            )
        
        # Depreciation recommendations
        if include_depreciation and depreciation_per_km > 0:
            dep_percentage = (depreciation_per_km / total_cost_per_km) * 100
            if dep_percentage > 25:
                if make.lower() in ["toyota", "lexus"]:
                    recommendations.append(
                        f"📉 Depreciation is {dep_percentage:.0f}% of costs. "
                        "Toyota vehicles typically hold value well. This estimate may be conservative."
                    )
                else:
                    recommendations.append(
                        f"📉 Depreciation is {dep_percentage:.0f}% of costs. "
                        "Consider a vehicle with better resale value."
                    )
        
        # Maintenance recommendations
        maintenance_percentage = (maintenance_per_km / total_cost_per_km) * 100
        if maintenance_percentage > 20:
            recommendations.append(
                f"🔧 Maintenance is {maintenance_percentage:.0f}% of costs. "
                "Regular servicing can prevent costly repairs."
            )
        
        # Insurance recommendations
        insurance_percentage = (insurance_per_km / total_cost_per_km) * 100
        if insurance_percentage > 15:
            recommendations.append(
                f"🛡️ Insurance is {insurance_percentage:.0f}% of costs. "
                "Shop around for better rates."
            )
        
        # Age-based recommendations
        if age > 10:
            recommendations.append(
                "🔧 This vehicle is over 10 years old. Consider higher maintenance costs."
            )
        elif age > 5 and age <= 10:
            recommendations.append(
                "📊 Vehicle is approaching 10 years old. Regular maintenance is crucial."
            )
        elif age <= 2:
            recommendations.append(
                "✅ This is a relatively new vehicle. It should be reliable with lower maintenance costs."
            )
        
        # Market data recommendations
        total_listings = market_stats.get("total_listings", 0)
        health = market_stats.get("market_health", "unknown")
        
        if total_listings == 0:
            recommendations.append(
                "📊 No market data available. Values are estimates based on similar vehicles."
            )
        elif health == "limited":
            recommendations.append(
                "📊 Limited market data available. Values may vary from estimates."
            )
        elif health == "good":
            recommendations.append(
                "📊 Good market data available. The valuation is supported by recent market listings."
            )
        
        # Overall recommendation
        if total_cost_per_km > 50:
            recommendations.append(
                "💰 Total running cost is high. Consider a more economical vehicle."
            )
        elif total_cost_per_km < 20:
            recommendations.append(
                "✅ Excellent running cost efficiency! Your vehicle is economical to operate."
            )
        
        if not recommendations:
            recommendations.append("📊 Running costs are within expected range for this vehicle type.")
        
        return recommendations
