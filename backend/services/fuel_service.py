"""
Fuel price service
Auto-D Kenya

Handles:
- Current petrol/diesel prices
- Fuel price updates
- Effective date tracking

For MVP:
    Uses in-memory storage.

For production:
    Move this data to PostgreSQL/Supabase.
"""

from datetime import datetime


# Current fuel prices
# Update on the 14th after new EPRA prices are released

fuel_prices = {

    "petrol": {
        "price": 189.00,
        "currency": "KES",
        "effective_date": "2026-07-14"
    },

    "diesel": {
        "price": 175.00,
        "currency": "KES",
        "effective_date": "2026-07-14"
    },

    "kerosene": {
        "price": 160.00,
        "currency": "KES",
        "effective_date": "2026-07-14"
    }

}



def get_fuel_price(
    fuel_type="petrol"
):
    """
    Get current fuel price.
    """

    fuel = fuel_prices.get(
        fuel_type.lower()
    )


    if not fuel:
        return None


    return fuel



def get_all_fuel_prices():
    """
    Return all current fuel prices.
    """

    return fuel_prices



def update_fuel_price(
    fuel_type,
    price
):
    """
    Update fuel price manually.

    Example:
        update_fuel_price("petrol", 190.50)
    """

    fuel_type = fuel_type.lower()


    fuel_prices[fuel_type] = {

        "price": float(price),

        "currency": "KES",

        "effective_date":
        datetime.now().strftime(
            "%Y-%m-%d"
        )

    }


    return fuel_prices[fuel_type]



def calculate_fuel_cost(
    fuel_type,
    litres
):
    """
    Calculate fuel cost.
    """

    fuel = get_fuel_price(
        fuel_type
    )


    if not fuel:
        return None


    return round(
        fuel["price"] * litres,
        2
    )
