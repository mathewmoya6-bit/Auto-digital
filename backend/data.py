CATEGORIES = [
    {"id": "cat1", "name": "Saloon Cars - Petrol", "fuel_type": "Petrol"},
    {"id": "cat2", "name": "Saloon Cars - Diesel", "fuel_type": "Diesel"},
    {"id": "cat3", "name": "SUVs & Crossovers", "fuel_type": "Diesel"},
    {"id": "cat4", "name": "Pickups & Vans", "fuel_type": "Diesel"},
    {"id": "cat5", "name": "Electric Vehicles", "fuel_type": "Electric"},
    {"id": "cat6", "name": "Motorcycles", "fuel_type": "Petrol"},
]

VARIANTS = {
    "cat1": [
        {"id": "v1", "category_id": "cat1", "label": "1.5L Petrol - Standard",
         "fuel_type": "Petrol", "fixed_per_km": 12.50, "operating_per_km": 18.75,
         "total_per_km": 31.25, "initial_cost": 1500000,
         "components": {"Insurance": 2.50, "Depreciation": 5.00, "Interest": 5.00, "Fuel": 8.75,
                         "Servicing": 4.00, "Repairs": 3.00, "Tyres": 2.00, "Licences": 1.00},
         "year1": 28.50, "year2": 32.00, "year3": 36.00, "year4": 41.00, "year5": 47.00},
        {"id": "v2", "category_id": "cat1", "label": "1.8L Petrol - Premium",
         "fuel_type": "Petrol", "fixed_per_km": 15.00, "operating_per_km": 22.50,
         "total_per_km": 37.50, "initial_cost": 2000000,
         "components": {"Insurance": 3.00, "Depreciation": 6.00, "Interest": 6.00, "Fuel": 10.50,
                         "Servicing": 5.00, "Repairs": 3.50, "Tyres": 2.50, "Licences": 1.00},
         "year1": 34.00, "year2": 38.00, "year3": 43.00, "year4": 49.00, "year5": 56.00},
    ],
    "cat2": [
        {"id": "v3", "category_id": "cat2", "label": "1.6L Diesel - Standard",
         "fuel_type": "Diesel", "fixed_per_km": 14.00, "operating_per_km": 16.50,
         "total_per_km": 30.50, "initial_cost": 1800000,
         "components": {"Insurance": 2.80, "Depreciation": 5.50, "Interest": 5.70, "Fuel": 7.50,
                         "Servicing": 4.50, "Repairs": 2.50, "Tyres": 2.00, "Licences": 1.00},
         "year1": 27.50, "year2": 30.50, "year3": 34.50, "year4": 39.50, "year5": 45.50},
    ],
    "cat3": [
        {"id": "v4", "category_id": "cat3", "label": "2.0L Diesel - 4x4",
         "fuel_type": "Diesel", "fixed_per_km": 18.00, "operating_per_km": 20.00,
         "total_per_km": 38.00, "initial_cost": 3500000,
         "components": {"Insurance": 4.00, "Depreciation": 8.00, "Interest": 6.00, "Fuel": 10.00,
                         "Servicing": 6.00, "Repairs": 4.00, "Tyres": 3.00, "Licences": 1.50},
         "year1": 34.00, "year2": 38.50, "year3": 44.00, "year4": 50.50, "year5": 58.00},
    ],
    "cat4": [
        {"id": "v5", "category_id": "cat4", "label": "3.0L Diesel - 4x4",
         "fuel_type": "Diesel", "fixed_per_km": 20.00, "operating_per_km": 22.00,
         "total_per_km": 42.00, "initial_cost": 4500000,
         "components": {"Insurance": 4.50, "Depreciation": 9.00, "Interest": 6.50, "Fuel": 12.00,
                         "Servicing": 7.00, "Repairs": 4.50, "Tyres": 3.50, "Licences": 1.50},
         "year1": 38.00, "year2": 42.00, "year3": 48.00, "year4": 55.00, "year5": 63.00},
    ],
    "cat5": [
        {"id": "v6", "category_id": "cat5", "label": "EV Standard Range",
         "fuel_type": "Electric", "fixed_per_km": 10.00, "operating_per_km": 8.00,
         "total_per_km": 18.00, "initial_cost": 4000000,
         "components": {"Insurance": 3.50, "Depreciation": 12.00, "Interest": 4.50, "Fuel": 3.00,
                         "Servicing": 2.00, "Repairs": 1.50, "Tyres": 2.00, "Licences": 0.50},
         "year1": 16.00, "year2": 18.50, "year3": 22.00, "year4": 27.00, "year5": 33.00},
    ],
    "cat6": [
        {"id": "v7", "category_id": "cat6", "label": "150cc Motorcycle",
         "fuel_type": "Petrol", "fixed_per_km": 5.00, "operating_per_km": 4.50,
         "total_per_km": 9.50, "initial_cost": 180000,
         "components": {"Insurance": 1.00, "Depreciation": 2.00, "Interest": 2.00, "Fuel": 2.50,
                         "Servicing": 1.00, "Repairs": 0.50, "Tyres": 0.50, "Licences": 0.30},
         "year1": 8.50, "year2": 9.50, "year3": 11.00, "year4": 13.00, "year5": 15.50},
    ],
}

ROUTES = [
    {"from_city": "Nairobi", "to_city": "Mombasa", "km": 485},
    {"from_city": "Nairobi", "to_city": "Kisumu", "km": 355},
    {"from_city": "Nairobi", "to_city": "Nakuru", "km": 160},
    {"from_city": "Nairobi", "to_city": "Eldoret", "km": 315},
    {"from_city": "Nairobi", "to_city": "Malindi", "km": 500},
    {"from_city": "Nairobi", "to_city": "Nanyuki", "km": 210},
]

def find_variant(variant_id: str):
    for variants in VARIANTS.values():
        for v in variants:
            if v["id"] == variant_id:
                return v
    return None
