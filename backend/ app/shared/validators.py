# app/shared/validators.py
# Auto-D Kenya - Validators
# ================================================================
# TYPE: SHARED - Validation utilities

import re
from typing import Optional


def validate_phone(phone: str) -> bool:
    """Validate phone number."""
    cleaned = re.sub(r'\D', '', phone)
    if cleaned.startswith('254'):
        cleaned = cleaned[3:]
    if cleaned.startswith('0'):
        cleaned = cleaned[1:]
    return bool(re.match(r'^(7\d{8}|11\d{7})$', cleaned))


def validate_email(email: str) -> bool:
    """Validate email address."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_plate(plate: str) -> bool:
    """Validate vehicle plate number."""
    pattern = r'^[A-Z]{2,3}\s?\d{3}[A-Z]?$'
    return bool(re.match(pattern, plate.upper().strip()))


def validate_year(year: int) -> bool:
    """Validate vehicle year."""
    current_year = datetime.utcnow().year
    return 1950 <= year <= current_year


def validate_mileage(mileage: int) -> bool:
    """Validate mileage."""
    return 0 <= mileage <= 1000000


def validate_price(price: float) -> bool:
    """Validate price."""
    return 0 <= price <= 100000000
