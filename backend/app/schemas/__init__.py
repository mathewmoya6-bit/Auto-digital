"""
Schemas Package
"""
from app.schemas.request import (
    ValuationRequest,
    RunningCostRequest,
    MileageRequest,
    MileageRateRequest,
    OwnershipRequest,
    FuelRequest,
    VehicleSearchRequest,
    VehicleCreateRequest,
)

from app.schemas.response import (
    CostComponent,
    ValuationResponse,
    VehicleMakeResponse,
    VehicleModelResponse,
    VehicleVariantResponse,
    VehicleDetailResponse,
    VehicleSearchResponse,
    RunningCostResponse,
    MileageResponse,
    MileageRateResponse,  # ← Added
    OwnershipResponse,
    FuelResponse,
    MarketTrendsResponse,
    ErrorResponse,
)

__all__ = [
    # Request schemas
    "ValuationRequest",
    "RunningCostRequest",
    "MileageRequest",
    "MileageRateRequest",
    "OwnershipRequest",
    "FuelRequest",
    "VehicleSearchRequest",
    "VehicleCreateRequest",
    # Response schemas
    "CostComponent",
    "ValuationResponse",
    "VehicleMakeResponse",
    "VehicleModelResponse",
    "VehicleVariantResponse",
    "VehicleDetailResponse",
    "VehicleSearchResponse",
    "RunningCostResponse",
    "MileageResponse",
    "MileageRateResponse",  # ← Added
    "OwnershipResponse",
    "FuelResponse",
    "MarketTrendsResponse",
    "ErrorResponse",
]
