from supabase import create_client
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

specs = supabase.table("vehicle_master_specs").select("*").execute().data

fuel_lookup = {
    "Petrol": 1,
    "Diesel": 2,
    "Hybrid": 3,
    "Electric": 4,
    "CNG": 5,
    "LPG": 6,
    "Hydrogen": 7,
}

trans_lookup = {
    "Manual 4spd": 1,
    "Manual 5spd": 2,
    "Manual 6spd": 3,
    "Automatic 4spd": 4,
    "Automatic 5spd": 5,
    "Automatic 6spd": 6,
    "Automatic 8spd": 7,
    "CVT": 8,
    "DCT": 9,
    "DSG": 10,
    "Electric Direct Drive": 11,
}

for spec in specs:

    update = {
        "engine_size_cc": spec["engine_cc"],
        "fuel_type_id": fuel_lookup.get(spec["fuel_type"]),
        "transmission_type_id": trans_lookup.get(spec["transmission"]),
    }

    supabase.table("vehicle_variants") \
        .update(update) \
        .eq("id", int(spec["variant_id"])) \
        .execute()

print("Vehicle variants synchronized.")
