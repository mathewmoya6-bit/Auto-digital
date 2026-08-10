# app/modules/valuation/schema.py
"""Pydantic request/response schemas for AUTO-D valuation."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ValuationRequest(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    manufacture_year: Optional[int] = Field(default=None, ge=1900, le=2100)
    mileage: int = Field(default=0, ge=0)
    condition: str = "good"
    accident_history: str = "none"
    previous_owners: int = Field(default=0, ge=0)
    location: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    engine_capacity_id: Optional[int] = None

    # Compatible with the current frontend/router.
    vehicle_crsp_id: Optional[int] = None
    crsp_id: Optional[int] = None

    vehicle_type: Optional[str] = None
    body_type: Optional[str] = None

    # Extra frontend fields can be accepted without breaking the API.
    registration: Optional[str] = None


class ValuationResponse(BaseModel):
    success: bool
    status: str
    crsp_found: bool = False
    crsp_id: Optional[int] = None
    crsp_value: float = 0.0
    estimated_value: float = 0.0
    estimated_value_min: float = 0.0
    estimated_value_max: float = 0.0
    confidence_score: int = 0
    value_adjustments: Dict[str, Any] = Field(default_factory=dict)

    vehicle: Dict[str, Any] = Field(default_factory=dict)
    crsp: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

    class Config:
        extra = "allow"


class CRSPVehicleResponse(BaseModel):
    success: bool
    found: bool
    data: Optional[Dict[str, Any]] = None
    results: list[Dict[str, Any]] = Field(default_factory=list)
    message: Optional[str] = None
