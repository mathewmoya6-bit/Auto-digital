"""
Fuel and Energy Price Service
Auto-D Kenya - Professional Vehicle Intelligence Platform

Handles:
- Multiple fuel types (Petrol, Diesel, Electric, Hybrid, LPG, CNG, Hydrogen)
- Fuel price aliases and normalization
- Current prices with effective date tracking
- Unit conversions (L/100km, kWh/100km, kg/100km)
- Admin dashboard price updates (CRUD operations)

For MVP: Uses in-memory storage with persistence.
For production: Move this data to PostgreSQL/Supabase.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
import json
import os
import logging

logger = logging.getLogger(__name__)

# ─── PRICE STORAGE ──────────────────────────────────────────────────

# Default fuel prices (EPRA Kenya rates)
DEFAULT_FUEL_PRICES = {
    # Liquid Fuels
    "petrol": {
        "price": 189.00,
        "currency": "KES",
        "unit": "L",
        "unit_per_100km": "L/100km",
        "category": "liquid",
        "effective_date": "2026-07-14",
        "source": "EPRA Kenya",
        "co2_per_unit": 2.31
    },
    "diesel": {
        "price": 175.00,
        "currency": "KES",
        "unit": "L",
        "unit_per_100km": "L/100km",
        "category": "liquid",
        "effective_date": "2026-07-14",
        "source": "EPRA Kenya",
        "co2_per_unit": 2.68
    },
    "kerosene": {
        "price": 160.00,
        "currency": "KES",
        "unit": "L",
        "unit_per_100km": "L/100km",
        "category": "liquid",
        "effective_date": "2026-07-14",
        "source": "EPRA Kenya",
        "co2_per_unit": 2.45
    },
    
    # Gaseous Fuels
    "lpg": {
        "price": 120.00,
        "currency": "KES",
        "unit": "kg",
        "unit_per_100km": "kg/100km",
        "category": "gas",
        "effective_date": "2026-07-14",
        "source": "EPRA Kenya",
        "co2_per_unit": 1.50
    },
    "cng": {
        "price": 100.00,
        "currency": "KES",
        "unit": "kg",
        "unit_per_100km": "kg/100km",
        "category": "gas",
        "effective_date": "2026-07-14",
        "source": "EPRA Kenya",
        "co2_per_unit": 1.20
    },
    "hydrogen": {
        "price": 500.00,
        "currency": "KES",
        "unit": "kg",
        "unit_per_100km": "kg/100km",
        "category": "gas",
        "effective_date": "2026-07-14",
        "source": "Global Market",
        "co2_per_unit": 0.00
    },
    
    # Electric
    "electric": {
        "price": 30.00,
        "currency": "KES",
        "unit": "kWh",
        "unit_per_100km": "kWh/100km",
        "category": "electric",
        "effective_date": "2026-07-14",
        "source": "Kenya Power",
        "co2_per_unit": 0.00
    },
    
    # Hybrid
    "hybrid": {
        "price": 150.00,
        "currency": "KES",
        "unit": "L + kWh",
        "unit_per_100km": "L/100km + kWh/100km",
        "category": "hybrid",
        "effective_date": "2026-07-14",
        "source": "Combined",
        "co2_per_unit": 1.50
    },
    "phev": {
        "price": 140.00,
        "currency": "KES",
        "unit": "L + kWh",
        "unit_per_100km": "L/100km + kWh/100km",
        "category": "hybrid",
        "effective_date": "2026-07-14",
        "source": "Combined",
        "co2_per_unit": 1.20
    }
}

# ─── FUEL TYPE DEFINITIONS ────────────────────────────────────────

FUEL_TYPES = {
    # Liquid Fuels
    "petrol": {
        "aliases": ["gasoline", "super", "unleaded", "premium", "regular"],
        "unit": "L",
        "unit_per_100km": "L/100km",
        "category": "liquid",
        "co2_per_unit": 2.31
    },
    "diesel": {
        "aliases": ["automotive diesel", "gas oil", "agri-diesel"],
        "unit": "L",
        "unit_per_100km": "L/100km",
        "category": "liquid",
        "co2_per_unit": 2.68
    },
    "kerosene": {
        "aliases": ["paraffin", "illuminating oil"],
        "unit": "L",
        "unit_per_100km": "L/100km",
        "category": "liquid",
        "co2_per_unit": 2.45
    },
    
    # Gaseous Fuels
    "lpg": {
        "aliases": ["gas", "propane", "butane", "autogas"],
        "unit": "kg",
        "unit_per_100km": "kg/100km",
        "category": "gas",
        "co2_per_unit": 1.50
    },
    "cng": {
        "aliases": ["compressed natural gas", "natural gas"],
        "unit": "kg",
        "unit_per_100km": "kg/100km",
        "category": "gas",
        "co2_per_unit": 1.20
    },
    "hydrogen": {
        "aliases": ["h2", "fuel cell", "green hydrogen"],
        "unit": "kg",
        "unit_per_100km": "kg/100km",
        "category": "gas",
        "co2_per_unit": 0.00
    },
    
    # Electric
    "electric": {
        "aliases": ["ev", "battery electric", "bev", "electricity", "charge"],
        "unit": "kWh",
        "unit_per_100km": "kWh/100km",
        "category": "electric",
        "co2_per_unit": 0.00
    },
    
    # Hybrid
    "hybrid": {
        "aliases": ["hev", "plug-in hybrid", "phev", "hybrid electric"],
        "unit": "L + kWh",
        "unit_per_100km": "L/100km + kWh/100km",
        "category": "hybrid",
        "co2_per_unit": 1.50
    },
    "phev": {
        "aliases": ["plug-in hybrid electric", "plug-in hybrid"],
        "unit": "L + kWh",
        "unit_per_100km": "L/100km + kWh/100km",
        "category": "hybrid",
        "co2_per_unit": 1.20
    }
}

# ─── PRICE STORAGE CLASS ──────────────────────────────────────────

class FuelPriceStorage:
    """
    Manages fuel/energy price storage with persistence.
    Supports admin dashboard updates.
    """
    
    def __init__(self, storage_file: str = "fuel_prices.json"):
        self.storage_file = storage_file
        self.prices = {}
        self._load_prices()
    
    def _load_prices(self):
        """Load prices from storage file or use defaults"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    self.prices = json.load(f)
                logger.info(f"Loaded {len(self.prices)} fuel prices from {self.storage_file}")
            else:
                self.prices = self._get_default_prices()
                self._save_prices()
                logger.info(f"Created default fuel prices file: {self.storage_file}")
        except Exception as e:
            logger.error(f"Error loading fuel prices: {e}")
            self.prices = self._get_default_prices()
    
    def _save_prices(self):
        """Save prices to storage file"""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.prices, f, indent=2)
            logger.info(f"Saved {len(self.prices)} fuel prices to {self.storage_file}")
        except Exception as e:
            logger.error(f"Error saving fuel prices: {e}")
    
    def _get_default_prices(self) -> Dict[str, Any]:
        """Get default prices with full metadata"""
        prices = {}
        for fuel_type, fuel_data in FUEL_TYPES.items():
            default_data = DEFAULT_FUEL_PRICES.get(fuel_type, {})
            prices[fuel_type] = {
                "price": default_data.get("price", 0),
                "currency": default_data.get("currency", "KES"),
                "effective_date": default_data.get("effective_date", datetime.now().strftime("%Y-%m-%d")),
                "source": default_data.get("source", "Default"),
                "updated_at": datetime.now().isoformat(),
                "updated_by": "system"
            }
        return prices
    
    def get_price(self, fuel_type: str) -> Optional[Dict[str, Any]]:
        """Get price for a fuel type"""
        normalized = normalize_fuel_type(fuel_type)
        if not normalized:
            return None
        
        price_data = self.prices.get(normalized, {})
        fuel_data = FUEL_TYPES.get(normalized, {})
        
        return {
            "fuel_type": normalized,
            "price": price_data.get("price", 0),
            "currency": price_data.get("currency", "KES"),
            "unit": fuel_data.get("unit", ""),
            "unit_per_100km": fuel_data.get("unit_per_100km", ""),
            "category": fuel_data.get("category", ""),
            "effective_date": price_data.get("effective_date", ""),
            "source": price_data.get("source", ""),
            "co2_per_unit": fuel_data.get("co2_per_unit", 0),
            "updated_at": price_data.get("updated_at", ""),
            "updated_by": price_data.get("updated_by", "system")
        }
    
    def get_all_prices(self) -> Dict[str, Any]:
        """Get all fuel prices with metadata"""
        result = {}
        for fuel_type in FUEL_TYPES.keys():
            result[fuel_type] = self.get_price(fuel_type)
        return result
    
    def update_price(self, fuel_type: str, price: float, updated_by: str = "admin") -> Dict[str, Any]:
        """
        Update fuel price - called from admin dashboard
        
        Args:
            fuel_type: Type of fuel (petrol, diesel, etc.)
            price: New price value
            updated_by: User who made the update
        
        Returns:
            Updated price data
        """
        normalized = normalize_fuel_type(fuel_type)
        if not normalized:
            raise ValueError(f"Unknown fuel type: {fuel_type}")
        
        if price <= 0:
            raise ValueError(f"Price must be positive: {price}")
        
        # Update price
        self.prices[normalized] = {
            "price": float(price),
            "currency": DEFAULT_FUEL_PRICES.get(normalized, {}).get("currency", "KES"),
            "effective_date": datetime.now().strftime("%Y-%m-%d"),
            "source": DEFAULT_FUEL_PRICES.get(normalized, {}).get("source", "Updated"),
            "updated_at": datetime.now().isoformat(),
            "updated_by": updated_by
        }
        
        self._save_prices()
        logger.info(f"Updated {normalized} price to {price} by {updated_by}")
        
        return self.get_price(normalized)
    
    def bulk_update_prices(self, updates: Dict[str, float], updated_by: str = "admin") -> Dict[str, Any]:
        """
        Bulk update multiple fuel prices
        
        Args:
            updates: Dict of {fuel_type: new_price}
            updated_by: User who made the update
        
        Returns:
            Dict of updated prices
        """
        results = {}
        for fuel_type, price in updates.items():
            try:
                results[fuel_type] = self.update_price(fuel_type, price, updated_by)
            except Exception as e:
                results[fuel_type] = {"error": str(e)}
        
        return results
    
    def add_fuel_type(self, fuel_type: str, price_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new fuel type (admin function)
        
        Args:
            fuel_type: New fuel type key
            price_data: Price and metadata
        
        Returns:
            Created fuel data
        """
        if fuel_type in FUEL_TYPES:
            raise ValueError(f"Fuel type already exists: {fuel_type}")
        
        # Add to fuel types
        FUEL_TYPES[fuel_type] = {
            "aliases": price_data.get("aliases", []),
            "unit": price_data.get("unit", ""),
            "unit_per_100km": price_data.get("unit_per_100km", ""),
            "category": price_data.get("category", "other"),
            "co2_per_unit": price_data.get("co2_per_unit", 0)
        }
        
        # Add price
        self.prices[fuel_type] = {
            "price": float(price_data.get("price", 0)),
            "currency": price_data.get("currency", "KES"),
            "effective_date": datetime.now().strftime("%Y-%m-%d"),
            "source": price_data.get("source", "Custom"),
            "updated_at": datetime.now().isoformat(),
            "updated_by": price_data.get("updated_by", "admin")
        }
        
        self._save_prices()
        logger.info(f"Added new fuel type: {fuel_type}")
        
        return self.get_price(fuel_type)
    
    def get_price_history(self, fuel_type: str) -> List[Dict[str, Any]]:
        """
        Get price history for a fuel type
        (Implementation would require separate history table)
        """
        # For MVP, just return current price with history note
        current = self.get_price(fuel_type)
        if not current:
            return []
        
        return [
            {
                "price": current["price"],
                "effective_date": current["effective_date"],
                "updated_at": current.get("updated_at", ""),
                "updated_by": current.get("updated_by", "system"),
                "note": "Current price"
            }
        ]


# ─── SINGLETON INSTANCE ────────────────────────────────────────────

_price_storage = None

def get_price_storage() -> FuelPriceStorage:
    """Get the singleton price storage instance"""
    global _price_storage
    if _price_storage is None:
        _price_storage = FuelPriceStorage()
    return _price_storage


# ─── FUEL ALIAS MAPPING ──────────────────────────────────────────

def normalize_fuel_type(fuel_input: str) -> Optional[str]:
    """
    Normalize fuel type input to standard key.
    
    Example:
        normalize_fuel_type("Gasoline") -> "petrol"
        normalize_fuel_type("EV") -> "electric"
        normalize_fuel_type("LPG") -> "lpg"
    """
    if not fuel_input:
        return None
    
    fuel_input = fuel_input.lower().strip()
    
    # Direct match
    if fuel_input in FUEL_TYPES:
        return fuel_input
    
    # Check aliases
    for fuel_key, fuel_data in FUEL_TYPES.items():
        if fuel_input in fuel_data.get("aliases", []):
            return fuel_key
        if fuel_input == fuel_key:
            return fuel_key
    
    return None


# ─── FUEL PRICE FUNCTIONS ──────────────────────────────────────────

def get_fuel_price(fuel_type: str) -> Optional[Dict[str, Any]]:
    """
    Get current fuel/energy price.
    
    Args:
        fuel_type: Any fuel type or alias (petrol, diesel, electric, etc.)
    
    Returns:
        Dict with price data or None if not found
    """
    storage = get_price_storage()
    return storage.get_price(fuel_type)


def get_all_fuel_prices() -> Dict[str, Any]:
    """Return all current fuel/energy prices."""
    storage = get_price_storage()
    return storage.get_all_prices()


def update_fuel_price(fuel_type: str, price: float, updated_by: str = "admin") -> Dict[str, Any]:
    """
    Update fuel/energy price manually.
    
    Args:
        fuel_type: Type of fuel
        price: New price
        updated_by: User who made the update
    
    Returns:
        Updated price data
    """
    storage = get_price_storage()
    return storage.update_price(fuel_type, price, updated_by)


def bulk_update_fuel_prices(updates: Dict[str, float], updated_by: str = "admin") -> Dict[str, Any]:
    """
    Bulk update multiple fuel prices.
    
    Args:
        updates: Dict of {fuel_type: new_price}
        updated_by: User who made the update
    
    Returns:
        Dict of updated prices
    """
    storage = get_price_storage()
    return storage.bulk_update_prices(updates, updated_by)


def calculate_energy_cost(
    fuel_type: str,
    distance_km: float,
    consumption: float,
    consumption_unit: str = "per_100km"
) -> Optional[Dict[str, Any]]:
    """
    Calculate energy/fuel cost for a given distance.
    
    Args:
        fuel_type: Type of fuel/energy
        distance_km: Distance in kilometers
        consumption: Consumption value (L/100km, kWh/100km, kg/100km)
        consumption_unit: Unit type ('per_100km' or 'per_km')
    
    Returns:
        Dict with cost breakdown
    """
    fuel_data = get_fuel_price(fuel_type)
    if not fuel_data:
        return None
    
    # Convert to per km if needed
    if consumption_unit == "per_100km":
        consumption_per_km = consumption / 100
    else:
        consumption_per_km = consumption
    
    # Calculate energy used
    energy_used = distance_km * consumption_per_km
    
    # Calculate cost
    cost = energy_used * fuel_data["price"]
    
    return {
        "fuel_type": fuel_data["fuel_type"],
        "fuel_price": fuel_data["price"],
        "currency": fuel_data["currency"],
        "unit": fuel_data["unit"],
        "unit_per_100km": fuel_data["unit_per_100km"],
        "effective_date": fuel_data["effective_date"],
        "source": fuel_data["source"],
        "category": fuel_data["category"],
        "co2_per_unit": fuel_data["co2_per_unit"],
        "distance_km": distance_km,
        "consumption": consumption,
        "consumption_unit": consumption_unit,
        "energy_used": round(energy_used, 2),
        "energy_cost": round(cost, 2),
        "cost_per_km": round(cost / distance_km if distance_km > 0 else 0, 2)
    }


def calculate_fuel_cost(fuel_type: str, litres: float) -> Optional[float]:
    """
    Simple fuel cost calculation (backward compatibility).
    
    Args:
        fuel_type: Type of fuel
        litres: Litres used
    
    Returns:
        Total cost or None
    """
    fuel_data = get_fuel_price(fuel_type)
    if not fuel_data:
        return None
    
    return round(fuel_data["price"] * litres, 2)


# ─── RUNNING COST ENGINE ──────────────────────────────────────────

class RunningCostEngine:
    """
    Professional Running Cost Engine for vehicle cost calculation.
    """
    
    def __init__(self):
        self.fuel_service = self
    
    def calculate_trip_cost(
        self,
        distance_km: float,
        vehicle_data: Dict[str, Any],
        include_fixed_costs: bool = False,
        include_operating_costs: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate complete trip cost breakdown.
        
        Args:
            distance_km: Distance in kilometers
            vehicle_data: Vehicle specifications
            include_fixed_costs: Include fixed costs in calculation
            include_operating_costs: Include operating costs
        
        Returns:
            Complete cost breakdown
        """
        # Get fuel/energy data
        fuel_type = vehicle_data.get("fuel_type", "petrol")
        consumption = vehicle_data.get("fuel_consumption", 8)
        
        # Calculate energy cost
        energy_result = calculate_energy_cost(
            fuel_type=fuel_type,
            distance_km=distance_km,
            consumption=consumption
        )
        
        if not energy_result:
            return {"error": f"Fuel type not available: {fuel_type}"}
        
        # Operating costs
        operating_costs = {}
        operating_cost_total = 0
        
        if include_operating_costs:
            # Maintenance
            maintenance_per_km = vehicle_data.get("maintenance_per_km", 0)
            maintenance_cost = distance_km * maintenance_per_km
            operating_costs["maintenance"] = round(maintenance_cost, 2)
            operating_cost_total += maintenance_cost
            
            # Tyres
            tyre_cost_per_km = vehicle_data.get("tyre_cost_per_km", 0)
            tyre_cost = distance_km * tyre_cost_per_km
            operating_costs["tyres"] = round(tyre_cost, 2)
            operating_cost_total += tyre_cost
            
            # Repairs
            repair_per_km = vehicle_data.get("repair_per_km", 0)
            repair_cost = distance_km * repair_per_km
            operating_costs["repairs"] = round(repair_cost, 2)
            operating_cost_total += repair_cost
            
            # Other operating costs
            other_per_km = vehicle_data.get("other_operating_per_km", 0)
            other_cost = distance_km * other_per_km
            operating_costs["other"] = round(other_cost, 2)
            operating_cost_total += other_cost
        
        # Fixed costs
        fixed_costs = {}
        fixed_cost_total = 0
        
        if include_fixed_costs:
            # Insurance
            insurance_annual = vehicle_data.get("insurance_annual", 0)
            annual_km = vehicle_data.get("annual_km", 20000)
            insurance_per_km = insurance_annual / annual_km if annual_km > 0 else 0
            insurance_cost = distance_km * insurance_per_km
            fixed_costs["insurance"] = round(insurance_cost, 2)
            fixed_cost_total += insurance_cost
            
            # Depreciation
            purchase_price = vehicle_data.get("purchase_price", 0)
            years_owned = vehicle_data.get("years_owned", 5)
            depreciation_annual = purchase_price / years_owned if years_owned > 0 else 0
            depreciation_per_km = depreciation_annual / annual_km if annual_km > 0 else 0
            depreciation_cost = distance_km * depreciation_per_km
            fixed_costs["depreciation"] = round(depreciation_cost, 2)
            fixed_cost_total += depreciation_cost
            
            # Licensing
            licensing_annual = vehicle_data.get("licensing_annual", 5000)
            licensing_per_km = licensing_annual / annual_km if annual_km > 0 else 0
            licensing_cost = distance_km * licensing_per_km
            fixed_costs["licensing"] = round(licensing_cost, 2)
            fixed_cost_total += licensing_cost
            
            # Interest
            if vehicle_data.get("financed", False):
                interest_annual = vehicle_data.get("interest_annual", 0)
                interest_per_km = interest_annual / annual_km if annual_km > 0 else 0
                interest_cost = distance_km * interest_per_km
                fixed_costs["interest"] = round(interest_cost, 2)
                fixed_cost_total += interest_cost
        
        energy_cost = energy_result["energy_cost"]
        energy_per_km = energy_result["cost_per_km"]
        
        total_cost = energy_cost + operating_cost_total + fixed_cost_total
        total_per_km = total_cost / distance_km if distance_km > 0 else 0
        
        return {
            "summary": {
                "total_cost": round(total_cost, 2),
                "total_per_km": round(total_per_km, 2),
                "distance_km": distance_km,
                "energy_cost": energy_cost,
                "energy_per_km": energy_per_km,
                "operating_cost_total": round(operating_cost_total, 2),
                "fixed_cost_total": round(fixed_cost_total, 2)
            },
            "energy": energy_result,
            "operating_costs": operating_costs,
            "fixed_costs": fixed_costs,
            "vehicle": {
                "fuel_type": fuel_type,
                "consumption": consumption,
                "consumption_unit": energy_result.get("unit_per_100km", "L/100km")
            }
        }


# ─── EXAMPLE USAGE ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("🔋 Auto-D Kenya Fuel/Energy Service")
    print("=" * 60)
    
    # Example 1: Get all prices
    print("\n📊 Current Fuel Prices:")
    for fuel_type, data in get_all_fuel_prices().items():
        if data:
            print(f"  {fuel_type.capitalize()}: {data['currency']} {data['price']:.2f} per {data['unit']}")
    
    # Example 2: Update a price (admin function)
    print("\n🔄 Admin: Updating petrol price...")
    try:
        update_fuel_price("petrol", 195.50, "admin@autod.ke")
        print("  ✅ Petrol price updated to KES 195.50")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Example 3: Calculate energy cost
    print("\n🚗 Example: Toyota Prado on Petrol")
    result = calculate_energy_cost(
        fuel_type="petrol",
        distance_km=100,
        consumption=8
    )
    if result:
        print(f"  Distance: {result['distance_km']} km")
        print(f"  Fuel Used: {result['energy_used']} {result['unit']}")
        print(f"  Fuel Cost: {result['currency']} {result['energy_cost']:.2f}")
        print(f"  Cost per km: {result['currency']} {result['cost_per_km']:.2f}")
    
    # Example 4: Running Cost Engine
    print("\n🏎️ Professional Running Cost Engine")
    engine = RunningCostEngine()
    
    vehicle = {
        "fuel_type": "petrol",
        "fuel_consumption": 8,
        "maintenance_per_km": 2.5,
        "tyre_cost_per_km": 1.2,
        "repair_per_km": 1.0,
        "insurance_annual": 50000,
        "purchase_price": 5200000,
        "years_owned": 5,
        "annual_km": 20000
    }
    
    trip_result = engine.calculate_trip_cost(
        distance_km=100,
        vehicle_data=vehicle,
        include_fixed_costs=True,
        include_operating_costs=True
    )
    
    if "error" not in trip_result:
        print(f"  Total Trip Cost: KES {trip_result['summary']['total_cost']:.2f}")
        print(f"  Cost per km: KES {trip_result['summary']['total_per_km']:.2f}")
        print(f"  Energy: KES {trip_result['summary']['energy_cost']:.2f}")
        print(f"  Operating: KES {trip_result['summary']['operating_cost_total']:.2f}")
        print(f"  Fixed: KES {trip_result['summary']['fixed_cost_total']:.2f}")
    
    print("\n" + "=" * 60)
