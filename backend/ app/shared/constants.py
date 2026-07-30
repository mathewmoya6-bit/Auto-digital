# app/shared/constants.py
# Auto-D Kenya - Constants
# ================================================================
# TYPE: SHARED - Application constants

# ─── CURRENCIES ──────────────────────────────────────────────────

CURRENCIES = {
    "KES": "Kenyan Shilling",
    "USD": "US Dollar",
    "EUR": "Euro",
    "GBP": "British Pound",
    "TZS": "Tanzanian Shilling",
    "UGX": "Ugandan Shilling"
}

# ─── FUEL TYPES ──────────────────────────────────────────────────

FUEL_TYPES = {
    "petrol": "Petrol",
    "diesel": "Diesel",
    "electric": "Electric",
    "hybrid": "Hybrid",
    "lpg": "LPG",
    "cng": "CNG"
}

# ─── BODY TYPES ──────────────────────────────────────────────────

BODY_TYPES = {
    "suv": "SUV",
    "sedan": "Sedan",
    "hatchback": "Hatchback",
    "pickup": "Pickup",
    "van": "Van",
    "truck": "Truck",
    "bus": "Bus",
    "coupe": "Coupe",
    "convertible": "Convertible",
    "wagon": "Wagon"
}

# ─── TRANSMISSION TYPES ──────────────────────────────────────────

TRANSMISSION_TYPES = {
    "automatic": "Automatic",
    "manual": "Manual",
    "cvt": "CVT",
    "semi_automatic": "Semi-Automatic"
}

# ─── VEHICLE CONDITIONS ──────────────────────────────────────────

VEHICLE_CONDITIONS = {
    "excellent": "Excellent",
    "very_good": "Very Good",
    "good": "Good",
    "fair": "Fair",
    "poor": "Poor"
}

# ─── ACCIDENT HISTORY ────────────────────────────────────────────

ACCIDENT_HISTORY = {
    "none": "None",
    "minor": "Minor",
    "major": "Major",
    "total_loss": "Total Loss"
}

# ─── LOCATION FACTORS ────────────────────────────────────────────

LOCATION_FACTORS = {
    "nairobi": 1.05,
    "mombasa": 1.02,
    "kisumu": 1.00,
    "nakuru": 1.00,
    "eldoret": 1.00,
    "thika": 1.00,
    "kiambu": 1.02,
    "kajiado": 1.00,
    "machakos": 1.00,
    "meru": 0.98,
    "nyeri": 0.98,
    "embu": 0.97,
    "malindi": 1.02,
    "nanyuki": 1.01,
    "other": 1.00
}

# ─── CONFIGURATION ───────────────────────────────────────────────

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
MAX_PHOTO_UPLOADS = 8
PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100
