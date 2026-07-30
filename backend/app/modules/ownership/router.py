# app/modules/ownership/router.py
"""Ownership (TCO) routes for Auto-D Kenya"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime

from app.modules.auth.dependencies import get_current_user

router = APIRouter()

# ─── SCHEMAS ──────────────────────────────────────────────────────

class TCORequest(BaseModel):
    """Request for Total Cost of Ownership calculation"""
    variant_id: int = Field(..., description="Vehicle variant ID")
    purchase_price: float = Field(4500000, description="Purchase price in KES", ge=0)
    down_payment: float = Field(1000000, description="Down payment in KES", ge=0)
    loan_term_years: int = Field(3, description="Loan term in years", ge=1, le=7)
    interest_rate: float = Field(14, description="Annual interest rate %", ge=0, le=28)
    annual_mileage: float = Field(20000, description="Annual mileage in km", ge=0, le=60000)
    fuel_price: float = Field(200, description="Fuel price in KES per litre", ge=0, le=500)
    insurance_rate: float = Field(3, description="Insurance rate %", ge=0, le=8)
    maintenance_cost_per_km: float = Field(1.5, description="Maintenance cost per km", ge=0, le=5)
    tyre_cost_per_km: float = Field(0.8, description="Tyre cost per km", ge=0, le=2)
    include_depreciation: bool = Field(True)
    include_insurance: bool = Field(True)
    include_maintenance: bool = Field(True)
    include_tyres: bool = Field(True)

class TCOComponent(BaseModel):
    """TCO component breakdown"""
    name: str
    amount: float
    percentage: float

class TCOResponse(BaseModel):
    """Response for TCO calculation"""
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

# ─── ENDPOINTS ──────────────────────────────────────────────────

@router.post("/ownership/calculate", response_model=TCOResponse)
async def calculate_tco(
    request: TCORequest,
    current_user = Depends(get_current_user)
):
    """
    Calculate Total Cost of Ownership (TCO) for a vehicle.
    
    Returns:
    - Total ownership cost
    - Monthly breakdown
    - Loan details
    - Year-by-year analysis
    """
    # Import service here to avoid circular import
    from app.modules.ownership.service import OwnershipService
    service = OwnershipService()
    return await service.calculate_tco(request, current_user["id"])

@router.get("/ownership/health")
async def health_check():
    """Health check for ownership service"""
    return {"status": "healthy", "service": "ownership"}
