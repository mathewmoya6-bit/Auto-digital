def calculate_vehicle_value(
    purchase_price,
    age_years,
    depreciation_rate=0.15
):

    current_value = (
        purchase_price *
        ((1 - depreciation_rate) ** age_years)
    )

    return {
        "estimated_value":
        round(current_value, 2)
    }
