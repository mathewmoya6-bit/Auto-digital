# backend/app/api/v1/__init__.py
"""
API V1 - Version 1 of the Auto-D API
All endpoints are prefixed with /api/v1
"""

from app.api.v1 import (
    auth,
    vehicles,
    valuation,
    mileage,
    ownership,
    fuel,
    admin,
    reports,
    running_cost
)

__all__ = [
    "auth",
    "vehicles",
    "valuation",
    "mileage",
    "ownership",
    "fuel",
    "admin",
    "reports",
    "running_cost",
]
