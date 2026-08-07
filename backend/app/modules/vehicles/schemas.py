"""
Auto-D Kenya
Vehicle Master Module
"""

from app.modules.vehicle_master.router import router
from app.modules.vehicle_master.schemas import (
    VehicleMasterUpdate,
    BasePriceUpdate,
    SpecificationUpdate,
    VehicleUpdate,
)
from app.modules.vehicle_master.service import VehicleMasterService

__all__ = [
    "router",
    "VehicleMasterUpdate",
    "BasePriceUpdate",
    "SpecificationUpdate",
    "VehicleUpdate",
    "VehicleMasterService",
]
