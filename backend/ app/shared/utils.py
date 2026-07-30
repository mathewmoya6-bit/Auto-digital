# app/shared/utils.py
# Auto-D Kenya - Utility Functions
# ================================================================
# TYPE: SHARED - General utility functions

import re
import json
from datetime import datetime
from typing import Optional, Dict, Any


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
    """Calculate age from year."""
    return datetime.utcnow().year - year


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp a value between min and max."""
    return max(min_value, min(value, max_value))


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def generate_slug(text: str) -> str:
    """Generate a URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text
