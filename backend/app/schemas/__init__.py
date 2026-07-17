# backend/app/schemas/__init__.py
"""
Schemas Package - Request/Response validation
Pydantic schemas for API requests and responses
"""

from app.schemas.request import (
    RunningCostRequest,
    MileageRateRequest,
    OwnershipCostRequest,
    ValuationRequest,
    FuelPriceRequest,
    AdminSettingsRequest,
    ReportRequest,
)
from app.schemas.response import (
    RunningCostResponse,
    MileageRateResponse,
    OwnershipCostResponse,
    ValuationResponse,
    VehicleDetailResponse,
    FuelPriceResponse,
    ReportResponse,
    CostComponent,
)

__all__ = [
    # Requests
    "RunningCostRequest",
    "MileageRateRequest",
    "OwnershipCostRequest",
    "ValuationRequest",
    "FuelPriceRequest",
    "AdminSettingsRequest",
    "ReportRequest",
    # Responses
    "RunningCostResponse",
    "MileageRateResponse",
    "OwnershipCostResponse",
    "ValuationResponse",
    "VehicleDetailResponse",
    "FuelPriceResponse",
    "ReportResponse",
    "CostComponent",
]
