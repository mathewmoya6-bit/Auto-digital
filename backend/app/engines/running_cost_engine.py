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
from app.schemas.request import RunningCostRequest, MileageRateRequest
from app.schemas.response import RunningCostResponse, CostComponent
from app.services.market_service import MarketService

logger = logging.getLogger(__name__)


class RunningCostEngine:
    """Engine for calculating running costs with scraper data"""
    
    # ─── Kenyan Market Cost Parameters ──────────────────────────────
    KENYA_COST_PARAMS = {
        "fuel": {
            "petrol": {"base": 203.47, "urban_multiplier": 1.15, "highway_multiplier": 0.85},
            "diesel": {"base": 195.67, "urban_multiplier": 1.12, "highway_multiplier": 0.88},
            "electric": {"base": 30.00, "urban_multiplier": 1.05, "highway_multiplier": 0.95},
            "hybrid": {"base": 150.00, "urban_multiplier": 1.08, "highway_multiplier": 0.90}
        },
        "service": {
            "base": 15000,
            "interval_km": 10000,
            "age_multiplier": 1.05,
            "suv_multiplier": 1.3,
            "luxury_multiplier": 1.8,
            "pickup_multiplier": 1.2
        },
        "tyres": {
            "base_cost": 40000,
            "lifespan_km": 45000,
            "suv_multiplier": 1.3,
            "luxury_multiplier": 1.6,
            "pickup_multiplier": 1.2
        },
        "insurance": {
            "comprehensive_rate": 0.045,
            "third_party_fee": 7000,
            "age_multiplier": 0.95,
            "nairobi_multiplier": 1.05
        },
        "depreciation": {
            "suv": 0.15,
            "sedan": 0.13,
            "pickup": 0.14,
            "luxury": 0.20,
            "electric": 0.18,
            "hybrid": 0.14
        },
        "repairs": {
            "base_per_km": 1.5,
            "suv_multiplier": 1.4,
            "luxury_multiplier": 1.8,
            "pickup_multiplier": 1.3
        }
    }
    
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
    ) -> RunningCostResponse:
        """Calculate running costs for a vehicle with market data"""
        
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
            "year": vehicle.get("year") or request.year or datetime.now().year,
            "condition": request.condition or "good",
            "location": request.location or "nairobi"
        }
        
        # ─── Calculate each cost component ─────────────────────────
        fuel_cost = self.fuel_engine.calculate(
            vehicle_data, 
            request.distance,
            request.trip_type
        )
        
        service_cost = self.service_engine.calculate(
            vehicle_data,
            request.distance
        )
        
        tyre_cost = self.tyre_engine.calculate(
            vehicle_data,
            request.distance
        )
        
        insurance_cost = self.insurance_engine.calculate(
            vehicle_data,
            request.distance,
            request.driving_style
        )
        
        depreciation_cost = self.depreciation_engine.calculate(
            vehicle_data,
            request.distance,
            request.driving_style
        )
        
        repair_cost = self.repair_engine.calculate(
            vehicle_data,
            request.distance,
            request.driving_style
        )
        
        finance_cost = self.finance_engine.calculate(
            vehicle_data,
            request.distance
        )
        
        misc_cost = self.misc_engine.calculate(
            vehicle_data,
            request.distance,
            request.trip_type
        )
        
        # ─── Combine all costs ────────────────────────────────────
        total_cost = sum([
            fuel_cost.amount,
            service_cost.amount,
            tyre_cost.amount,
            insurance_cost.amount,
            depreciation_cost.amount,
            repair_cost.amount,
            finance_cost.amount,
            misc_cost.amount
        ])
        
        cost_per_km = total_cost / request.distance if request.distance > 0 else 0
        
        # ─── Generate recommendations ─────────────────────────────
        recommendations = self._generate_recommendations(
            vehicle_data=vehicle_data,
            costs={
                "fuel": fuel_cost.amount,
                "service": service_cost.amount,
                "tyres": tyre_cost.amount,
                "insurance": insurance_cost.amount,
                "depreciation": depreciation_cost.amount,
                "repairs": repair_cost.amount
            },
            cost_per_km=cost_per_km,
            market_data=market_data
        )
        
        return RunningCostResponse(
            fuel=fuel_cost.amount,
            service=service_cost.amount,
            tyres=tyre_cost.amount,
            insurance=insurance_cost.amount,
            repairs=repair_cost.amount,
            depreciation=depreciation_cost.amount,
            finance=finance_cost.amount,
            misc=misc_cost.amount,
            total=round(total_cost, 2),
            cost_per_km=round(cost_per_km, 2),
            components=[fuel_cost, service_cost, tyre_cost, insurance_cost, 
                       depreciation_cost, repair_cost, finance_cost, misc_cost],
            recommendations=recommendations,
            market_data={
                "market_value": market_value,
                "listings_available": len(similar_listings) if similar_listings else 0,
                "market_health": market_data.get("metrics", {}).get("market_health", "unknown") if market_data else "unknown"
            }
        )
    
    def _get_market_value(
        self, 
        vehicle: Dict, 
        market_data: Optional[Dict],
        similar_listings: Optional[List[Dict]]
    ) -> float:
        """Get market value from scraper data or fallback"""
        
        # ─── Check if we have scraper data ─────────────────────────
        if similar_listings and len(similar_listings) > 0:
            prices = [l.get("price", 0) for l in similar_listings if l.get("price", 0) > 0]
            if prices:
                avg_price = statistics.mean(prices)
                if avg_price > 100000:  # Minimum reasonable price
                    logger.info(f"Using scraper data: {len(prices)} listings, avg KES {avg_price:,.2f}")
                    return avg_price
        
        # ─── Check market insights ──────────────────────────────────
        if market_data:
            avg_price = market_data.get("metrics", {}).get("average_price", 0)
            if avg_price > 100000:
                return avg_price
        
        # ─── Fallback: Use vehicle's stored value ──────────────────
        if vehicle.get("market_value"):
            return vehicle["market_value"]
        
        if vehicle.get("base_price"):
            return vehicle["base_price"]
        
        if vehicle.get("price"):
            return vehicle["price"]
        
        # ─── Estimate based on vehicle type ────────────────────────
        return self._estimate_value(vehicle)
    
    def _estimate_value(self, vehicle: Dict) -> float:
        """Estimate vehicle value based on type and specs"""
        make = vehicle.get("make_name") or vehicle.get("make", "").lower()
        model = vehicle.get("model_name") or vehicle.get("model", "").lower()
        body_type = vehicle.get("body_type") or vehicle.get("body_type_name", "sedan").lower()
        year = vehicle.get("year") or datetime.now().year
        current_year = datetime.now().year
        age = max(0, current_year - year)
        
        # Base values by type
        base_values = {
            "suv": 4500000,
            "sedan": 3500000,
            "hatchback": 2500000,
            "pickup": 4000000,
            "van": 3800000,
            "truck": 6000000,
            "luxury": 8000000,
            "crossover": 3800000,
            "coupe": 5000000,
            "convertible": 5500000,
            "wagon": 3200000,
            "minivan": 3500000
        }
        
        base_value = base_values.get(body_type, 3000000)
        
        # Age depreciation
        base_value *= max(0.3, 1 - (age * 0.12))
        
        # Make adjustments
        luxury_makes = ["mercedes", "bmw", "audi", "lexus", "porsche", "range rover", "land rover"]
        premium_makes = ["toyota", "honda", "nissan", "mazda", "subaru", "volkswagen"]
        
        make_lower = make.lower()
        if any(m in make_lower for m in luxury_makes):
            base_value *= 1.4
        elif any(m in make_lower for m in premium_makes):
            base_value *= 1.0
        else:
            base_value *= 0.85
        
        # Engine size adjustment
        engine_cc = vehicle.get("engine_cc", 0)
        if engine_cc > 4000:
            base_value *= 1.3
        elif engine_cc > 3000:
            base_value *= 1.15
        elif engine_cc > 2000:
            base_value *= 1.0
        elif engine_cc > 1500:
            base_value *= 0.9
        else:
            base_value *= 0.75
        
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
    
    def _generate_recommendations(
        self,
        vehicle_data: Dict,
        costs: Dict,
        cost_per_km: float,
        market_data: Optional[Dict]
    ) -> List[str]:
        """Generate cost-saving recommendations"""
        recommendations = []
        
        # ─── Fuel recommendations ──────────────────────────────────
        fuel_cost = costs.get("fuel", 0)
        if fuel_cost > 0 and cost_per_km > 0:
            fuel_percentage = (fuel_cost / (cost_per_km * 100 if cost_per_km > 0 else 1)) * 100
            if fuel_percentage > 40:
                recommendations.append("Fuel costs are high. Consider eco-driving techniques.")
                if vehicle_data.get("fuel_type") == "petrol":
                    recommendations.append("Diesel or hybrid vehicles may offer better fuel economy.")
        
        # ─── Service recommendations ──────────────────────────────
        service_cost = costs.get("service", 0)
        if service_cost > 0 and cost_per_km > 0:
            service_percentage = (service_cost / (cost_per_km * 100 if cost_per_km > 0 else 1)) * 100
            if service_percentage > 20:
                recommendations.append("Service costs are significant. Regular maintenance can prevent costly repairs.")
        
        # ─── Tyre recommendations ──────────────────────────────────
        tyre_cost = costs.get("tyres", 0)
        if tyre_cost > 0 and cost_per_km > 0:
            tyre_percentage = (tyre_cost / (cost_per_km * 100 if cost_per_km > 0 else 1)) * 100
            if tyre_percentage > 15:
                recommendations.append("Tyre costs are high. Check tyre pressure regularly and rotate tyres.")
        
        # ─── Insurance recommendations ─────────────────────────────
        insurance_cost = costs.get("insurance", 0)
        if insurance_cost > 0 and cost_per_km > 0:
            insurance_percentage = (insurance_cost / (cost_per_km * 100 if cost_per_km > 0 else 1)) * 100
            if insurance_percentage > 15:
                recommendations.append("Insurance costs are significant. Shop around for better rates.")
        
        # ─── Depreciation recommendations ──────────────────────────
        dep_cost = costs.get("depreciation", 0)
        if dep_cost > 0 and cost_per_km > 0:
            dep_percentage = (dep_cost / (cost_per_km * 100 if cost_per_km > 0 else 1)) * 100
            if dep_percentage > 25:
                recommendations.append("Depreciation is high. Consider vehicles with better resale value.")
        
        # ─── Overall recommendations ──────────────────────────────
        if cost_per_km > 50:
            recommendations.append("Overall running cost is high. Consider a more fuel-efficient vehicle.")
        elif cost_per_km < 20:
            recommendations.append("Excellent running cost efficiency! Your vehicle is economical to operate.")
        
        # ─── Market recommendations ──────────────────────────────
        if market_data:
            health = market_data.get("metrics", {}).get("market_health", "unknown")
            if health == "limited":
                recommendations.append("Limited market data available. Consider getting professional advice.")
            elif health == "good":
                recommendations.append("Market data suggests good resale value for this vehicle.")
        
        if not recommendations:
            recommendations.append("Running costs are within expected range for this vehicle type.")
        
        return recommendations
