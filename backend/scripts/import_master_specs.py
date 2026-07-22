import os
import pandas as pd
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CSV_FILE = "data/vehicle_master_specs.csv"

df = pd.read_csv(CSV_FILE)

print(f"Found {len(df)} specifications")

success = 0
failed = 0

for _, row in df.iterrows():

    record = {
        "variant_id": str(row["variant_id"]),
        "engine_cc": None if pd.isna(row["engine_cc"]) else int(row["engine_cc"]),
        "horsepower": None if pd.isna(row["horsepower"]) else int(row["horsepower"]),
        "torque_nm": None if pd.isna(row["torque_nm"]) else int(row["torque_nm"]),
        "fuel_type": None if pd.isna(row["fuel_type"]) else row["fuel_type"],
        "transmission": None if pd.isna(row["transmission"]) else row["transmission"],
        "drive_type": None if pd.isna(row["drive_type"]) else row["drive_type"],
        "body_style": None if pd.isna(row["body_style"]) else row["body_style"],
        "seats": None if pd.isna(row["seats"]) else int(row["seats"]),
        "doors": None if pd.isna(row["doors"]) else int(row["doors"]),
        "combined_consumption": None if pd.isna(row["combined_consumption"]) else float(row["combined_consumption"]),
        "service_interval_km": None if pd.isna(row["service_interval_km"]) else int(row["service_interval_km"])
    }

    try:
        supabase.table("vehicle_master_specs").upsert(record).execute()
        success += 1
    except Exception as e:
        failed += 1
        print(record["variant_id"], e)

print("----------------------------")
print("Imported :", success)
print("Failed   :", failed)
