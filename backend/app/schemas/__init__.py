"""
Schemas Package
"""
from app.schemas.request import (
    ValuationRequest,
    RunningCostRequest,
    MileageRequest,
    OwnershipRequest,
    FuelRequest,
    VehicleSearchRequest,
    VehicleCreateRequest,
)

from app.schemas.response import (
    ValuationResponse,
    VehicleMakeResponse,
    VehicleModelResponse,
    VehicleVariantResponse,
    VehicleDetailResponse,
    VehicleSearchResponse,
    ErrorResponse,
    MarketTrendsResponse,
    RunningCostResponse,
    MileageResponse,
    OwnershipResponse,
    FuelResponse,
)

__all__ = [
    # Request schemas
    "ValuationRequest",
    "RunningCostRequest",
    "MileageRequest",
    "OwnershipRequest",
    "FuelRequest",
    "VehicleSearchRequest",
    "VehicleCreateRequest",
    # Response schemas
    "ValuationResponse",
    "VehicleMakeResponse",
    "VehicleModelResponse",
    "VehicleVariantResponse",
    "VehicleDetailResponse",
    "VehicleSearchResponse",
    "ErrorResponse",
    "MarketTrendsResponse",
    "RunningCostResponse",
    "MileageResponse",
    "OwnershipResponse",
    "FuelResponse",
]
