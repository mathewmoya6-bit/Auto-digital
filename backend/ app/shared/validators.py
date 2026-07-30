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
   
