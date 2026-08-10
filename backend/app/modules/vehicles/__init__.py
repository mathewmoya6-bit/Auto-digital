"""
Auto-D Kenya
Vehicles Module
"""

from app.modules.vehicles.router import router
from app.modules.vehicles.service import VehicleService
from app.modules.vehicles.repository import VehicleRepository

__all__ = [
    "router",
    "VehicleService",
    "VehicleRepository",
]
