"""
Mileage and running cost calculations
Auto-D Kenya
"""

from services.fuel_service import get_fuel_price



def calculate_mileage_cost(
    distance_km,
    fuel_type,
    fuel_consumption,
    maintenance_per_km=0,
    insurance=0,
    tax=0
):
    """
    Calculate vehicle mileage and running cost.

    distance_km:
        Distance travelled

    fuel_type:
        petrol / diesel / kerosene

    fuel_consumption:
        Litres per 100km

    maintenance_per_km:
        Maintenance cost per kilometre

    insurance:
        Insurance cost for period

    tax:
        Tax/licensing cost for period
    """


    # Get current fuel price automatically
    fuel = get_fuel_price(
        fuel_type
    )


    if not fuel:
        return {
            "error":
            "Fuel type not available"
        }



    fuel_price = fuel["price"]



    fuel_used = (
        distance_km / 100
    ) * fuel_consumption



    fuel_cost = (
        fuel_used * fuel_price
    )



    maintenance_cost = (
        distance_km *
        maintenance_per_km
    )



    total_cost = (
        fuel_cost
        + maintenance_cost
        + insurance
        + tax
    )



    cost_per_km = (

        total_cost / distance_km

        if distance_km > 0

        else 0

    )



    return {

        "fuel_type":
        fuel_type,

        "fuel_price":
        fuel_price,

        "fuel_price_date":
        fuel["effective_date"],

        "fuel_used_litres":
        round(fuel_used, 2),

        "fuel_cost":
        round(fuel_cost, 2),

        "maintenance_cost":
        round(maintenance_cost, 2),

        "total_cost":
        round(total_cost, 2),

        "cost_per_km":
        round(cost_per_km, 2)

    }
