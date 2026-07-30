# app/shared/__init__.py
# Auto-D Kenya - Shared Package
# ================================================================

"""Shared utilities and constants for Auto-D Kenya."""

from .cache import CacheService
from .utils import format_currency, format_number, clean_phone_number
from .validators import validate_phone, validate_email, validate_plate
from .constants import CURRENCIES, FUEL_TYPES, BODY_TYPES, TRANSMISSION_TYPES

__all__ = [
    "CacheService",
    "format_currency",
    "format_number",
    "clean_phone_number",
    "validate_phone",
    "validate_email",
    "validate_plate",
    "CURRENCIES",
    "FUEL_TYPES",
    "BODY_TYPES",
    "TRANSMISSION_TYPES"
]
