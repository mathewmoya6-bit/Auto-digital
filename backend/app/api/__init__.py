# backend/app/api/__init__.py
"""
API Package - Versioned API endpoints
"""

from app.api.v1 import auth, vehicles, valuation, mileage, ownership, fuel, admin, reports, running_cost

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
