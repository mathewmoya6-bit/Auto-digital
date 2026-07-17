# backend/app/models/__init__.py
"""
Models Package - Data models
Contains Pydantic models for data validation and serialization
"""

from app.models.vehicle import VehicleMake, VehicleModel, VehicleVariant
from app.models.user import User, UserProfile
from app.models.fuel import FuelPrice
from app.models.mileage import MileageReport
from app.models.ownership import OwnershipReport

__all__ = [
    "VehicleMake",
    "VehicleModel",
    "VehicleVariant",
    "User",
    "UserProfile",
    "FuelPrice",
    "MileageReport",
    "OwnershipReport",
]
