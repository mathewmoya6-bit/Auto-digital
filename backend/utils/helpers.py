# utils/helpers.py
# Auto-D Kenya - Helper Functions
# ================================================================
# TYPE: SERVICE - Utility helper functions

import re
import json
from typing import Optional, Dict, Any
from datetime import datetime


def format_currency(value: float, currency: str = "KES") -> str:
    """Format currency value."""
    return f"{currency} {value:,.2f}"


def format_number(value: float) -> str:
    """Format number with commas."""
    return f"{value:,.0f}"


def clean_phone_number(phone: str) -> str:
    """Clean and normalize phone number."""
    phone = re.sub(r'\D', '', phone)
    if phone.startswith('254'):
        phone = phone[3:]
    if phone.startswith('0'):
        phone = phone[1:]
    return phone


def is_valid_safaricom_phone(phone: str) -> bool:
    """Check if phone number is a valid Safaricom number."""
    phone = clean_phone_number(phone)
    return bool(re.match(r'^(7\d{8}|11\d{7})$', phone))


def safe_parse_json(data: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON string."""
    try:
        return json.loads(data)
    except:
        return None


def get_timestamp() -> str:
    """Get current timestamp as ISO string."""
    return datetime.utcnow().isoformat()


def calculate_age(year: int) -> int:
    """Calculate age of vehicle from year."""
    current_year = datetime.utcnow().year
    return current_year - year


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp a value between min and max."""
    return max(min_value, min(value, max_value))


def get_location_factor(location: str) -> float:
    """Get location factor for valuation."""
    factors = {
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
    return factors.get(location.lower(), 1.00)


def get_condition_factor(condition: str) -> float:
    """Get condition factor for valuation."""
    factors = {
        "excellent": 1.10,
        "very_good": 1.05,
        "good": 1.00,
        "fair": 0.90,
        "poor": 0.75
    }
    return factors.get(condition.lower(), 1.00)


def get_accident_factor(accident_history: str) -> float:
    """Get accident history factor for valuation."""
    factors = {
        "none": 1.00,
        "minor": 0.92,
        "major": 0.80,
        "total_loss": 0.60
    }
    return factors.get(accident_history.lower(), 1.00)
