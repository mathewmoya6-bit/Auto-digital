def calculate_ownership_cost(
    purchase_price,
    years_owned,
    fuel_cost,
    maintenance_cost,
    insurance_cost,
    taxes,
    resale_value=0
):

    total_cost = (
        purchase_price
        + fuel_cost
        + maintenance_cost
        + insurance_cost
        + taxes
        - resale_value
    )

    yearly_cost = (
        total_cost / years_owned
        if years_owned
        else total_cost
    )

    return {
        "total_ownership_cost":
        round(total_cost, 2),

        "annual_cost":
        round(yearly_cost, 2)
    }
