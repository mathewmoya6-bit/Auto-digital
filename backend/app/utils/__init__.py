# backend/app/utils/__init__.py
"""
Utils Package - Utility functions
Helper functions for various operations
"""

from app.utils.converters import (
    km_to_miles,
    miles_to_km,
    liters_to_gallons,
    gallons_to_liters,
    currency_format,
)
from app.utils.validators import (
    validate_email,
    validate_phone,
    validate_vin,
    validate_license_plate,
)
from app.utils.helpers import (
    generate_uuid,
    calculate_age,
    format_date,
    get_current_timestamp,
)

__all__ = [
    "km_to_miles",
    "miles_to_km",
    "liters_to_gallons",
    "gallons_to_liters",
    "currency_format",
    "validate_email",
    "validate_phone",
    "validate_vin",
    "validate_license_plate",
    "generate_uuid",
    "calculate_age",
    "format_date",
    "get_current_timestamp",
]
