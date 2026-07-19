# backend/app/api/v1/__init__.py
"""
API V1 - Version 1 of the Auto-D API
All endpoints are prefixed with /api/v1
"""

# Import all routers directly
from .auth import router as auth_router
from .vehicles import router as vehicles_router
from .valuation import router as valuation_router
from .mileage import router as mileage_router
from .ownership import router as ownership_router
from .fuel import router as fuel_router
from .admin import router as admin_router
from .reports import router as reports_router
from .running_cost import router as running_cost_router
from .mpesa import router as mpesa_router

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
    "mpesa_router",
]
