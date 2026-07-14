"""
Ownership Service - Auto-D Kenya
Service for calculating total cost of vehicle ownership
Serves: ownership-cost.html
Endpoint: /api/service/ownership
"""

from typing import Dict, Any
import logging

# Import the ownership engine
from engines.ownership_engine import OwnershipEngine, calculate_ownership_cost

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
    """
    
    def __init__(self):
        """Initialize the Ownership Service"""
        self.engine = OwnershipEngine()
        self.logger = logging.getLogger(__name__)
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate ownership cost from request data.
        
        Args:
            data: Request data containing ownership parameters
            
        Returns:
            Dict with ownership cost results
        
        Expected input format (manual):
        {
            "purchase_price": 5000000,
            "years_owned": 5,
            "fuel_cost": 360000,
            "maintenance_cost": 120000,
            "insurance_cost": 150000,
            "taxes": 50000,
            "resale_value": 2000000
        }
        
        OR (vehicle database):
        {
            "make": "toyota",
            "model": "prado",
            "years_owned": 5,
            "annual_mileage": 20000,
            "financed": true,
            "down_pct": 30,
            "interest_rate": 16,
            "loan_term": 4,
            "driving_locations": ["nairobi"]
        }
        """
        try:
            # Check if using vehicle database or manual input
            make = data.get("make")
            model = data.get("model")
            
            if make and model:
                # Use vehicle database - will be handled by ownership engine
                result = self._calculate_from_vehicle(data)
            else:
                # Manual input
                result = self._calculate_manual(data)
            
            if "error" in result:
                return result
            
            return {
                "success": True,
                "data": result,
                "service": "ownership",
                "timestamp": "2026-07-14T19:00:00Z"
            }
            
        except Exception as e:
            self.logger.error(f"Ownership calculation error: {str(e)}")
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
            resale_value = float(data.get("resale_value", 0))
            
            if purchase_price < 0 or years_owned < 0:
                raise ValueError
        except ValueError:
            return {"error": "All numeric fields must be valid positive numbers"}
        
        return calculate_ownership_cost(
            purchase_price=purchase_price,
            years_owned=years_owned,
            fuel_cost=fuel_cost,
            maintenance_cost=maintenance_cost,
            insurance_cost=insurance_cost,
            taxes=taxes,
            resale_value=resale_value
        )
    
    def _calculate_from_vehicle(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate ownership cost using vehicle database"""
        make = data.get("make")
        model = data.get("model")
        years_owned = data.get("years_owned", 5)
        annual_mileage = data.get("annual_mileage", 20000)
        
        # Try to get vehicle data from engine
        try:
            from engines.ownership_engine import calculate_ownership_from_vehicle
            result = calculate_ownership_from_vehicle(
                make=make,
                model=model,
                years_owned=years_owned,
                annual_mileage=annual_mileage,
                financed=data.get("financed", False),
                down_pct=data.get("down_pct", 30),
                interest_rate=data.get("interest_rate", 16),
                loan_term=data.get("loan_term", 4),
                driving_locations=data.get("driving_locations", [])
            )
            return result
        except ImportError:
            # Fallback to manual calculation with vehicle price
            from vehicle_data import get_vehicle_data
            vehicle = get_vehicle_data(make, model)
            if not vehicle:
                return {"error": f"Vehicle '{make} {model}' not found"}
            
            base_price = vehicle.get("price", 0)
            fuel_efficiency = vehicle.get("fuel_efficiency", 10)
            maintenance_per_km = vehicle.get("maintenance_per_km", 10)
            
            fuel_cost = annual_mileage * 182 / fuel_efficiency
            maintenance_cost = annual_mileage * maintenance_per_km * years_owned
            insurance_cost = base_price * 0.045 * years_owned
            taxes = 5000 * years_owned
            resale_value = base_price * 0.3
            
            return calculate_ownership_cost(
                purchase_price=base_price,
                years_owned=years_owned,
                fuel_cost=fuel_cost,
                maintenance_cost=maintenance_cost,
                insurance_cost=insurance_cost,
                taxes=taxes,
                resale_value=resale_value
            )


# ─── API COMPATIBILITY FUNCTIONS ──────────────────────────────

def calculate_ownership_cost(
    purchase_price: float,
    years_owned: float,
    fuel_cost: float,
    maintenance_cost: float,
    insurance_cost: float,
    taxes: float,
    resale_value: float = 0
) -> Dict[str, Any]:
    """
    Simplified ownership cost calculation (API compatibility).
    Matches Flask backend signature.
    """
    try:
        purchase_price = float(purchase_price)
        years_owned = float(years_owned)
        fuel_cost = float(fuel_cost)
        maintenance_cost = float(maintenance_cost)
        insurance_cost = float(insurance_cost)
        taxes = float(taxes)
        resale_value = float(resale_value)
    except (ValueError, TypeError):
        return {"error": "Invalid input values"}
    
    if purchase_price < 0 or years_owned < 0:
        return {"error": "Invalid input values"}
    
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
        "cost_per_day": round(annual_cost / 365, 2) if years_owned > 0 else 0
    }


def calculate_ownership_from_vehicle(
    make: str,
    model: str,
    years_owned: int,
    annual_mileage: int,
    financed: bool = False,
    down_pct: float = 30,
    interest_rate: float = 16,
    loan_term: int = 4,
    driving_locations: list = None
) -> Dict[str, Any]:
    """
    Calculate ownership cost using vehicle database.
    """
    from vehicle_data import get_vehicle_data
    
    vehicle = get_vehicle_data(make, model)
    if not vehicle:
        return {"error": f"Vehicle '{make} {model}' not found"}
    
    base_price = vehicle.get("price", 0)
    fuel_efficiency = vehicle.get("fuel_efficiency", 10)
    maintenance_per_km = vehicle.get("maintenance_per_km", 10)
    
    # Calculate costs
    fuel_cost = annual_mileage * 182 / fuel_efficiency * years_owned
    maintenance_cost = annual_mileage * maintenance_per_km * years_owned
    insurance_cost = base_price * 0.045 * years_owned
    taxes = 5000 * years_owned
    resale_value = base_price * 0.3
    
    # Financing
    financing_annual = 0
    if financed:
        down_pct = float(down_pct) / 100
        interest_rate = float(interest_rate) / 100
        loan_term = int(loan_term)
        loan_balance = base_price * (1 - down_pct)
        if loan_term > 0 and interest_rate > 0:
            monthly_rate = interest_rate / 12
            num_payments = loan_term * 12
            monthly_payment = loan_balance * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
            financing_annual = monthly_payment * 12 * years_owned
    
    total_cost = base_price + fuel_cost + maintenance_cost + insurance_cost + taxes + financing_annual - resale_value
    
    return {
        "vehicle": {
            "make": make,
            "model": model,
            "base_price": base_price,
            "fuel_efficiency": fuel_efficiency
        },
        "summary": {
            "total_cost": round(total_cost, 2),
            "cost_per_month": round(total_cost / (years_owned * 12), 2),
            "cost_per_km": round(total_cost / (annual_mileage * years_owned), 2),
            "resale_value": round(resale_value, 2),
            "total_depreciation": round(base_price - resale_value, 2)
        },
        "costs": {
            "purchase": round(base_price, 2),
            "fuel": round(fuel_cost, 2),
            "maintenance": round(maintenance_cost, 2),
            "insurance": round(insurance_cost, 2),
            "taxes": round(taxes, 2),
            "financing": round(financing_annual, 2)
        }
    }


# ─── EXAMPLE USAGE ─────────────────────────────────────────────

if __name__ == "__main__":
    service = OwnershipService()
    
    print("=" * 60)
    print("🚗 Auto-D Kenya - Ownership Service")
    print("=" * 60)
    
    # Example manual calculation
    result = service.calculate({
        "purchase_price": 5000000,
        "years_owned": 5,
        "fuel_cost": 360000,
        "maintenance_cost": 120000,
        "insurance_cost": 150000,
        "taxes": 50000,
        "resale_value": 2000000
    })
    
    print("\n📊 Manual Input Result:")
    if "success" in result:
        data = result.get("data", {})
        print(f"Total Cost: KES {data.get('total_cost', 0):,.2f}")
        print(f"Annual Cost: KES {data.get('annual_cost', 0):,.2f}")
        print(f"Cost per km: KES {data.get('cost_per_km', 0):,.2f}")
    
    print("\n" + "=" * 60)
