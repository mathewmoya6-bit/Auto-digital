# app/modules/valuation/schemas.py
# ================================================================
# Auto-D Kenya - Valuation Schemas
# ================================================================

from typing import Optional, List

from pydantic import BaseModel


class ValuationRequest(BaseModel):

    variant_id: int

    year: int = 2020

    mileage: int = 50000

    condition: str = "good"

    accident_history: str = "none"

    previous_owners: int = 1

    service_history: bool = True

    location: str = "nairobi"

    images: Optional[List[str]] = None



class ValuationResponse(BaseModel):

    variant_id: int

    market_value: float

    retail_value: float

    trade_value: float

    dealer_value: float = 0

    confidence_score: float = 0

    base_price: float = 0

    age_factor: float = 0

    mileage_factor: float = 0

    location_factor: float = 0

    condition_factor: float = 0

    accident_factor: float = 0
