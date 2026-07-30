# app/modules/vehicles/__init__.py
# Auto-D Kenya - Vehicles Module
# ================================================================

"""Vehicles module for Auto-D Kenya."""

from .router import router
from .service import VehicleService
from .schemas import VehicleRequest, VehicleResponse
from .models import Vehicle

__all__ = [
    "router",
    "VehicleService",
    "VehicleRequest",
    "VehicleResponse",
    "Vehicle"
]
