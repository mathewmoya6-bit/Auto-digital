import pandas as pd

df = pd.read_csv("data/vehicle_master_specs.csv")

required = [
    "variant_id",
    "fuel_type",
    "transmission",
    "engine_cc"
]

for col in required:

    missing = df[col].isna().sum()

    print(f"{col}: {missing} missing")

print()

duplicates = df["variant_id"].duplicated().sum()

print("Duplicate variant IDs:", duplicates)
