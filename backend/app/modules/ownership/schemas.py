from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class OwnershipCostRequest(BaseModel):
    vehicle_id: int = Field(..., gt=0)
    as_of_date: Optional[date] = None


class OwnershipCostResponse(BaseModel):
    vehicle_id: int
    purchase_price: float
    total_fuel_cost: float
    total_maintenance_cost: float
    total_insurance_cost: float
    total_tax_cost: float
    total_repair_cost: float
    depreciation: float
    total_cost_of_ownership: float
    ownership_days: int
    cost_per_day: float


class OwnershipCostResult(BaseModel):
    success: bool = True
    data: OwnershipCostResponse
    currency: str = "KES"
