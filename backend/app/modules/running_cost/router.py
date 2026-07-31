# app/modules/running_cost/router.py
"""
Auto-D Kenya - Running Cost Routes
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user

router = APIRouter(prefix="/running-cost", tags=["Running Cost"])


# ============================================================
# SCHEMAS
# ============================================================

class RunningCostRequest(BaseModel):
    variant_id: int

    distance: float = Field(default=150, ge=1)
    annual_mileage: float = Field(default=20000, ge=0)

    fuel_price: float = Field(default=200, ge=0)

    trip_type: str = "mixed"
    driving_style: str = "normal"
    usage_type: str = "private"
    location: str = "nairobi"
    condition: str = "good"

    year: int = 2024

    financed: bool = False
    down_payment: float = 30
    interest_rate: float = 16
    loan_term: int = 4

    years: int = 5

    include_insurance: bool = True
    include_maintenance: bool = True
    include_tyres: bool = True
    include_depreciation: bool = True


class RunningCostResponse(BaseModel):
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


# ============================================================
# ROUTES
# ============================================================

@router.post("/calculate", response_model=RunningCostResponse)
async def calculate_running_cost(
    request: RunningCostRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Calculate vehicle running costs.
    """
    from app.modules.running_cost.service import RunningCostService

    service = RunningCostService()

    return await service.calculate_running_cost(
        request=request,
        user_id=current_user["id"],
    )


@router.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "running_cost",
    }
