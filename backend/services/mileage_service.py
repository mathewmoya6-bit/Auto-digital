from data import find_variant

class MileageError(ValueError):
    pass

def calculate_mileage(variant_id: str, distance_km: float) -> dict:
    if not variant_id:
        raise MileageError("variant_id is required")
    try:
        distance_km = float(distance_km)
    except (TypeError, ValueError):
        raise MileageError("distance_km must be a number")
    if distance_km <= 0:
        raise MileageError("distance_km must be greater than 0")

    variant = find_variant(variant_id)
    if not variant:
        raise MileageError(f"Unknown variant_id: {variant_id}")

    fixed_rate = float(variant["fixed_per_km"])
    operating_rate = float(variant["operating_per_km"])
    total_rate = float(variant.get("total_per_km") or (fixed_rate + operating_rate))

    components = {k: round(float(v) * distance_km, 2) for k, v in variant.get("components", {}).items()}
    yearly = {f"year{i}": variant.get(f"year{i}", total_rate) for i in range(1, 6)}

    return {
        "variant_id": variant["id"], "label": variant["label"], "fuel_type": variant.get("fuel_type"),
        "distance_km": distance_km,
        "totalCost": round(total_rate * distance_km, 2),
        "fixedCost": round(fixed_rate * distance_km, 2),
        "operatingCost": round(operating_rate * distance_km, 2),
        "totalRate": round(total_rate, 2), "fixedRate": round(fixed_rate, 2), "operatingRate": round(operating_rate, 2),
        "components": components, "yearly": yearly, "initialCost": variant.get("initial_cost", 0),
    }
