"""
Auto-D Kenya
Vehicle Ownership Cost Schemas
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class OwnershipCostRequest(BaseModel):
    """
    Request for calculating vehicle ownership cost.
    """

    vehicle_id: int = Field(
        ...,
        gt=0,
        description="Vehicle ID",
    )

    as_of_date: Optional[date] = Field(
        default=None,
        description="Date up to which ownership cost is calculated",
    )


class OwnershipCostResponse(BaseModel):
    """
    Vehicle ownership cost calculation result.
    """

    vehicle_id: int

    purchase_price: float = 0.0

    total_fuel_cost: float = 0.0

    total_maintenance_cost: float = 0.0

    total_insurance_cost: float = 0.0

    total_tax_cost: float = 0.0

    total_repair_cost: float = 0.0

    depreciation: float = 0.0

    total_cost_of_ownership: float = 0.0

    ownership_days: int = 0

    cost_per_day: float = 0.0


class OwnershipCostResult(BaseModel):
    """
    API response wrapper.
    """

    success: bool = True

    data: OwnershipCostResponse

    currency: str = "KES"

    as_of_date: Optional[date] = None
