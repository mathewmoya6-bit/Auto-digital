"""
Running Cost Engine - Calculates running costs for vehicles
Integrates with scraper data for accurate market-based calculations
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import statistics

from app.engines.fuel_engine import FuelEngine
from app.engines.service_engine import ServiceEngine
from app.engines.tyre_engine import TyreEngine
from app.engines.insurance_engine import InsuranceEngine
from app.engines.depreciation_engine import DepreciationEngine
from app.engines.repair_engine import RepairEngine
from app.engines.finance_engine import FinanceEngine
from app.engines.miscellaneous_engine import MiscellaneousEngine
from app.schemas.request import RunningCostRequest
from app.schemas.response import RunningCostResponse, CostComponent
from app.services.market_service import MarketService

logger = logging.getLogger(__name__)


class RunningCostEngine:
    """Engine for calculating running costs with scraper data"""
    
    def __init__(self):
        self.fuel_engine = FuelEngine()
        self.service_engine = ServiceEngine()
        self.tyre_engine = TyreEngine()
        self.insurance_engine = InsuranceEngine()
        self.depreciation_engine = DepreciationEngine()
        self.repair_engine = RepairEngine()
        self.finance_engine = FinanceEngine()
        self.misc_engine = MiscellaneousEngine()
        self.market_service = MarketService()
    
    def calculate(
        self, 
        vehicle: Dict[str, Any], 
        request: RunningCostRequest,
        similar_listings: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Calculate running costs for a vehicle with market data.
        
        Returns a dictionary matching the frontend expectations.
        """
        
        # ─── Get market data for this vehicle type ──────────────────
        market_data = self.market_service.get_market_insights(
            make=vehicle.get("make_name") or vehicle.get("make"),
            model=vehicle.get("model_name") or vehicle.get("model"),
            days=90
        )
        
        # ─── Get market value from scraper data ────────────────────
        market_value = self._get_market_value(vehicle, market_data, similar_listings)
        
        # ─── Prepare vehicle data with market values ──────────────
        vehicle_data = {
            "engine_cc": vehicle.get("engine_cc", 0),
            "fuel_type": vehicle.get("fuel_type", "petrol"),
            "transmission": vehicle.get("transmission", "automatic"),
            "fuel_consumption": vehicle.get("fuel_consumption_combined") or vehicle.get("fuel_consumption", 10.0),
            "insurance_group": vehicle.get("insurance_group", 5),
            "service_interval": vehicle.get("service_interval", 10000),
            "tyre_size": vehicle.get("tyre_size", "225/65R17"),
            "market_value": market_value,
            "depreciation_class": vehicle.get("depreciation_class", self._get_depreciation_class(vehicle)),
            "tyre_cost": vehicle.get("tyre_cost", self._get_tyre_cost(vehicle)),
            "service_cost": vehicle.get("service_cost", self._get_service_cost(vehicle)),
            "make": vehicle.get("make_name") or vehicle.get("make", "Unknown"),
            "model": vehicle.get("model_name") or vehicle.get("model", "Unknown"),
            "body_type": vehicle.get("body_type") or vehicle.get("body_type_name", "sedan"),
            "year": vehicle.get("year") or datetime.now().year,
            "condition": request.condition or "good",
            "location": request.location or "nairobi",
            "driving_style": request.driving_style or "normal",
            "trip_type": request.trip_type or "mixed"
        }
        
        # ─── Use distance from request ──────────────────────────────
        distance = request.distance
        annual_mileage = request.annual_mileage or 20000
        
        # ─── Calculate per-trip costs ──────────────────────────────
        fuel_cost = self.fuel_engine.calculate(
            vehicle_data, 
            distance,
            request.trip_type or "mixed"
        )
        
        service_cost = self.service_engine.calculate(
            vehicle_data,
            distance
        )
        
        tyre_cost = self.tyre_engine.calculate(
            vehicle_data,
            distance
        )
        
        insurance_cost = self.insurance_engine.calculate(
            vehicle_data,
            distance,
            request.driving_style or "normal"
        )
        
        depreciation_cost = self.depreciation_engine.calculate(
            vehicle_data,
            distance,
            request.driving_style or "normal"
        )
        
        repair_cost = self.repair_engine.calculate(
            vehicle_data,
            distance,
            request.driving_style or "normal"
        )
        
        finance_cost = self.finance_engine.calculate(
            vehicle_data,
            distance
        )
        
        misc_cost = self.misc_engine.calculate(
            vehicle_data,
            distance,
            request.trip_type or "mixed"
        )
        
        # ─── Calculate annual costs ──────────────────────────────────
        # Convert per-trip costs to annual
        trips_per_year = annual_mileage / distance if distance > 0 else 1
        
        annual_fuel = fuel_cost.amount * trips_per_year
        annual_service = service_cost.amount * trips_per_year
        annual_tyres = tyre_cost.amount * trips_per_year
        annual_insurance = insurance_cost.amount * trips_per_year
        annual_depreciation = depreciation_cost.amount * trips_per_year
        annual_repairs = repair_cost.amount * trips_per_year
        annual_finance = finance_cost.amount * trips_per_year
        annual_misc = misc_cost.amount * trips_per_year
        
        annual_total = sum([
            annual_fuel,
            annual_service,
            annual_tyres,
            annual_insurance,
            annual_depreciation,
            annual_repairs,
            annual_finance,
            annual_misc
        ])
        
        # ─── Calculate per-km costs ──────────────────────────────────
        fuel_per_km = fuel_cost.amount / distance if distance > 0 else 0
        service_per_km = service_cost.amount / distance if distance > 0 else 0
        tyre_per_km = tyre_cost.amount / distance if distance > 0 else 0
        insurance_per_km = insurance_cost.amount / distance if distance > 0 else 0
        depreciation_per_km = depreciation_cost.amount / distance if distance > 0 else 0
        repairs_per_km = repair_cost.amount / distance if distance > 0 else 0
        finance_per_km = finance_cost.amount / distance if distance > 0 else 0
        misc_per_km = misc_cost.amount / distance if distance > 0 else 0
        
        total_per_km = sum([
            fuel_per_km,
            service_per_km,
            tyre_per_km,
            insurance_per_km,
            depreciation_per_km,
            repairs_per_km,
            finance_per_km,
            misc_per_km
        ])
        
        # ─── Trip total ──────────────────────────────────────────────
        trip_total = sum([
            fuel_cost.amount,
            service_cost.amount,
            tyre_cost.amount,
            insurance_cost.amount,
            depreciation_cost.amount,
            repair_cost.amount,
            finance_cost.amount,
            misc_cost.amount
        ])
        
        # ─── 5-Year projection ──────────────────────────────────────
        five_year_data = self._calculate_five_year_projection(
            vehicle_data=vehicle_data,
            annual_total=annual_total,
            annual_mileage=annual_mileage,
            years=request.years or 5
        )
        
        # ─── Monthly costs ───────────────────────────────────────────
        monthly_total = annual_total / 12
        monthly_fuel = annual_fuel / 12
        monthly_service = annual_service / 12
        monthly_tyres = annual_tyres / 12
        monthly_insurance = annual_insurance / 12
        monthly_depreciation = annual_depreciation / 12
        
        # ─── Return response matching frontend expectations ──────────
        return {
            "tripTotal": round(trip_total, 2),
            "tripCostPerKm": round(total_per_km, 2),
            "distance": distance,
            "fuelCostPerKm": round(fuel_per_km, 2),
            "fuelCostTrip": round(fuel_cost.amount, 2),
            "serviceTrip": round(service_cost.amount, 2),
            "tyreTrip": round(tyre_cost.amount, 2),
            "insuranceTrip": round(insurance_cost.amount, 2),
            "depreciationTrip": round(depreciation_cost.amount, 2),
            "fuelConsumption": round(vehicle_data.get("fuel_consumption", 10.0), 2),
            "fuelTypeDisplay": vehicle_data.get("fuel_type", "Petrol"),
            "transmissionDisplay": vehicle_data.get("transmission", "Automatic"),
            "initialCost": round(market_value, 2),
            "originalCost": round(market_value, 2),
            "ageAdjustedCost": round(market_value * 0.7, 2),
            "vehicleAge": self._get_vehicle_age(vehicle_data.get("year", 2020)),
            "annualKm": annual_mileage,
            "monthlyKm": annual_mileage / 12,
            "age": self._get_vehicle_age(vehicle_data.get("year", 2020)),
            "usageType": request.usage_type or "private",
            "monthlyFuel": round(monthly_fuel, 2),
            "monthlyService": round(monthly_service, 2),
            "monthlyTyre": round(monthly_tyres, 2),
            "monthlyInsurance": round(monthly_insurance, 2),
            "monthlyDepreciation": round(monthly_depreciation, 2),
            "annualFuel": round(annual_fuel, 2),
            "annualService": round(annual_service, 2),
            "annualTyre": round(annual_tyres, 2),
            "annualInsurance": round(annual_insurance, 2),
            "annualDepreciation": round(annual_depreciation, 2),
            "fiveYearData": five_year_data,
            "total5YearCost": round(sum(y["total"] for y in five_year_data), 2),
            "remainingValue": round(five_year_data[-1]["value"] if five_year_data else 0, 2),
            "fuelCostTrip": round(fuel_cost.amount, 2),
            "serviceTrip": round(service_cost.amount, 2),
            "tyreTrip": round(tyre_cost.amount, 2),
            "insuranceTrip": round(insurance_cost.amount, 2),
            "depreciationTrip": round(depreciation_cost.amount, 2),
            "recommendations": self._generate_recommendations(
                vehicle_data=vehicle_data,
                costs={
                    "fuel": fuel_cost.amount,
                    "service": service_cost.amount,
                    "tyres": tyre_cost.amount,
                    "insurance": insurance_cost.amount,
                    "depreciation": depreciation_cost.amount,
                    "repairs": repair_cost.amount
                },
                cost_per_km=total_per_km,
                market_data=market_data
            ),
            "depreciation_rate": 0.15,
            "mileageFactor": min(annual_mileage / 15000, 2.0)
        }
    
    def _get_vehicle_age(self, year: int) -> int:
        """Calculate vehicle age"""
        current_year = datetime.now().year
        return max(0, current_year - year)
    
    def _get_market_value(
        self, 
        vehicle: Dict, 
        market_data: Optional[Dict],
        similar_listings: Optional[List[Dict]]
    ) -> float:
        """Get market value from scraper data or fallback"""
        
        if similar_listings and len(similar_listings) > 0:
            prices = [l.get("price", 0) for l in similar_listings if l.get("price", 0) > 0]
            if prices:
                avg_price = statistics.mean(prices)
                if avg_price > 100000:
                    logger.info(f"Using scraper data: {len(prices)} listings, avg KES {avg_price:,.2f}")
                    return avg_price
        
        if market_data:
            avg_price = market_data.get("metrics", {}).get("average_price", 0)
            if avg_price > 100000:
                return avg_price
        
        if vehicle.get("market_value"):
            return vehicle["market_value"]
        
        if vehicle.get("base_price"):
            return vehicle["base_price"]
        
        if vehicle.get("price"):
            return vehicle["price"]
        
        return self._estimate_value(vehicle)
    
    def _estimate_value(self, vehicle: Dict) -> float:
        """Estimate vehicle value based on type and specs"""
        body_type = vehicle.get("body_type") or vehicle.get("body_type_name", "sedan").lower()
        year = vehicle.get("year") or datetime.now().year
        age = datetime.now().year - year
        
        base_values = {
            "suv": 4500000, "sedan": 3500000, "hatchback": 2500000,
            "pickup": 4000000, "van": 3800000, "truck": 6000000,
            "luxury": 8000000, "crossover": 3800000, "coupe": 5000000,
            "convertible": 5500000, "wagon": 3200000, "minivan": 3500000
        }
        
        base_value = base_values.get(body_type, 3000000)
        base_value *= max(0.3, 1 - (age * 0.12))
        
        make = vehicle.get("make", "").lower()
        luxury_makes = ["mercedes", "bmw", "audi", "lexus", "porsche", "range rover", "land rover"]
        premium_makes = ["toyota", "honda", "nissan", "mazda", "subaru", "volkswagen"]
        
        if any(m in make for m in luxury_makes):
            base_value *= 1.4
        elif any(m in make for m in premium_makes):
            base_value *= 1.0
        else:
            base_value *= 0.85
        
        return max(base_value, 300000)
    
    def _get_depreciation_class(self, vehicle: Dict) -> str:
        """Get depreciation class based on vehicle type"""
        body_type = vehicle.get("body_type") or vehicle.get("body_type_name", "sedan").lower()
        
        if body_type in ["suv", "crossover"]:
            return "SUV_D"
        elif body_type in ["pickup", "truck"]:
            return "PICKUP_C"
        elif body_type in ["luxury", "coupe", "convertible"]:
            return "LUXURY_A"
        elif body_type in ["hatchback", "sedan"]:
            return "SEDAN_B"
        else:
            return "SEDAN_C"
    
    def _get_tyre_cost(self, vehicle: Dict) -> float:
        """Get tyre cost based on vehicle type"""
        body_type = vehicle.get("body_type") or vehicle.get("body_type_name", "sedan").lower()
        
        if body_type in ["suv", "crossover"]:
            return 50000
        elif body_type in ["pickup", "truck"]:
            return 55000
        elif body_type in ["luxury", "coupe", "convertible"]:
            return 70000
        else:
            return 35000
    
    def _get_service_cost(self, vehicle: Dict) -> float:
        """Get service cost based on vehicle type"""
        body_type = vehicle.get("body_type") or vehicle.get("body_type_name", "sedan").lower()
        
        if body_type in ["suv", "crossover"]:
            return 20000
        elif body_type in ["pickup", "truck"]:
            return 18000
        elif body_type in ["luxury", "coupe", "convertible"]:
            return 30000
        else:
            return 15000
    
    def _calculate_five_year_projection(
        self,
        vehicle_data: Dict,
        annual_total: float,
        annual_mileage: float,
        years: int = 5
    ) -> List[Dict]:
        """Calculate 5-year cost projection"""
        five_year_data = []
        current_value = vehicle_data.get("market_value", 3000000)
        
        for year in range(1, years + 1):
            # Depreciation
            dep_rate = 0.12 - (year - 1) * 0.01
            dep_rate = max(0.08, min(0.25, dep_rate))
            depreciation = current_value * dep_rate
            current_value -= depreciation
            
            # Inflation
            inflation = 1 + (year - 1) * 0.04
            
            # Annual costs with inflation
            yearly_fuel = annual_total * 0.35 * inflation
            yearly_service = annual_total * 0.15 * (1 + (year - 1) * 0.05)
            yearly_insurance = annual_total * 0.15 * (1 + (year - 1) * 0.03)
            yearly_tyres = annual_total * 0.10 * (1 + (year - 1) * 0.04)
            
            yearly_total = depreciation + yearly_fuel + yearly_service + yearly_insurance + yearly_tyres
            
            five_year_data.append({
                "year": year,
                "depreciation": round(depreciation, 2),
                "fuel": round(yearly_fuel, 2),
                "service": round(yearly_service, 2),
                "insurance": round(yearly_insurance, 2),
                "tyres": round(yearly_tyres, 2),
                "total": round(yearly_total, 2),
                "value": round(max(current_value, 0), 2)
            })
        
        return five_year_data
    
    def _generate_recommendations(
        self,
        vehicle_data: Dict,
        costs: Dict,
        cost_per_km: float,
        market_data: Optional[Dict]
    ) -> List[str]:
        """Generate cost-saving recommendations"""
        recommendations = []
        
        fuel_cost = costs.get("fuel", 0)
        if fuel_cost > 0 and cost_per_km > 0:
            fuel_percentage = (fuel_cost / (cost_per_km * 100 if cost_per_km > 0 else 1)) * 100
            if fuel_percentage > 40:
                recommendations.append("Fuel costs are high. Consider eco-driving techniques.")
        
        service_cost = costs.get("service", 0)
        if service_cost > 0 and cost_per_km > 0:
            service_percentage = (service_cost / (cost_per_km * 100 if cost_per_km > 0 else 1)) * 100
            if service_percentage > 20:
                recommendations.append("Service costs are significant. Regular maintenance can prevent costly repairs.")
        
        tyre_cost = costs.get("tyres", 0)
        if tyre_cost > 0 and cost_per_km > 0:
            tyre_percentage = (tyre_cost / (cost_per_km * 100 if cost_per_km > 0 else 1)) * 100
            if tyre_percentage > 15:
                recommendations.append("Tyre costs are high. Check tyre pressure regularly and rotate tyres.")
        
        dep_cost = costs.get("depreciation", 0)
        if dep_cost > 0 and cost_per_km > 0:
            dep_percentage = (dep_cost / (cost_per_km * 100 if cost_per_km > 0 else 1)) * 100
            if dep_percentage > 25:
                recommendations.append("Depreciation is high. Consider vehicles with better resale value.")
        
        if cost_per_km > 50:
            recommendations.append("Overall running cost is high. Consider a more fuel-efficient vehicle.")
        elif cost_per_km < 20:
            recommendations.append("Excellent running cost efficiency! Your vehicle is economical to operate.")
        
        if market_data:
            health = market_data.get("metrics", {}).get("market_health", "unknown")
            if health == "limited":
                recommendations.append("Limited market data available. Consider getting professional advice.")
        
        if not recommendations:
            recommendations.append("Running costs are within expected range for this vehicle type.")
        
        return recommendations
