"""
Running Cost Engine - Auto-D Kenya
Professional cost calculation engine for vehicle operations
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
import math

logger = logging.getLogger(__name__)


@dataclass
class RunningCostResult:
    """Complete running cost result structure matching frontend expectations"""
    summary: Dict[str, Any] = field(default_factory=dict)
    fixed_costs: Dict[str, float] = field(default_factory=dict)
    operating_costs: Dict[str, float] = field(default_factory=dict)
    per_km_costs: Dict[str, float] = field(default_factory=dict)
    energy: Dict[str, Any] = field(default_factory=dict)
    environmental: Dict[str, Any] = field(default_factory=dict)
    projection: List[Dict[str, Any]] = field(default_factory=list)
    commercial_rates: Dict[str, float] = field(default_factory=dict)
    recommendations: List[Dict[str, str]] = field(default_factory=list)
    assumptions: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    
    def to_frontend_format(self) -> Dict[str, Any]:
        """Convert to frontend expected format"""
        return {
            "success": True,
            "data": {
                # Core results matching frontend
                "totalCost": self.summary.get("total_cost", 0),
                "fixedCost": self.summary.get("fixed_cost_total", 0),
                "operatingCost": self.summary.get("operating_cost_total", 0),
                "totalRate": self.summary.get("total_per_km", 0),
                "fixedRate": self.summary.get("breakdown", {}).get("fixed_per_km", 0),
                "operatingRate": self.summary.get("breakdown", {}).get("operating_per_km", 0),
                
                # Distance
                "distance_km": self.summary.get("distance_km", 0),
                
                # Detailed components (trip-level)
                "components": {
                    "Fuel": self.operating_costs.get("energy", 0),
                    "Oil": self.operating_costs.get("oil", 0),
                    "Tyres": self.operating_costs.get("tyres", 0),
                    "Service": self.operating_costs.get("maintenance", 0),
                    "Repairs": self.operating_costs.get("repairs", 0),
                    "Insurance": self.fixed_costs.get("insurance", 0),
                    "Depreciation": self.fixed_costs.get("depreciation", 0),
                    "Financing": self.fixed_costs.get("interest", 0),
                    "Fees": self.fixed_costs.get("licensing", 0),
                    "Battery Reserve": self.operating_costs.get("battery_reserve", 0)
                },
                
                # Per-km breakdown
                "perKmComponents": self.per_km_costs,
                
                # Yearly projection
                "yearly": {
                    f"year{i+1}": proj.get("cost_per_km", 0) 
                    for i, proj in enumerate(self.projection[:5])
                },
                
                # Commercial rates
                "privateCost": self.commercial_rates.get("private", 0),
                "fleetCost": self.commercial_rates.get("fleet", 0),
                "taxiRate": self.commercial_rates.get("taxi", 0),
                "recommendedRate": self.commercial_rates.get("recommended", 0),
                "deliveryPerParcel": self.commercial_rates.get("delivery", 0),
                "initialCost": self.summary.get("vehicle_price", 0),
                "currentValue": self.summary.get("current_value", 0),
                
                # Metrics
                "rci": self.summary.get("total_per_km", 0),
                "rciLabel": self._get_rci_label(self.summary.get("total_per_km", 0)),
                "rciStars": self._get_rci_stars(self.summary.get("total_per_km", 0)),
                "rciClass": self._get_rci_class(self.summary.get("total_per_km", 0)),
                "healthScore": self._calculate_health_score(),
                "healthLabel": self._get_health_label(),
                
                # Monthly & Annual
                "monthlyTotal": self.summary.get("monthly_total", 0),
                "annualTotal": self.summary.get("annual_total", 0),
                
                # Environmental
                "co2PerKm": self.environmental.get("co2_per_km", 0),
                "co2Trip": self.environmental.get("co2_emissions_kg", 0),
                "co2Annual": self.environmental.get("co2_annual", 0),
                "treesToOffset": self.environmental.get("trees_to_offset", 0),
                
                # Fuel info
                "fuelType": self.energy.get("fuel_type", "Unknown"),
                "fuelConsumption": self.energy.get("consumption", 0),
                "fuelPricePerUnit": self.energy.get("fuel_price", 0),
                
                # Vehicle info
                "vehicleName": self.summary.get("vehicle_name", "Unknown"),
                "fuelTypeDisplay": self.energy.get("fuel_type_display", "Unknown"),
                
                # Recommendations
                "recommendations": self.recommendations,
                
                # Metadata
                "method": "backend",
                "version": "4.0",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    
    def _get_rci_label(self, rci: float) -> str:
        if rci <= 20:
            return "Excellent"
        if rci <= 35:
            return "Good"
        if rci <= 50:
            return "Average"
        if rci <= 70:
            return "Expensive"
        return "Very Expensive"
    
    def _get_rci_stars(self, rci: float) -> str:
        if rci <= 20:
            return "★★★★★"
        if rci <= 35:
            return "★★★★"
        if rci <= 50:
            return "★★★"
        if rci <= 70:
            return "★★"
        return "★"
    
    def _get_rci_class(self, rci: float) -> str:
        if rci <= 20:
            return "excellent"
        if rci <= 35:
            return "good"
        if rci <= 50:
            return "average"
        if rci <= 70:
            return "expensive"
        return "very-expensive"
    
    def _calculate_health_score(self) -> int:
        """Calculate vehicle health score from available data"""
        score = 100
        # Age penalty
        age = self.summary.get("vehicle_age", 0)
        score -= age * 3
        # Efficiency bonus/penalty
        consumption = self.energy.get("consumption", 8)
        fuel_type = self.energy.get("fuel_type", "petrol")
        ideal = 20 if fuel_type == "electric" else (6 if fuel_type == "diesel" else 8)
        if consumption < ideal * 0.7:
            score += 5
        elif consumption > ideal * 1.3:
            score -= 5
        # Maintenance penalty
        maint_per_km = self.per_km_costs.get("Service", 0)
        if maint_per_km > 4:
            score -= 8
        elif maint_per_km > 3:
            score -= 3
        # Repair penalty
        repair_per_km = self.per_km_costs.get("Repairs", 0)
        if repair_per_km > 2:
            score -= 5
        # EV bonus
        if fuel_type == "electric":
            score += 5
        return max(0, min(100, score))
    
    def _get_health_label(self) -> str:
        score = self._calculate_health_score()
        if score >= 80:
            return "★★★★★ Excellent"
        if score >= 60:
            return "★★★★ Good"
        if score >= 40:
            return "★★★ Average"
        if score >= 20:
            return "★★ Needs Attention"
        return "★ Critical"


class RunningCostEngine:
    """
    Professional Running Cost Engine.
    Orchestrates all cost calculations for a trip.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        self.logger = logging.getLogger(__name__)
    
    def _default_config(self) -> Dict[str, Any]:
        return {
            "fuel_prices": {
                "petrol": 189.00,
                "diesel": 176.00,
                "lpg": 120.00,
                "electric": 8.50
            },
            "inflation_rate": 0.05,
            "depreciation_rate": 0.15,
            "maintenance_scaling": 0.08,
            "repair_scaling": 0.10,
            "tyre_scaling": 0.04,
            "insurance_scaling": 0.03,
            "interest_rate": 0.14,
            "profit_margin": 0.20,
            "co2_factors": {
                "petrol": 2.31,
                "diesel": 2.68,
                "lpg": 1.50,
                "electric": 0.20
            },
            "repair_bands": {
                "0-3": 0.80,
                "4-6": 1.50,
                "7-10": 3.00,
                "10+": 5.00
            },
            "driving_style": {
                "eco": {"fuel": -0.10, "maintenance": -0.05, "repairs": -0.08},
                "normal": {"fuel": 0, "maintenance": 0, "repairs": 0},
                "aggressive": {"fuel": 0.18, "maintenance": 0.12, "repairs": 0.15}
            },
            "trip_type": {
                "city": {"fuel": 0.20, "maintenance": 0.10, "repairs": 0.08, "tyres": 0.12},
                "highway": {"fuel": -0.05, "maintenance": -0.05, "repairs": -0.05, "tyres": -0.05},
                "mixed": {"fuel": 0.05, "maintenance": 0.02, "repairs": 0.02, "tyres": 0.02}
            },
            "usage_type": {
                "private": {"insurance": 1.0, "maintenance": 1.0, "repairs": 1.0, "overhead": 0},
                "commercial_passenger": {"insurance": 1.4, "maintenance": 1.3, "repairs": 1.4, "overhead": 3.0},
                "commercial_freight": {"insurance": 1.6, "maintenance": 1.5, "repairs": 1.6, "overhead": 4.0},
                "fleet": {"insurance": 1.2, "maintenance": 1.2, "repairs": 1.2, "overhead": 2.5},
                "taxi": {"insurance": 1.8, "maintenance": 1.6, "repairs": 1.8, "overhead": 5.0}
            }
        }
    
    def calculate_trip_cost(
        self,
        distance_km: float,
        vehicle_data: Dict[str, Any],
        trip_inputs: Optional[Dict[str, Any]] = None
    ) -> RunningCostResult:
        """
        Calculate complete trip cost breakdown.
        
        Args:
            distance_km: Distance in kilometers
            vehicle_data: Vehicle specifications
            trip_inputs: Optional trip parameters (driving style, trip type, etc.)
        
        Returns:
            RunningCostResult with all costs
        """
        trip_inputs = trip_inputs or {}
        
        # ─── Extract Vehicle Data ──────────────────────────────────
        fuel_type = vehicle_data.get("fuel_type", "petrol").lower()
        fuel_consumption = float(vehicle_data.get("fuel_consumption", 8.0))
        purchase_price = float(vehicle_data.get("initial_cost", 0))
        current_value = float(vehicle_data.get("current_value", purchase_price * 0.8))
        
        # ─── Extract Trip Inputs ──────────────────────────────────
        driving_style = trip_inputs.get("driving_style", "normal")
        trip_type = trip_inputs.get("trip_type", "mixed")
        usage_type = trip_inputs.get("usage_type", "private")
        year = trip_inputs.get("year", 2020)
        fuel_price = trip_inputs.get("fuel_price", None)
        annual_km = trip_inputs.get("annual_km", 20000)
        
        # ─── Calculate ────────────────────────────────────────────
        age = self._get_vehicle_age(year)
        actual_consumption = self._calculate_actual_consumption(
            fuel_consumption, driving_style, trip_type, usage_type, age
        )
        
        # Get fuel price
        fuel_price_per_unit = self._get_fuel_price(fuel_type, fuel_price)
        
        # Calculate energy cost
        energy_result = self._calculate_energy_cost(
            fuel_type, actual_consumption, distance_km, fuel_price_per_unit
        )
        
        # Calculate fixed costs
        fixed_costs = self._calculate_fixed_costs(
            vehicle_data, distance_km, annual_km, age, usage_type
        )
        
        # Calculate operating costs
        operating_costs = self._calculate_operating_costs(
            vehicle_data, distance_km, annual_km, age,
            driving_style, trip_type, usage_type, actual_consumption,
            fuel_price_per_unit, fuel_type
        )
        
        # Calculate per-km costs
        per_km_costs = self._calculate_per_km_costs(
            operating_costs, fixed_costs, distance_km, annual_km
        )
        
        # Calculate totals
        total_cost = sum(operating_costs.values()) + sum(fixed_costs.values())
        total_per_km = total_cost / distance_km if distance_km > 0 else 0
        
        # Calculate commercial rates
        commercial_rates = self._calculate_commercial_rates(
            total_per_km, usage_type
        )
        
        # Calculate environmental impact
        environmental = self._calculate_environmental(
            fuel_type, actual_consumption, distance_km, annual_km
        )
        
        # Calculate 5-year projection
        projection = self._calculate_projection(
            vehicle_data, operating_costs, fixed_costs,
            distance_km, annual_km, age, fuel_type
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            vehicle_data=vehicle_data,
            operating_costs=operating_costs,
            fixed_costs=fixed_costs,
            total_per_km=total_per_km,
            age=age,
            fuel_type=fuel_type,
            usage_type=usage_type,
            actual_consumption=actual_consumption,
            distance_km=distance_km
        )
        
        # Build summary
        summary = {
            "total_cost": round(total_cost, 2),
            "total_per_km": round(total_per_km, 2),
            "distance_km": distance_km,
            "energy_cost": round(operating_costs.get("energy", 0), 2),
            "energy_per_km": round(operating_costs.get("energy", 0) / distance_km if distance_km > 0 else 0, 2),
            "operating_cost_total": round(sum(operating_costs.values()), 2),
            "fixed_cost_total": round(sum(fixed_costs.values()), 2),
            "monthly_total": round(total_cost * (annual_km / 12) / distance_km if distance_km > 0 else 0, 2),
            "annual_total": round(total_cost * annual_km / distance_km if distance_km > 0 else 0, 2),
            "vehicle_name": vehicle_data.get("label", "Unknown"),
            "vehicle_price": purchase_price,
            "current_value": current_value,
            "vehicle_age": age,
            "breakdown": {
                "fixed_per_km": round(sum(fixed_costs.values()) / distance_km if distance_km > 0 else 0, 2),
                "operating_per_km": round(sum(operating_costs.values()) / distance_km if distance_km > 0 else 0, 2)
            }
        }
        
        # Build assumptions
        assumptions = {
            "fuel_price": fuel_price_per_unit,
            "fuel_price_source": "user_input" if fuel_price else "default",
            "annual_mileage": annual_km,
            "depreciation_method": "Declining Balance",
            "interest_rate": self.config["interest_rate"],
            "vehicle_condition": vehicle_data.get("condition", "Good"),
            "driving_style": driving_style,
            "trip_type": trip_type,
            "usage_type": usage_type,
            "vehicle_year": year,
            "vehicle_age": age
        }
        
        # Generate warnings
        warnings = self._generate_warnings(vehicle_data, distance_km, annual_km)
        
        return RunningCostResult(
            summary=summary,
            fixed_costs={k: round(v, 2) for k, v in fixed_costs.items()},
            operating_costs={k: round(v, 2) for k, v in operating_costs.items()},
            per_km_costs={k: round(v, 2) for k, v in per_km_costs.items()},
            energy=energy_result,
            environmental=environmental,
            projection=projection,
            commercial_rates=commercial_rates,
            recommendations=recommendations,
            assumptions=assumptions,
            warnings=warnings
        )
    
    def _get_vehicle_age(self, year: int) -> int:
        current_year = datetime.utcnow().year
        return max(0, current_year - year)
    
    def _get_fuel_price(self, fuel_type: str, user_price: Optional[float]) -> float:
        if user_price and user_price > 0:
            return user_price
        return self.config["fuel_prices"].get(fuel_type, 189.00)
    
    def _calculate_actual_consumption(
        self, 
        base_consumption: float,
        driving_style: str,
        trip_type: str,
        usage_type: str,
        age: int
    ) -> float:
        style_adj = self.config["driving_style"].get(driving_style, {}).get("fuel", 0)
        trip_adj = self.config["trip_type"].get(trip_type, {}).get("fuel", 0)
        consumption = base_consumption * (1 + style_adj + trip_adj)
        
        # Usage adjustments
        if usage_type == "commercial_freight":
            consumption *= 1.08
        elif usage_type == "taxi":
            consumption *= 1.05
        
        # Age adjustment (older vehicles less efficient)
        consumption *= (1 + age * 0.003)
        
        return round(consumption, 2)
    
    def _calculate_energy_cost(
        self,
        fuel_type: str,
        consumption: float,
        distance_km: float,
        fuel_price: float
    ) -> Dict[str, Any]:
        if fuel_type == "electric":
            # consumption is in km/kWh, we need kWh per km
            energy_used = distance_km / consumption
            energy_cost = energy_used * fuel_price
            unit = "kWh"
        else:
            # consumption is in km/L, we need L per km
            energy_used = distance_km / consumption
            energy_cost = energy_used * fuel_price
            unit = "L"
        
        return {
            "fuel_type": fuel_type,
            "fuel_type_display": fuel_type.capitalize(),
            "fuel_price": fuel_price,
            "consumption": consumption,
            "energy_used": round(energy_used, 2),
            "energy_unit": unit,
            "energy_cost": round(energy_cost, 2),
            "energy_per_km": round(energy_cost / distance_km if distance_km > 0 else 0, 2),
            "source": "user_input"
        }
    
    def _calculate_fixed_costs(
        self,
        vehicle_data: Dict[str, Any],
        distance_km: float,
        annual_km: float,
        age: int,
        usage_type: str
    ) -> Dict[str, float]:
        costs = {}
        
        # Insurance
        insurance_annual = float(vehicle_data.get("insurance_annual", 60000))
        usage_adj = self.config["usage_type"].get(usage_type, {}).get("insurance", 1.0)
        insurance_annual *= usage_adj
        insurance_annual *= (1 - age * 0.02)  # Decreases with age
        insurance_annual = max(insurance_annual, insurance_annual * 0.5)
        costs["insurance"] = (insurance_annual / annual_km) * distance_km if annual_km > 0 else 0
        
        # Depreciation
        purchase_price = float(vehicle_data.get("initial_cost", 0))
        current_value = float(vehicle_data.get("current_value", purchase_price * 0.8))
        expected_resale = float(vehicle_data.get("expected_resale", purchase_price * 0.4))
        years_remaining = float(vehicle_data.get("years_remaining", max(1, 10 - age)))
        
        total_loss = current_value - expected_resale
        distance_remaining = years_remaining * annual_km
        depreciation_per_km = max(0, total_loss / max(distance_remaining, 1))
        costs["depreciation"] = depreciation_per_km * distance_km
        
        # Licensing/Fees
        fees_annual = float(vehicle_data.get("tax_annual", 8000))
        if usage_type == "commercial_passenger":
            fees_annual += 5000
        elif usage_type == "commercial_freight":
            fees_annual += 8000
        elif usage_type == "taxi":
            fees_annual += 10000
        elif usage_type == "fleet":
            fees_annual += 3000
        costs["licensing"] = (fees_annual / annual_km) * distance_km if annual_km > 0 else 0
        
        # Interest/Financing
        loan_amount = float(vehicle_data.get("loan_amount", purchase_price * 0.8))
        if usage_type == "private" and not vehicle_data.get("loan_amount"):
            # Opportunity cost for cash purchase
            opportunity_rate = 0.10
            interest_annual = purchase_price * opportunity_rate
        else:
            interest_annual = loan_amount * self.config["interest_rate"]
        
        costs["interest"] = (interest_annual / annual_km) * distance_km if annual_km > 0 else 0
        
        return costs
    
    def _calculate_operating_costs(
        self,
        vehicle_data: Dict[str, Any],
        distance_km: float,
        annual_km: float,
        age: int,
        driving_style: str,
        trip_type: str,
        usage_type: str,
        actual_consumption: float,
        fuel_price: float,
        fuel_type: str
    ) -> Dict[str, float]:
        costs = {}
        
        # Energy (Fuel/Electricity)
        if fuel_type == "electric":
            energy_cost = (distance_km / actual_consumption) * fuel_price
        else:
            energy_cost = (distance_km / actual_consumption) * fuel_price
        costs["energy"] = energy_cost
        
        # Oil
        oil_interval = float(vehicle_data.get("oil_interval", 10000))
        oil_cost = float(vehicle_data.get("oil_cost", 6000))
        oil_per_km = oil_cost / oil_interval if oil_interval > 0 else 0
        costs["oil"] = oil_per_km * distance_km
        
        # Tyres
        tyre_cost = float(vehicle_data.get("tyre_cost", 120000))
        tyre_life = float(vehicle_data.get("tyre_life", 50000))
        tyre_per_km = tyre_cost / tyre_life if tyre_life > 0 else 0
        
        # Trip type tyre adjustment
        trip_tyre_adj = self.config["trip_type"].get(trip_type, {}).get("tyres", 0)
        tyre_per_km *= (1 + trip_tyre_adj)
        
        # Usage tyre adjustment
        if usage_type == "commercial_freight":
            tyre_per_km *= 1.15
        elif usage_type == "taxi":
            tyre_per_km *= 1.20
        
        costs["tyres"] = tyre_per_km * distance_km
        
        # Service/Maintenance
        minor_interval = float(vehicle_data.get("minor_service_interval", 10000))
        minor_cost = float(vehicle_data.get("minor_service_cost", 15000))
        major_interval = float(vehicle_data.get("major_service_interval", 40000))
        major_cost = float(vehicle_data.get("major_service_cost", 45000))
        
        minor_per_km = minor_cost / minor_interval if minor_interval > 0 else 0
        major_per_km = major_cost / major_interval if major_interval > 0 else 0
        service_per_km = minor_per_km + major_per_km
        
        # Adjustments
        style_maint = self.config["driving_style"].get(driving_style, {}).get("maintenance", 0)
        trip_maint = self.config["trip_type"].get(trip_type, {}).get("maintenance", 0)
        usage_maint = self.config["usage_type"].get(usage_type, {}).get("maintenance", 1.0)
        service_per_km *= (1 + style_maint + trip_maint + (usage_maint - 1))
        service_per_km *= (1 + age * 0.015)  # Age adjustment
        
        costs["maintenance"] = service_per_km * distance_km
        
        # Repairs
        repair_per_km = self._get_repair_rate(age)
        style_repair = self.config["driving_style"].get(driving_style, {}).get("repairs", 0)
        trip_repair = self.config["trip_type"].get(trip_type, {}).get("repairs", 0)
        usage_repair = self.config["usage_type"].get(usage_type, {}).get("repairs", 1.0)
        repair_per_km *= (1 + style_repair + trip_repair + (usage_repair - 1))
        repair_per_km *= (1 + (annual_km / 30000) * 0.1)  # Mileage adjustment
        
        costs["repairs"] = repair_per_km * distance_km
        
        # Battery Reserve (EV)
        if fuel_type == "electric":
            battery_cost = float(vehicle_data.get("battery_cost", 1200000))
            battery_life = float(vehicle_data.get("battery_life", 250000))
            battery_per_km = battery_cost / battery_life if battery_life > 0 else 0
            costs["battery_reserve"] = battery_per_km * distance_km
        
        return costs
    
    def _get_repair_rate(self, age: int) -> float:
        bands = self.config["repair_bands"]
        if age <= 3:
            return bands["0-3"]
        elif age <= 6:
            return bands["4-6"]
        elif age <= 10:
            return bands["7-10"]
        else:
            return bands["10+"]
    
    def _calculate_per_km_costs(
        self,
        operating_costs: Dict[str, float],
        fixed_costs: Dict[str, float],
        distance_km: float,
        annual_km: float
    ) -> Dict[str, float]:
        per_km = {}
        
        # Operating costs per km
        for key, value in operating_costs.items():
            per_km[key.capitalize()] = value / distance_km if distance_km > 0 else 0
        
        # Fixed costs per km
        for key, value in fixed_costs.items():
            per_km[key.capitalize()] = value / distance_km if distance_km > 0 else 0
        
        return per_km
    
    def _calculate_commercial_rates(
        self,
        total_per_km: float,
        usage_type: str
    ) -> Dict[str, float]:
        overhead = self.config["usage_type"].get(usage_type, {}).get("overhead", 0)
        profit_margin = self.config["profit_margin"]
        
        return {
            "private": round(total_per_km, 2),
            "fleet": round(total_per_km + overhead, 2),
            "taxi": round(total_per_km * (1 + profit_margin + 0.15), 2),
            "recommended": round(total_per_km * (1 + profit_margin), 2),
            "delivery": round(total_per_km * 1.25 * 15, 2)  # 15km average delivery
        }
    
    def _calculate_environmental(
        self,
        fuel_type: str,
        consumption: float,
        distance_km: float,
        annual_km: float
    ) -> Dict[str, Any]:
        co2_factor = self.config["co2_factors"].get(fuel_type, 2.31)
        co2_per_km = co2_factor / consumption if consumption > 0 else 0
        
        return {
            "co2_emissions_kg": round(co2_per_km * distance_km, 2),
            "co2_per_km": round(co2_per_km, 2),
            "co2_annual": round(co2_per_km * annual_km, 2),
            "trees_to_offset": round((co2_per_km * annual_km) / 20, 2),  # 20kg CO2 per tree/year
            "fuel_type": fuel_type
        }
    
    def _calculate_projection(
        self,
        vehicle_data: Dict[str, Any],
        operating_costs: Dict[str, float],
        fixed_costs: Dict[str, float],
        distance_km: float,
        annual_km: float,
        age: int,
        fuel_type: str
    ) -> List[Dict[str, Any]]:
        projection = []
        
        # Base values
        base_fuel = operating_costs.get("energy", 0) * (annual_km / distance_km) if distance_km > 0 else 0
        base_service = operating_costs.get("maintenance", 0) * (annual_km / distance_km) if distance_km > 0 else 0
        base_repair = operating_costs.get("repairs", 0) * (annual_km / distance_km) if distance_km > 0 else 0
        base_tyre = operating_costs.get("tyres", 0) * (annual_km / distance_km) if distance_km > 0 else 0
        base_insurance = fixed_costs.get("insurance", 0) * (annual_km / distance_km) if distance_km > 0 else 0
        base_depreciation = fixed_costs.get("depreciation", 0) * (annual_km / distance_km) if distance_km > 0 else 0
        base_interest = fixed_costs.get("interest", 0) * (annual_km / distance_km) if distance_km > 0 else 0
        base_fees = fixed_costs.get("licensing", 0) * (annual_km / distance_km) if distance_km > 0 else 0
        base_battery = operating_costs.get("battery_reserve", 0) * (annual_km / distance_km) if distance_km > 0 else 0
        
        purchase_price = float(vehicle_data.get("initial_cost", 0))
        current_value = float(vehicle_data.get("current_value", purchase_price * 0.8))
        
        for year in range(1, 6):
            infl = self.config["inflation_rate"]
            
            fuel = base_fuel * (1 + infl) ** year
            service = base_service * (1 + infl + self.config["maintenance_scaling"]) ** year
            repair = base_repair * (1 + infl + self.config["repair_scaling"]) ** year
            tyre = base_tyre * (1 + self.config["tyre_scaling"] * year)
            insurance = base_insurance * (1 + infl + self.config["insurance_scaling"]) ** year
            depreciation = base_depreciation * (1 - 0.15 * year)
            interest = base_interest * (1 - 0.2 * year)
            fees = base_fees * (1 + infl * 0.5 * year)
            battery = base_battery * (1 + infl * year * 0.5)
            
            total = fuel + service + repair + tyre + insurance + depreciation + interest + fees + battery
            
            # Vehicle value
            value = current_value * (1 - 0.15 * year)
            
            projection.append({
                "year": year,
                "total_cost": round(total, 2),
                "cost_per_km": round(total / annual_km if annual_km > 0 else 0, 2),
                "vehicle_value": round(max(value, 0), 2),
                "depreciation": round(depreciation, 2),
                "fuel": round(fuel, 2),
                "maintenance": round(service, 2),
                "repairs": round(repair, 2),
                "tyres": round(tyre, 2),
                "insurance": round(insurance, 2),
                "interest": round(interest, 2),
                "fees": round(fees, 2),
                "battery_reserve": round(battery, 2) if fuel_type == "electric" else 0
            })
        
        return projection
    
    def _generate_recommendations(
        self,
        vehicle_data: Dict[str, Any],
        operating_costs: Dict[str, float],
        fixed_costs: Dict[str, float],
        total_per_km: float,
        age: int,
        fuel_type: str,
        usage_type: str,
        actual_consumption: float,
        distance_km: float
    ) -> List[Dict[str, str]]:
        """Generate AI-style recommendations based on calculated costs"""
        recommendations = []
        
        # Energy/Fuel cost
        energy = operating_costs.get("energy", 0)
        energy_per_km = energy / distance_km if distance_km > 0 else 0
        
        if energy_per_km > 20:
            recommendations.append({
                "icon": "⛽",
                "text": f"Fuel cost ({energy_per_km:.2f} KES/km) is high. Consider diesel or EV if feasible.",
                "type": "warning",
                "tag": "Fuel"
            })
        
        # Service/Maintenance cost
        service = operating_costs.get("maintenance", 0)
        service_per_km = service / distance_km if distance_km > 0 else 0
        if service_per_km > 3:
            recommendations.append({
                "icon": "🔧",
                "text": f"Service cost ({service_per_km:.2f} KES/km) is high. Consider extended service intervals.",
                "type": "warning",
                "tag": "Service"
            })
        
        # Tyre cost
        tyres = operating_costs.get("tyres", 0)
        tyre_per_km = tyres / distance_km if distance_km > 0 else 0
        if tyre_per_km > 3:
            recommendations.append({
                "icon": "🛞",
                "text": f"Tyre cost ({tyre_per_km:.2f} KES/km) is high. Check pressure and alignment regularly.",
                "type": "info",
                "tag": "Tyres"
            })
        
        # Depreciation
        dep = fixed_costs.get("depreciation", 0)
        dep_per_km = dep / distance_km if distance_km > 0 else 0
        if dep_per_km > 20:
            recommendations.append({
                "icon": "📉",
                "text": f"Depreciation ({dep_per_km:.2f} KES/km) is high. Consider buying used or different model.",
                "type": "warning",
                "tag": "Depreciation"
            })
        
        # Age-based recommendation
        if age > 10:
            repair = operating_costs.get("repairs", 0)
            repair_per_km = repair / distance_km if distance_km > 0 else 0
            recommendations.append({
                "icon": "🏥",
                "text": f"Vehicle is {age} years old. Repair costs ({repair_per_km:.2f} KES/km) are rising. Consider replacement.",
                "type": "warning",
                "tag": "Age"
            })
        
        # EV recommendation
        if fuel_type == "electric":
            savings = max(0, energy_per_km - 5)
            recommendations.append({
                "icon": "🌱",
                "text": f"Great EV choice! Save {savings:.2f} KES/km vs petrol. Zero tailpipe emissions.",
                "type": "success",
                "tag": "Green"
            })
        elif fuel_type in ["petrol", "diesel"] and energy_per_km > 15:
            savings = energy_per_km - 5
            recommendations.append({
                "icon": "⚡",
                "text": f"Consider switching to electric. You could save up to {savings:.2f} KES/km on fuel costs.",
                "type": "info",
                "tag": "EV"
            })
        
        # Usage-specific recommendations
        if usage_type == "taxi" and total_per_km > 30:
            recommendations.append({
                "icon": "🚖",
                "text": f"Operating cost ({total_per_km:.2f} KES/km) is high for taxi. Consider LPG or EV conversion.",
                "type": "warning",
                "tag": "Taxi"
            })
        
        if usage_type == "commercial_freight" and total_per_km > 40:
            recommendations.append({
                "icon": "📦",
                "text": f"High operating cost ({total_per_km:.2f} KES/km) for freight. Consider fleet optimization.",
                "type": "warning",
                "tag": "Freight"
            })
        
        if usage_type == "fleet" and total_per_km > 35:
            recommendations.append({
                "icon": "🏢",
                "text": f"Fleet cost ({total_per_km:.2f} KES/km) is above average. Review maintenance schedules and fuel contracts.",
                "type": "warning",
                "tag": "Fleet"
            })
        
        # RCI-based recommendation
        if total_per_km > 50:
            recommendations.append({
                "icon": "💰",
                "text": f"RCI ({total_per_km:.2f} KES/km) is in the 'Expensive' range. Review all cost categories.",
                "type": "warning",
                "tag": "Cost"
            })
        elif total_per_km <= 20:
            recommendations.append({
                "icon": "🌟",
                "text": f"Excellent RCI ({total_per_km:.2f} KES/km)! Your vehicle is very cost-efficient.",
                "type": "success",
                "tag": "Excellent"
            })
        
        # Health score recommendation
        # Create a temporary result to calculate health score
        temp_result = RunningCostResult(
            summary={"vehicle_age": age},
            energy={"consumption": actual_consumption, "fuel_type": fuel_type},
            per_km_costs={"Service": service_per_km, "Repairs": repair_per_km if 'repair_per_km' in locals() else 0}
        )
        health_score = temp_result._calculate_health_score()
        if health_score < 50:
            recommendations.append({
                "icon": "🏥",
                "text": f"Vehicle health score ({health_score}/100) is low. Schedule comprehensive inspection.",
                "type": "warning",
                "tag": "Health"
            })
        
        # Default if no recommendations
        if not recommendations:
            recommendations.append({
                "icon": "✅",
                "text": "Vehicle performing well across all metrics. Continue regular maintenance.",
                "type": "success",
                "tag": "All Good"
            })
        
        return recommendations
    
    def _generate_warnings(
        self,
        vehicle_data: Dict[str, Any],
        distance_km: float,
        annual_km: float
    ) -> List[str]:
        warnings = []
        
        if vehicle_data.get("initial_cost", 0) <= 0:
            warnings.append("Purchase price not provided. Using estimates.")
        
        if vehicle_data.get("fuel_consumption", 0) <= 0:
            warnings.append("Fuel consumption not provided. Using default values.")
        
        if annual_km <= 0:
            warnings.append("Annual mileage not provided. Using default 20,000 km.")
        
        if distance_km <= 0:
            warnings.append("Distance must be greater than 0.")
        
        return warnings
