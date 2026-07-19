"""
Schemas Package
"""
from app.schemas.request import (
    ValuationRequest,
    RunningCostRequest,  # ← This should now work
    MileageRequest,
    OwnershipRequest,
    FuelRequest,
    VehicleSearchRequest,
    VehicleCreateRequest,
)
from app.schemas.response import (
    ValuationResponse,
    ErrorResponse,
    VehicleVariantResponse,
    MarketTrendsResponse,
    VehicleDetailResponse,
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
    "ErrorResponse",
    "VehicleVariantResponse",
    "MarketTrendsResponse",
    "VehicleDetailResponse",
]
