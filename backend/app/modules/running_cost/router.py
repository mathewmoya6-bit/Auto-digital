# app/modules/running_cost/router.py
"""Running Cost routes for Auto-D Kenya"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime

from app.core.database import get_supabase
from app.modules.auth.dependencies import get_current_user
from app.modules.running_cost.service import RunningCostService

router = APIRouter()

# ─── SCHEMAS ──────────────────────────────────────────────────────

class RunningCostRequest(BaseModel):
    """Request for running cost calculation"""
    variant_id: int = Field(..., description="Vehicle variant ID")
    distance: float = Field(150, description="Trip distance in km", ge=1, le=100000)
    annual_mileage: float = Field(20000, description="Annual mileage in km", ge=0, le=200000)
    fuel_price: float = Field(200, description="Fuel price in KES per litre", ge=0, le=500)
    trip_type: str = Field("mixed", description="Trip type: urban, highway, mixed, offroad")
    driving_style: str = Field("normal", description="Driving style: eco, normal, aggressive")
    usage_type: str = Field("private", description="Usage type: private, commercial, fleet, taxi")
    location: str = Field("nairobi", description="Location for cost adjustment")
    condition: str = Field("good", description="Vehicle condition: poor, fair, good, excellent")
    year: int = Field(2024, description="Vehicle year of manufacture")
    financed: bool = Field(False, description="Whether the vehicle is financed")
    down_payment: float = Field(30, description="Down payment percentage")
    interest_rate: float = Field(16, description="Interest rate percentage")
    loan_term: int = Field(4, description="Loan term in years")
    years: int = Field(5, description="Number of years for projection")
    include_insurance: bool = Field(True)
    include_maintenance: bool = Field(True)
    include_tyres: bool = Field(True)
    include_depreciation: bool = Field(True)

class RunningCostResponse(BaseModel):
    """Response for running cost calculation"""
    tripTotal: float
    tripCostPerKm: float
    distance: float
    fuelCostTrip: float
    serviceTrip: float
    tyreTrip: float
    insuranceTrip: float
    depreciationTrip: float
    fuelCostPerKm: float
    servicePerKm: float
    tyrePerKm: float
    insurancePerKm: float
    depreciationPerKm: float
    monthlyFuel: float
    monthlyService: float
    monthlyTyre: float
    monthlyInsurance: float
    monthlyDepreciation: float
    annualFuel: float
    annualService: float
    annualTyre: float
    annualInsurance: float
    annualDepreciation: float
    fiveYearData: list
    total5YearCost: float
    originalCost: float
    ageAdjustedCost: float
    current_value: float
    remainingValue: float
    resale_value: float
    fuelTypeDisplay: str
    fuelConsumption: float
    calculated_at: datetime

# ─── ENDPOINTS ──────────────────────────────────────────────────

@router.post("/running-cost/calculate", response_model=RunningCostResponse)
async def calculate_running_cost(
    request: RunningCostRequest,
    current_user = Depends(get_current_user)
):
    """
    Calculate running costs for a vehicle.
    
    Returns:
    - Trip costs
    - Per km breakdown
    - Monthly/Annual projections
    - 5-year cost analysis
    """
    service = RunningCostService()
    return await service.calculate_running_cost(request, current_user["id"])

@router.get("/running-cost/health")
async def health_check():
    """Health check for running cost service"""
    return {"status": "healthy", "service": "running_cost"}
