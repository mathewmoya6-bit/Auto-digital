# app/modules/mileage/__init__.py

"""
Mileage Module
==============

Handles vehicle mileage tracking, validation, and analytics.
"""

from .router import router
from .schemas import (
    MileageCreate,
    MileageUpdate,
    MileageResponse,
    MileageListResponse,
    MileageAnalytics,
    MileageValidationRequest,
    MileageValidationResponse,
)
from .service import MileageService
from .repository import MileageRepository

__all__ = [
    "router",
    "MileageCreate",
    "MileageUpdate",
    "MileageResponse",
    "MileageListResponse",
    "MileageAnalytics",
    "MileageValidationRequest",
    "MileageValidationResponse",
    "MileageService",
    "MileageRepository",
]
