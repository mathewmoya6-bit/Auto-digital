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
    CostComponent,
    ValuationResponse,
    VehicleMakeResponse,
    VehicleModelResponse,
    VehicleVariantResponse,
    VehicleDetailResponse,
    VehicleSearchResponse,
    RunningCostResponse,
    MileageResponse,
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
    "OwnershipResponse",
    "FuelResponse",
    "MarketTrendsResponse",
    "ErrorResponse",
]
