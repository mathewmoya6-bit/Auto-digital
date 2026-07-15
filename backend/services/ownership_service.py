"""
Ownership Service - Auto-D Kenya
Service for calculating total cost of vehicle ownership
Serves: ownership-cost.html
Endpoint: /api/service/ownership
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

# Import the ownership engine
try:
    from engines.ownership_engine import OwnershipEngine, calculate_ownership_cost
    ENGINE_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ OwnershipEngine imported successfully")
except ImportError as e:
    ENGINE_AVAILABLE = False
    logging.getLogger(__name__).warning(f"⚠️ OwnershipEngine import failed: {e}")
    OwnershipEngine = None
    calculate_ownership_cost = None

logger = logging.getLogger(__name__)


class OwnershipService:
    """
    Service class for vehicle ownership cost calculation.
    
    Provides methods to calculate total cost of ownership including:
    - Purchase price
    - Loan/interest
    - Insurance
    - Fuel
    - Maintenance
    - Repairs
    - Tyres
    - Depreciation
    - Resale value
    - RCI Rating
    - Vehicle Health Score
    - Environmental Impact
    - AI Recommendations
    """
    
    def __init__(self):
        """Initialize the Ownership Service"""
        self.engine = OwnershipEngine() if ENGINE_AVAILABLE else None
        self.logger = logging.getLogger(__name__)
        
        if self.engine:
            self.logger.info("✅ OwnershipEngine initialized in OwnershipService")
        else:
            self.logger.warning("⚠️ OwnershipEngine not available - using simple calculations")
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate ownership cost from request data.
        
        Args:
            data: Request data containing ownership parameters
            
        Returns:
            Dict with ownership cost results matching frontend format
        
        Expected input format (vehicle database):
        {
            "make": "toyota",
            "model": "prado",
            "years_owned": 5,
            "annual_mileage": 20000,
            "financed": true,
            "down_pct": 30,
            "interest_rate": 16,
            "loan_term": 4,
            "driving_locations": ["nairobi"],
            "fuel_type": "diesel",
            "insurance_rate": 4.5,
            "insurance_type": "comprehensive",
            "year": 2020,
            "engine_cc": 2800,
            "transmission": "automatic"
        }
        """
        try:
            # Check if using vehicle database or manual input
            make = data.get("make")
            model = data.get("model")
            
            if make and model:
                # Use vehicle database
                result = self._calculate_from_vehicle(data)
            else:
                # Manual input
                result = self._calculate_manual(data)
            
            if "error" in result:
                return result
            
            # Ensure result has proper frontend format
            formatted_result = self._format_for_frontend(result, data)
            
            return {
                "success": True,
                "data": formatted_result,
                "service": "ownership",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Ownership calculation error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Ownership calculation failed: {str(e)}"
            }
    
    def _calculate_manual(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate ownership cost from manual input"""
        required_fields = ["purchase_price", "years_owned", "fuel_cost",
                          "maintenance_cost", "insurance_cost", "taxes"]
        
        missing_fields = [field for field in required_fields if data.get(field) is None]
        if missing_fields:
            return {
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }
        
        try:
            purchase_price = float(data.get("purchase_price"))
            years_owned = float(data.get("years_owned"))
            fuel_cost = float(data.get("fuel_cost"))
            maintenance_cost = float(data.get("maintenance_cost"))
            insurance_cost = float(data.get("insurance_cost"))
            taxes = float(data.get("taxes"))
            resale_value = float(data.get("resale_value", purchase_price * 0.3))
            
            if purchase_price < 0 or years_owned < 0:
                raise ValueError
        except ValueError:
            return {"error": "All numeric fields must be valid positive numbers"}
        
        if callable(calculate_ownership_cost):
            return calculate_ownership_cost(
                purchase_price=purchase_price,
                years_owned=years_owned,
                fuel_cost=fuel_cost,
                maintenance_cost=maintenance_cost,
                insurance_cost=insurance_cost,
                taxes=taxes,
                resale_value=resale_value
            )
        else:
            # Fallback calculation
            total_operating_cost = fuel_cost + maintenance_cost + insurance_cost + taxes
            total_cost = purchase_price + total_operating_cost - resale_value
            annual_cost = total_cost / years_owned if years_owned > 0 else 0
            
            return {
                "purchase_price": round(purchase_price, 2),
                "years_owned": years_owned,
                "fuel_cost": round(fuel_cost, 2),
                "maintenance_cost": round(maintenance_cost, 2),
                "insurance_cost": round(insurance_cost, 2),
                "taxes": round(taxes, 2),
                "resale_value": round(resale_value, 2),
                "total_operating_cost": round(total_operating_cost, 2),
                "total_cost": round(total_cost, 2),
                "annual_cost": round(annual_cost, 2),
                "cost_per_km": round(annual_cost / 20000, 2) if years_owned > 0 else 0,
                "cost_per_month": round(annual_cost / 12, 2) if years_owned > 0 else 0
            }
    
    def _calculate_from_vehicle(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate ownership cost using vehicle database with full breakdown"""
        make = data.get("make")
        model = data.get("model")
        years_owned = int(data.get("years_owned", 5))
        annual_mileage = int(data.get("annual_mileage", 20000))
        
        # Try to get vehicle data
        try:
            from vehicle_data import get_vehicle_data
            vehicle = get_vehicle_data(make, model)
        except ImportError:
            # Fallback vehicle data
            vehicle = self._get_fallback_vehicle(make, model)
        
        if not vehicle:
            return {"error": f"Vehicle '{make} {model}' not found"}
        
        base_price = float(vehicle.get("price", 0))
        fuel_efficiency = float(vehicle.get("fuel", 15))
        maintenance_per_km = float(vehicle.get("maintenancePerKm", 5))
        service_interval = float(vehicle.get("serviceInterval", 10000))
        minor_cost = float(vehicle.get("minor", 15000))
        major_cost = float(vehicle.get("major", 45000))
        
        # Get fuel price based on fuel type
        fuel_type = data.get("fuel_type", "petrol")
        fuel_price = self._get_fuel_price(fuel_type)
        
        # Location multipliers
        locations = data.get("driving_locations", [])
        fuel_mult, maint_mult, tyre_mult, ins_mult = self._get_location_multipliers(locations)
        
        # Insurance
        insurance_rate = float(data.get("insurance_rate", 4.5)) / 100
        insurance_annual = base_price * insurance_rate * ins_mult
        
        # Financing
        financed = data.get("financed", False)
        financing_total = 0
        if financed:
            down_pct = float(data.get("down_pct", 30)) / 100
            interest_rate = float(data.get("interest_rate", 16)) / 100
            loan_term = int(data.get("loan_term", 4))
            loan_balance = base_price * (1 - down_pct)
            if loan_term > 0 and interest_rate > 0:
                monthly_rate = interest_rate / 12
                num_payments = loan_term * 12
                monthly_payment = loan_balance * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
                financing_total = monthly_payment * 12 * years_owned
        
        # Calculate yearly breakdown
        rows = []
        vehicle_value = base_price
        total_cost = 0
        
        for year in range(1, years_owned + 1):
            # Depreciation
            dep_rate = 0.12 * (1 + (year - 1) * 0.08)
            depreciation = vehicle_value * min(dep_rate, 0.40)
            vehicle_value -= depreciation
            
            # Insurance (decreases with vehicle value)
            insurance = max(vehicle_value, base_price * 0.15) * insurance_rate * ins_mult
            
            # Fuel
            litres = annual_mileage / max(fuel_efficiency, 0.1)
            fuel = litres * fuel_price * fuel_mult
            
            # Maintenance (increases with age)
            age_multiplier = 1 + (year - 1) * 0.08
            maintenance = annual_mileage * maintenance_per_km * maint_mult * age_multiplier
            
            # Tyres (every 45,000 km)
            tyre_cost = 20000 if "tyres" not in vehicle else 32000
            tyres = (annual_mileage / 45000) * tyre_cost * tyre_mult
            
            # Licensing
            licensing = 5000 + (year > 1 and year <= years_owned and year * 1000 or 0)
            
            # Financing (only for first loan_term years)
            financing = financing_total / years_owned if financed and year <= loan_term else 0
            
            year_total = depreciation + financing + insurance + fuel + maintenance + tyres + licensing
            total_cost += year_total
            
            rows.append({
                "year": year,
                "depreciation": round(depreciation, 2),
                "financing": round(financing, 2),
                "insurance": round(insurance, 2),
                "fuel": round(fuel, 2),
                "maintenance": round(maintenance, 2),
                "tyres": round(tyres, 2),
                "licensing": round(licensing, 2),
                "total": round(year_total, 2),
                "vehicleValue": round(max(vehicle_value, base_price * 0.05), 2)
            })
        
        resale_value = max(vehicle_value, base_price * 0.05)
        total_km = annual_mileage * years_owned
        cost_per_km = total_cost / total_km if total_km > 0 else 0
        cost_per_month = total_cost / (years_owned * 12)
        
        # ─── RCI ──────────────────────────────────────────────────────
        rci = cost_per_km
        rci_label, rci_stars, rci_class = self._get_rci_rating(rci)
        
        # ─── Health Score ────────────────────────────────────────────
        age = datetime.utcnow().year - int(data.get("year", 2020))
        health_score = self._calculate_health_score(
            age=age,
            fuel_efficiency=fuel_efficiency,
            fuel_type=fuel_type,
            maintenance_per_km=maintenance_per_km
        )
        health_label = self._get_health_label(health_score)
        
        # ─── Environmental ───────────────────────────────────────────
        co2_per_km = self._get_co2_factor(fuel_type) / max(fuel_efficiency, 0.1)
        co2_annual = co2_per_km * annual_mileage
        trees_to_offset = co2_annual / 20
        
        # ─── Recommendations ─────────────────────────────────────────
        recommendations = self._generate_recommendations(
            cost_per_km=cost_per_km,
            rci=rci,
            health_score=health_score,
            age=age,
            fuel_type=fuel_type,
            financed=financed,
            total_cost=total_cost,
            financing_total=financing_total
        )
        
        # ─── Return full result ──────────────────────────────────────
        return {
            "vehicle": {
                "make": make,
                "model": model,
                "base_price": base_price,
                "fuel_efficiency": fuel_efficiency,
                "fuel_type": fuel_type,
                "year": data.get("year", 2020),
                "engine_cc": data.get("engine_cc", 0),
                "transmission": data.get("transmission", "automatic")
            },
            "summary": {
                "total_cost": round(total_cost, 2),
                "cost_per_month": round(cost_per_month, 2),
                "cost_per_km": round(cost_per_km, 2),
                "resale_value": round(resale_value, 2),
                "total_depreciation": round(base_price - resale_value, 2),
                "value_retained": round((resale_value / base_price) * 100, 2)
            },
            "yearly_breakdown": rows,
            "costs": {
                "purchase": round(base_price, 2),
                "fuel": round(sum(r["fuel"] for r in rows), 2),
                "maintenance": round(sum(r["maintenance"] for r in rows), 2),
                "insurance": round(sum(r["insurance"] for r in rows), 2),
                "tyres": round(sum(r["tyres"] for r in rows), 2),
                "licensing": round(sum(r["licensing"] for r in rows), 2),
                "depreciation": round(sum(r["depreciation"] for r in rows), 2),
                "financing": round(sum(r["financing"] for r in rows), 2)
            },
            "metrics": {
                "rci": round(rci, 2),
                "rci_label": rci_label,
                "rci_stars": rci_stars,
                "rci_class": rci_class,
                "health_score": round(health_score),
                "health_label": health_label,
                "co2_per_km": round(co2_per_km, 2),
                "co2_annual": round(co2_annual, 2),
                "trees_to_offset": round(trees_to_offset, 2)
            },
            "recommendations": recommendations
        }
    
    def _format_for_frontend(self, result: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Format result for frontend consumption (ownership-cost.html)"""
        if "yearly_breakdown" in result:
            # Vehicle database result
            rows = result.get("yearly_breakdown", [])
            summary = result.get("summary", {})
            costs = result.get("costs", {})
            metrics = result.get("metrics", {})
            vehicle = result.get("vehicle", {})
            
            return {
                "totalCost": summary.get("total_cost", 0),
                "costPerMonth": summary.get("cost_per_month", 0),
                "costPerKm": summary.get("cost_per_km", 0),
                "resaleValue": summary.get("resale_value", 0),
                "totalDepreciation": summary.get("total_depreciation", 0),
                "valueRetained": summary.get("value_retained", 0),
                "yearlyBreakdown": rows,
                "costComponents": costs,
                "rci": metrics.get("rci", 0),
                "rciLabel": metrics.get("rci_label", "Good"),
                "rciStars": metrics.get("rci_stars", "★★★★"),
                "rciClass": metrics.get("rci_class", "good"),
                "healthScore": metrics.get("health_score", 75),
                "healthLabel": metrics.get("health_label", "★★★★ Good"),
                "co2PerKm": metrics.get("co2_per_km", 0),
                "co2Annual": metrics.get("co2_annual", 0),
                "treesToOffset": metrics.get("trees_to_offset", 0),
                "fuelType": vehicle.get("fuel_type", "petrol"),
                "fuelEfficiency": vehicle.get("fuel_efficiency", 0),
                "basePrice": vehicle.get("base_price", 0),
                "vehicleName": f"{vehicle.get('make', '').capitalize()} {vehicle.get('model', '').replace('_', ' ').title()}",
                "yearsOwned": data.get("years_owned", 5),
                "annualMileage": data.get("annual_mileage", 20000),
                "recommendations": result.get("recommendations", [])
            }
        else:
            # Manual input result
            return {
                "totalCost": result.get("total_cost", 0),
                "costPerMonth": result.get("cost_per_month", 0),
                "costPerKm": result.get("cost_per_km", 0),
                "resaleValue": result.get("resale_value", 0),
                "totalDepreciation": result.get("purchase_price", 0) - result.get("resale_value", 0),
                "valueRetained": 0,
                "yearlyBreakdown": [],
                "costComponents": {
                    "purchase": result.get("purchase_price", 0),
                    "fuel": result.get("fuel_cost", 0),
                    "maintenance": result.get("maintenance_cost", 0),
                    "insurance": result.get("insurance_cost", 0),
                    "taxes": result.get("taxes", 0)
                },
                "rci": result.get("cost_per_km", 0),
                "rciLabel": "Good",
                "rciStars": "★★★★",
                "rciClass": "good",
                "healthScore": 75,
                "healthLabel": "★★★★ Good",
                "co2PerKm": 0,
                "co2Annual": 0,
                "treesToOffset": 0,
                "fuelType": "petrol",
                "fuelEfficiency": 0,
                "basePrice": result.get("purchase_price", 0),
                "vehicleName": "Custom Vehicle",
                "yearsOwned": result.get("years_owned", 5),
                "annualMileage": 20000,
                "recommendations": []
            }
    
    def _get_fuel_price(self, fuel_type: str) -> float:
        """Get fuel price by type"""
        prices = {
            "petrol": 214.03,
            "diesel": 222.86,
            "hybrid": 150.00,
            "electric": 30.00,
            "lpg": 120.00
        }
        return prices.get(fuel_type, 214.03)
    
    def _get_location_multipliers(self, locations: List[str]) -> tuple:
        """Get location multipliers for fuel, maintenance, tyres, insurance"""
        multipliers = {
            "nairobi": {"fuel": 0.9, "maintenance": 1.1, "tyres": 1.0, "insurance": 1.0},
            "mombasa": {"fuel": 1.1, "maintenance": 1.1, "tyres": 1.1, "insurance": 1.05},
            "rural": {"fuel": 1.15, "maintenance": 1.3, "tyres": 1.3, "insurance": 1.1},
            "highway": {"fuel": 0.95, "maintenance": 1.0, "tyres": 1.0, "insurance": 0.95}
        }
        
        fuel_mult = 1.0
        maint_mult = 1.0
        tyre_mult = 1.0
        ins_mult = 1.0
        
        for loc in locations:
            if loc in multipliers:
                m = multipliers[loc]
                fuel_mult *= m.get("fuel", 1.0)
                maint_mult *= m.get("maintenance", 1.0)
                tyre_mult *= m.get("tyres", 1.0)
                ins_mult *= m.get("insurance", 1.0)
        
        return fuel_mult, maint_mult, tyre_mult, ins_mult
    
    def _get_rci_rating(self, rci: float) -> tuple:
        """Get RCI rating labels"""
        if rci <= 20:
            return "Excellent", "★★★★★", "excellent"
        elif rci <= 35:
            return "Good", "★★★★", "good"
        elif rci <= 50:
            return "Average", "★★★", "average"
        elif rci <= 70:
            return "Expensive", "★★", "expensive"
        else:
            return "Very Expensive", "★", "very-expensive"
    
    def _calculate_health_score(self, age: int, fuel_efficiency: float, fuel_type: str, maintenance_per_km: float) -> float:
        """Calculate vehicle health score (0-100)"""
        score = 100
        score -= age * 3
        ideal = 20 if fuel_type == "electric" else (6 if fuel_type == "diesel" else 8)
        if fuel_efficiency < ideal * 0.7:
            score += 5
        elif fuel_efficiency > ideal * 1.3:
            score -= 5
        if maintenance_per_km > 4:
            score -= 8
        elif maintenance_per_km > 3:
            score -= 3
        if fuel_type == "electric":
            score += 5
        return max(0, min(100, score))
    
    def _get_health_label(self, score: float) -> str:
        """Get health label based on score"""
        if score >= 80:
            return "★★★★★ Excellent"
        elif score >= 60:
            return "★★★★ Good"
        elif score >= 40:
            return "★★★ Average"
        elif score >= 20:
            return "★★ Needs Attention"
        else:
            return "★ Critical"
    
    def _get_co2_factor(self, fuel_type: str) -> float:
        """Get CO2 emission factor by fuel type"""
        factors = {
            "petrol": 2.31,
            "diesel": 2.68,
            "hybrid": 1.80,
            "electric": 0.20,
            "lpg": 1.50
        }
        return factors.get(fuel_type, 2.31)
    
    def _generate_recommendations(self, **kwargs) -> List[Dict[str, str]]:
        """Generate AI-style recommendations"""
        recommendations = []
        cost_per_km = kwargs.get("cost_per_km", 0)
        rci = kwargs.get("rci", 0)
        health_score = kwargs.get("health_score", 0)
        age = kwargs.get("age", 0)
        fuel_type = kwargs.get("fuel_type", "petrol")
        financed = kwargs.get("financed", False)
        total_cost = kwargs.get("total_cost", 0)
        financing_total = kwargs.get("financing_total", 0)
        
        if cost_per_km > 30:
            recommendations.append({
                "icon": "💰",
                "text": f"Cost per km ({cost_per_km:.2f} KES/km) is high. Consider a more fuel-efficient vehicle.",
                "type": "warning",
                "tag": "Cost"
            })
        
        if rci > 50:
            recommendations.append({
                "icon": "📊",
                "text": f"RCI ({rci:.2f}) is in the 'Expensive' range. Review your vehicle choice.",
                "type": "warning",
                "tag": "RCI"
            })
        
        if health_score < 50:
            recommendations.append({
                "icon": "🏥",
                "text": f"Vehicle health score ({health_score:.0f}/100) is low. Consider a newer or better-maintained vehicle.",
                "type": "warning",
                "tag": "Health"
            })
        
        if age > 10:
            recommendations.append({
                "icon": "📅",
                "text": f"Vehicle is {age} years old. Maintenance costs will increase significantly.",
                "type": "warning",
                "tag": "Age"
            })
        
        if fuel_type == "electric":
            recommendations.append({
                "icon": "🌱",
                "text": "Great EV choice! Zero tailpipe emissions and lower running costs.",
                "type": "success",
                "tag": "Green"
            })
        elif fuel_type in ["petrol", "diesel"] and cost_per_km > 15:
            recommendations.append({
                "icon": "⚡",
                "text": "Consider switching to electric. You could save up to 60% on fuel costs.",
                "type": "info",
                "tag": "EV"
            })
        
        if financed and financing_total > total_cost * 0.15:
            recommendations.append({
                "icon": "🏦",
                "text": f"Financing represents {((financing_total / total_cost) * 100):.0f}% of total cost. Consider a larger down payment.",
                "type": "info",
                "tag": "Financing"
            })
        
        if not recommendations:
            recommendations.append({
                "icon": "✅",
                "text": "Vehicle performing well across all metrics. Good ownership value.",
                "type": "success",
                "tag": "All Good"
            })
        
        return recommendations
    
    def _get_fallback_vehicle(self, make: str, model: str) -> Optional[Dict[str, Any]]:
        """Get fallback vehicle data when vehicle_data module is not available"""
        # This is a minimal fallback - in production, use the actual vehicle database
        fallback_data = {
            "toyota": {
                "prado": {"price": 5200000, "fuel": 11, "serviceInterval": 10000, "minor": 18000, "major": 65000, "maintenancePerKm": 14},
                "hilux": {"price": 3800000, "fuel": 12, "serviceInterval": 10000, "minor": 15000, "major": 55000, "maintenancePerKm": 12},
                "corolla": {"price": 2000000, "fuel": 15, "serviceInterval": 15000, "minor": 10000, "major": 35000, "maintenancePerKm": 6}
            },
            "nissan": {
                "xtrail": {"price": 3200000, "fuel": 12, "serviceInterval": 15000, "minor": 12000, "major": 42000, "maintenancePerKm": 8}
            },
            "mercedes": {
                "c_class": {"price": 6000000, "fuel": 13, "serviceInterval": 15000, "minor": 22000, "major": 80000, "maintenancePerKm": 16}
            },
            "bmw": {
                "x3": {"price": 5500000, "fuel": 12, "serviceInterval": 15000, "minor": 20000, "major": 75000, "maintenancePerKm": 15}
            }
        }
        
        if make in fallback_data and model in fallback_data[make]:
            return fallback_data[make][model]
        return None


# ─── STANDALONE TEST ─────────────────────────────────────────────

if __name__ == "__main__":
    service = OwnershipService()
    
    print("=" * 60)
    print("🚗 Auto-D Kenya - Ownership Service")
    print("=" * 60)
    
    # Example calculation with vehicle database
    result = service.calculate({
        "make": "toyota",
        "model": "prado",
        "years_owned": 5,
        "annual_mileage": 20000,
        "financed": True,
        "down_pct": 30,
        "interest_rate": 16,
        "loan_term": 4,
        "driving_locations": ["nairobi"],
        "fuel_type": "diesel",
        "insurance_rate": 4.5,
        "year": 2020
    })
    
    if "success" in result and result["success"]:
        data = result.get("data", {})
        print("\n📊 Vehicle Ownership Result:")
        print(f"Vehicle: {data.get('vehicleName', 'Unknown')}")
        print(f"Total Cost: KES {data.get('totalCost', 0):,.2f}")
        print(f"Cost Per Month: KES {data.get('costPerMonth', 0):,.2f}")
        print(f"Cost Per Km: KES {data.get('costPerKm', 0):,.2f}")
        print(f"Resale Value: KES {data.get('resaleValue', 0):,.2f}")
        print(f"RCI: {data.get('rci', 0):.2f} ({data.get('rciLabel', 'N/A')})")
        print(f"Health Score: {data.get('healthScore', 0)}/100")
        print(f"CO₂ per km: {data.get('co2PerKm', 0):.2f} g/km")
        
        if data.get("yearlyBreakdown"):
            print("\n📅 Yearly Breakdown:")
            for row in data["yearlyBreakdown"]:
                print(f"  Year {row['year']}: KES {row['total']:,.2f}")
    else:
        print("Error:", result.get("error", "Unknown error"))
    
    print("\n" + "=" * 60)
