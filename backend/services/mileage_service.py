def calculate_mileage_cost(
    distance_km,
    fuel_price,
    fuel_consumption,
    maintenance_per_km=0,
    insurance=0,
    tax=0
):
    fuel_used = (
        distance_km / 100
    ) * fuel_consumption

    fuel_cost = (
        fuel_used * fuel_price
    )

    maintenance_cost = (
        distance_km * maintenance_per_km
    )

    total_cost = (
        fuel_cost
        + maintenance_cost
        + insurance
        + tax
    )

    cost_per_km = (
        total_cost / distance_km
        if distance_km
        else 0
    )

    return {
        "fuel_cost": round(fuel_cost, 2),
        "maintenance_cost": round(maintenance_cost, 2),
        "total_cost": round(total_cost, 2),
        "cost_per_km": round(cost_per_km, 2)
    }
