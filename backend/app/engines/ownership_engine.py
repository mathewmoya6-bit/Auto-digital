"""
Ownership Engine - Calculate total cost of vehicle ownership
Uses database and scraper data for accurate calculations
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from app.schemas.request import OwnershipCostRequest
from app.schemas.response import OwnershipResponse
from app.services.data_service import DataService

logger = logging.getLogger(__name__)


class OwnershipEngine:
    """Engine for calculating total cost of vehicle ownership with database data"""
    
    def __init__(self):
        self.data_service = DataService()
    
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
        purchase_price = request.purchase_price or market_value
        
        # 4. Get fuel type and consumption
        fuel_type = variant.get("fuel_type", "petrol").lower()
        fuel_consumption = variant.get("fuel_consumption_combined") or variant.get("fuel_consumption", 8.0)
        
        # 5. Get fuel price
        fuel_data = self.data_service.get_fuel_prices(fuel_type)
        fuel_price = request.fuel_price or fuel_data.get("price", 200)
        
        # 6. Get vehicle type
        body_type = variant.get("body_type") or variant.get("body_type_name", "sedan").lower()
        type_params = self.data_service.get_vehicle_type_parameters(body_type)
        
        # 7. Get insurance rates
        insurance_data = self.data_service.get_insurance_rates(body_type)
        insurance_rate = request.insurance_rate or insurance_data.get("comprehensive_rate", 0.045)
        
        # 8. Get service intervals
        service_data = self.data_service.get_service_intervals(body_type)
        
        # 9. Get depreciation rates
        dep_class = variant.get("depreciation_class") or f"{body_type.upper()}_D"
        dep_data = self.data_service.get_depreciation_rates(dep_class)
        
        # 10. Get location factors
        location = request.location or "nairobi"
        location_data = self.data_service.get_location_factors(location)
        
        # ─── Calculate cost components ──────────────────────────────
        
        # 1. Loan calculation
        loan_amount = max(0, purchase_price - request.down_payment)
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
        fuel_cost_per_km = (fuel_consumption / 100) * fuel_price
        fuel_cost_per_km *= type_params.get("fuel_multiplier", 1.0)
        annual_fuel_cost = fuel_cost_per_km * annual_mileage
        
        # 3. Insurance cost
        location_multiplier = location_data.get("insurance_multiplier", 1.0)
        age = max(0, datetime.now().year - (variant.get("year") or datetime.now().year))
        age_factor = max(0.6, 1 - (age * 0.02))
        
        annual_insurance = purchase_price * insurance_rate * location_multiplier * age_factor
        
        # 4. Maintenance cost
        interval_km = service_data.get("interval_km", 10000)
        base_service_cost = service_data.get("base_cost", 15000)
        major_interval = service_data.get("major_interval_km", 40000)
        major_service_cost = service_data.get("major_cost", 45000)
        
        regular_per_km = base_service_cost / interval_km
        major_per_km = major_service_cost / major_interval
        maintenance_per_km = regular_per_km + major_per_km
        
        age_multiplier = 1 + (age * 0.05)
        maintenance_per_km *= age_multiplier
        maintenance_per_km *= type_params.get("maintenance_multiplier", 1.0)
        
        annual_maintenance = maintenance_per_km * annual_mileage
        
        # 5. Tyre cost
        tyre_cost = variant.get("tyre_cost", 40000)
        tyre_lifespan = variant.get("tyre_lifespan", 45000)
        tyre_per_km = (tyre_cost / tyre_lifespan) * type_params.get("tyre_multiplier", 1.0)
        annual_tyres = tyre_per_km * annual_mileage
        
        # 6. Depreciation
        if request.include_depreciation:
            # Get depreciation rate based on year
            if age <= 1:
                dep_rate = dep_data.get("year_1", 0.15)
            elif age <= 2:
                dep_rate = dep_data.get("year_2", 0.12)
            elif age <= 3:
                dep_rate = dep_data.get("year_3", 0.10)
            elif age <= 4:
                dep_rate = dep_data.get("year_4", 0.08)
            elif age <= 5:
                dep_rate = dep_data.get("year_5", 0.07)
            else:
                dep_rate = dep_data.get("year_6_plus", 0.06)
            
            annual_depreciation = purchase_price * dep_rate
            total_depreciation = annual_depreciation * request.loan_term_years
        else:
            annual_depreciation = 0
            total_depreciation = 0
        
        # 7. Financing cost
        total_financing = total_loan_cost - loan_amount + total_interest
        
        # ─── Total annual running costs ──────────────────────────────
        total_annual_running = annual_fuel_cost + annual_insurance + annual_maintenance + annual_tyres
        
        # ─── Total cost over loan term ──────────────────────────────
        total_running_cost = total_annual_running * request.loan_term_years
        total_cost = total_loan_cost + total_running_cost + request.down_payment
        total_cost_with_depreciation = total_cost + total_depreciation
        
        # ─── Monthly affordability ──────────────────────────────────
        monthly_running_cost = total_annual_running / 12
        total_monthly_cost = monthly_payment + monthly_running_cost
        
        # ─── Affordability score (0-100) ────────────────────────────
        monthly_income_estimate = total_monthly_cost * 3  # Assumes 33% of income
        affordability_score = min(100, max(0, int(100 - (total_monthly_cost / monthly_income_estimate * 100))))
        
        # ─── Breakdown ──────────────────────────────────────────────
        breakdown = {
            "down_payment": round(request.down_payment, 2),
            "loan_principal": round(loan_amount, 2),
            "loan_interest": round(total_interest, 2),
            "total_loan_payments": round(total_loan_cost, 2),
            "financing_cost": round(total_financing, 2),
            "fuel_total": round(total_running_cost * (annual_fuel_cost / total_annual_running) if total_annual_running > 0 else 0, 2),
            "insurance_total": round(total_running_cost * (annual_insurance / total_annual_running) if total_annual_running > 0 else 0, 2),
            "maintenance_total": round(total_running_cost * (annual_maintenance / total_annual_running) if total_annual_running > 0 else 0, 2),
            "tyres_total": round(total_running_cost * (annual_tyres / total_annual_running) if total_annual_running > 0 else 0, 2),
            "depreciation": round(total_depreciation, 2)
        }
        
        # Remove zero values
        breakdown = {k: v for k, v in breakdown.items() if v > 0}
        
        # ─── Year by year breakdown ──────────────────────────────────
        year_by_year = self._calculate_year_by_year(
            purchase_price=purchase_price,
            annual_fuel_cost=annual_fuel_cost,
            annual_insurance=annual_insurance,
            annual_maintenance=annual_maintenance,
            annual_tyres=annual_tyres,
            dep_data=dep_data,
            years=request.loan_term_years
        )
        
        # ─── Recommendations ──────────────────────────────────────────
        recommendations = self._generate_recommendations(
            monthly_payment=monthly_payment,
            total_monthly_cost=total_monthly_cost,
            annual_fuel_cost=annual_fuel_cost,
            annual_insurance=annual_insurance,
            total_annual_running=total_annual_running,
            affordability_score=affordability_score,
            purchase_price=purchase_price,
            market_stats=market_stats,
            age=age
        )
        
        # ─── Return response ──────────────────────────────────────────
        return OwnershipResponse(
            total_cost=round(total_cost_with_depreciation, 2),
            total_cost_without_depreciation=round(total_cost, 2),
            monthly_payment=round(monthly_payment, 2),
            monthly_running_cost=round(monthly_running_cost, 2),
            total_monthly_cost=round(total_monthly_cost, 2),
            total_interest=round(total_interest, 2),
            annual_running_cost=round(total_annual_running, 2),
            breakdown=breakdown,
            year_by_year=year_by_year,
            affordability_score=affordability_score,
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
        if market_stats.get("total_listings", 0) > 0:
            return market_stats.get("median_price", 0) or market_stats.get("average_price", 0)
        
        if variant.get("market_value"):
            return variant["market_value"]
        
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
    
    def _calculate_year_by_year(
        self,
        purchase_price: float,
        annual_fuel_cost: float,
        annual_insurance: float,
        annual_maintenance: float,
        annual_tyres: float,
        dep_data: Dict,
        years: int
    ) -> List[Dict]:
        """Calculate year by year breakdown"""
        year_by_year = []
        current_value = purchase_price
        
        for year in range(1, years + 1):
            # Get depreciation rate for this year
            if year <= 1:
                dep_rate = dep_data.get("year_1", 0.15)
            elif year <= 2:
                dep_rate = dep_data.get("year_2", 0.12)
            elif year <= 3:
                dep_rate = dep_data.get("year_3", 0.10)
            elif year <= 4:
                dep_rate = dep_data.get("year_4", 0.08)
            elif year <= 5:
                dep_rate = dep_data.get("year_5", 0.07)
            else:
                dep_rate = dep_data.get("year_6_plus", 0.06)
            
            depreciation = current_value * dep_rate
            current_value -= depreciation
            
            # Inflation adjustment (3% per year)
            inflation = 1 + (year - 1) * 0.03
            
            year_by_year.append({
                "year": year,
                "depreciation": round(depreciation, 2),
                "fuel": round(annual_fuel_cost * inflation, 2),
                "insurance": round(annual_insurance * (1 + (year - 1) * 0.02), 2),
                "maintenance": round(annual_maintenance * (1 + (year - 1) * 0.05), 2),
                "tyres": round(annual_tyres * (1 + (year - 1) * 0.03), 2),
                "total": round(
                    depreciation +
                    annual_fuel_cost * inflation +
                    annual_insurance * (1 + (year - 1) * 0.02) +
                    annual_maintenance * (1 + (year - 1) * 0.05) +
                    annual_tyres * (1 + (year - 1) * 0.03),
                    2
                ),
                "remaining_value": round(max(current_value, purchase_price * 0.10), 2)
            })
        
        return year_by_year
    
    def _generate_recommendations(
        self,
        monthly_payment: float,
        total_monthly_cost: float,
        annual_fuel_cost: float,
        annual_insurance: float,
        total_annual_running: float,
        affordability_score: int,
        purchase_price: float,
        market_stats: Dict,
        age: int
    ) -> List[str]:
        """Generate recommendations"""
        recommendations = []
        
        # Payment recommendations
        if monthly_payment > (purchase_price * 0.05):
            recommendations.append("💰 Monthly payment is high. Consider a larger down payment or longer loan term.")
        
        # Fuel recommendations
        if annual_fuel_cost > total_annual_running * 0.40:
            recommendations.append("⛽ Fuel cost is significant. Consider a more fuel-efficient vehicle.")
        
        # Insurance recommendations
        if annual_insurance > total_annual_running * 0.20:
            recommendations.append("🛡️ Insurance cost is high. Shop around for better rates.")
        
        # Affordability recommendations
        if affordability_score < 60:
            recommendations.append("⚠️ Affordability score is low. Consider a less expensive vehicle or better financing terms.")
        elif affordability_score > 80:
            recommendations.append("✅ This vehicle appears to be well within affordable range.")
        
        # Age recommendations
        if age > 10:
            recommendations.append("🔧 Vehicle is older. Consider higher maintenance costs in your budget.")
        elif age > 5:
            recommendations.append("📊 Vehicle is aging. Regular maintenance is crucial for reliability.")
        
        # Market recommendations
        if market_stats.get("total_listings", 0) == 0:
            recommendations.append("📊 No market data available. Consider professional advice for accurate valuation.")
        elif market_stats.get("market_health") == "limited":
            recommendations.append("📊 Limited market data available. Price may vary from estimates.")
        
        if not recommendations:
            recommendations.append("📊 This vehicle appears to be a sound financial choice based on available data.")
        
        return recommendations
