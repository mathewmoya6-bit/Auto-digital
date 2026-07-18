# backend/app/api/__init__.py
"""
API Package - Versioned API endpoints
"""

from app.api.v1 import (
    auth_router,
    vehicles_router,
    valuation_router,
    mileage_router,
    ownership_router,
    fuel_router,
    admin_router,
    reports_router,
    running_cost_router,
)

__all__ = [
    "auth_router",
    "vehicles_router",
    "valuation_router",
    "mileage_router",
    "ownership_router",
    "fuel_router",
    "admin_router",
    "reports_router",
    "running_cost_router",
]
