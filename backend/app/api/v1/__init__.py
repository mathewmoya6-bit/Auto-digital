# backend/app/api/v1/__init__.py
"""
API V1 - Version 1 of the Auto-D API
All endpoints are prefixed with /api/v1
"""

# Import all router modules
from app.api.v1 import auth
from app.api.v1 import vehicles
from app.api.v1 import valuation
from app.api.v1 import mileage
from app.api.v1 import ownership
from app.api.v1 import fuel
from app.api.v1 import admin
from app.api.v1 import reports
from app.api.v1 import running_cost

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
