# backend/app/repositories/__init__.py
"""
Repositories Package - Data access layer
Handles database operations and data retrieval
"""

from app.repositories.vehicle_repository import VehicleRepository
from app.repositories.fuel_repository import FuelRepository
from app.repositories.settings_repository import SettingsRepository
from app.repositories.user_repository import UserRepository

__all__ = [
    "VehicleRepository",
    "FuelRepository",
    "SettingsRepository",
    "UserRepository",
]
