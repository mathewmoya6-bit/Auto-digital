# app/modules/valuation/schemas.py
# Auto-D Kenya - Valuation Schemas
# ================================================================
# TYPE: MODULE - Valuation Pydantic schemas

from typing import Optional, List
from pydantic import BaseModel


class ValuationRequest(BaseModel):
    variant_id: str
    year: int = 2020
    mileage: float = 50000
    condition: str = "good"
    accident_history: str = "none"
    previous_owners: int = 1
    service_history: bool = True
    location: str = "nairobi"
    images: Optional[List[str]] = None


class ValuationResponse(BaseModel):
    variant_id: str
    market_value: float
    retail_value: float
    trade_value: float
    dealer_value: float
    confidence_score: float
    base_price: float
    age_factor: float
    mileage_factor: float
    location_factor: float
    condition_factor: float
    accident_factor: float
