# app/modules/ownership/router.py
"""
Auto-D Kenya - Ownership (TCO) Routes
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user

router = APIRouter(
    prefix="/ownership",
    tags=["Ownership"],
)


# ============================================================
# SCHEMAS
# ============================================================

class TCORequest(BaseModel):
    """Total Cost of Ownership request."""

    variant_id: int

    purchase_price: float = Field(default=4_500_000, ge=0)
    down_payment: float = Field(default=1_000_000, ge=0)

    loan_term_years: int = Field(default=3, ge=1, le=7)
    interest_rate: float = Field(default=14, ge=0, le=28)

    annual_mileage: float = Field(default=20_000, ge=0, le=60_000)

    fuel_price: float = Field(default=200, ge=0, le=500)

    insurance_rate: float = Field(default=3, ge=0, le=8)

    maintenance_cost_per_km: float = Field(default=1.5, ge=0, le=5)
    tyre_cost_per_km: float = Field(default=0.8, ge=0, le=2)

    include_depreciation: bool = True
    include_insurance: bool = True
    include_maintenance: bool = True
    include_tyres: bool = True


class TCOComponent(BaseModel):
    name: str
    amount: float
    percentage: float


class TCOResponse(BaseModel):
    total_cost: float
    monthly_cost: float
    monthly_payment: float
    total_interest: float

    components: List[TCOComponent]
    yearly_breakdown: List[dict]

    loan_details: dict
    vehicle_details: dict

    currency: str = "KES"

    calculated_at: datetime


# ============================================================
# ROUTES
# ============================================================

@router.post("/calculate", response_model=TCOResponse)
async def calculate_tco(
    request: TCORequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Calculate Total Cost of Ownership (TCO).
    """
    from app.modules.ownership.service import OwnershipService

    service = OwnershipService()

    return await service.calculate_tco(
        request=request,
        user_id=current_user["id"],
    )


@router.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "service": "ownership",
    }
