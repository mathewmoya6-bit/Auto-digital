"""
Fuel Service - Auto-D Kenya
Handles fuel price data and calculations
"""

from typing import Dict, Any, Optional
from datetime import datetime

# ─── Fuel Prices Data ──────────────────────────────────────────────
FUEL_PRICES = {
    "petrol": {"price": 182.00, "currency": "KES", "effective_date": "2026-07-14", "source": "EPRA Kenya"},
    "diesel": {"price": 170.00, "currency": "KES", "effective_date": "2026-07-14", "source": "EPRA Kenya"},
    "electric": {"price": 30.00, "currency": "KES", "effective_date": "2026-07-14", "source": "Kenya Power"},
    "lpg": {"price": 120.00, "currency": "KES", "effective_date": "2026-07-14", "source": "EPRA Kenya"},
    "hybrid": {"price": 150.00, "currency": "KES", "effective_date": "2026-07-14", "source": "Combined"},
    "cng": {"price": 100.00, "currency": "KES", "effective_date": "2026-07-14", "source": "EPRA Kenya"},
    "hydrogen": {"price": 500.00, "currency": "KES", "effective_date": "2026-07-14", "source": "Global Market"}
}

def normalize_fuel_type(fuel_input: str) -> Optional[str]:
    """Normalize fuel type input"""
    fuel_input = fuel_input.lower().strip()
    
    # Direct match
    if fuel_input in FUEL_PRICES:
        return fuel_input
    
    # Aliases
    aliases = {
        "gasoline": "petrol",
        "super": "petrol",
        "unleaded": "petrol",
        "premium": "petrol",
        "regular": "petrol",
        "ev": "electric",
        "battery": "electric",
        "bev": "electric",
        "electricity": "electric",
        "charge": "electric",
        "gas": "lpg",
        "propane": "lpg",
        "butane": "lpg",
        "autogas": "lpg",
        "hev": "hybrid",
        "phev": "hybrid",
        "plug-in": "hybrid",
        "cng": "cng",
        "h2": "hydrogen"
    }
    
    return aliases.get(fuel_input)

def get_fuel_price(fuel_type: str) -> Optional[Dict[str, Any]]:
    """Get current fuel price"""
    normalized = normalize_fuel_type(fuel_type)
    if not normalized:
        return None
    
    fuel_data = FUEL_PRICES.get(normalized)
    if not fuel_data:
        return None
    
    return {
        "fuel_type": normalized,
        "price": fuel_data["price"],
        "currency": fuel_data["currency"],
        "effective_date": fuel_data["effective_date"],
        "source": fuel_data["source"]
    }

def get_all_fuel_prices() -> Dict[str, Any]:
    """Return all fuel prices"""
    return FUEL_PRICES

def calculate_energy_cost(fuel_type: str, distance_km: float, consumption: float) -> Optional[Dict[str, Any]]:
    """Calculate energy cost for a trip"""
    fuel_data = get_fuel_price(fuel_type)
    if not fuel_data:
        return None
    
    consumption_per_km = consumption / 100
    energy_used = distance_km * consumption_per_km
    cost = energy_used * fuel_data["price"]
    
    return {
        "fuel_type": fuel_data["fuel_type"],
        "fuel_price": fuel_data["price"],
        "currency": fuel_data["currency"],
        "unit_per_100km": "L/100km",
        "effective_date": fuel_data["effective_date"],
        "source": fuel_data["source"],
        "distance_km": distance_km,
        "consumption": consumption,
        "energy_used": round(energy_used, 2),
        "energy_cost": round(cost, 2),
        "cost_per_km": round(cost / distance_km if distance_km > 0 else 0, 2)
    }

def update_fuel_price(fuel_type: str, price: float) -> Dict[str, Any]:
    """Update fuel price"""
    normalized = normalize_fuel_type(fuel_type)
    if not normalized:
        raise ValueError(f"Unknown fuel type: {fuel_type}")
    
    FUEL_PRICES[normalized]["price"] = float(price)
    FUEL_PRICES[normalized]["effective_date"] = datetime.now().strftime("%Y-%m-%d")
    
    return FUEL_PRICES[normalized]
