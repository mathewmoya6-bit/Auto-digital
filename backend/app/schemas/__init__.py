"""
Schemas Package
"""
from app.schemas.request import (
    ValuationRequest,
    RunningCostRequest,
    MileageRequest,
    MileageRateRequest,
    OwnershipRequest,
    OwnershipCostRequest,  # ← Added
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
    MileageRateResponse,
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
    "OwnershipCostRequest",  # ← Added
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
    "MileageRateResponse",
    "OwnershipResponse",
    "FuelResponse",
    "MarketTrendsResponse",
    "ErrorResponse",
]
