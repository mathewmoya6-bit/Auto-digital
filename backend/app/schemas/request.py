# backend/app/schemas/request.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class RunningCostRequest(BaseModel):
    variant_id: str
    distance: float = Field(..., gt=0, description="Distance in km")
    trip_type: str = Field("mixed", description="urban, highway, mixed, offroad")
    driving_style: str = Field("normal", description="normal, aggressive, defensive")
    year: Optional[int] = None
    
class MileageRateRequest(RunningCostRequest):
    pass
    
class OwnershipCostRequest(BaseModel):
    variant_id: str
    years: int = Field(5, gt=0, le=20)
    annual_distance: float = Field(20000, gt=0)
    driving_style: str = Field("normal", description="normal, aggressive, defensive")
    trip_type: str = Field("mixed", description="urban, highway, mixed, offroad")
    include_finance: bool = False
    down_payment: Optional[float] = None
    interest_rate: Optional[float] = None
    
class ValuationRequest(BaseModel):
    variant_id: str
    year: int
    mileage: float
    condition: str = Field("good", description="excellent, good, fair, poor")
    accident_history: bool = False
    previous_owners: int = 1
    service_history: bool = True

class FuelPriceRequest(BaseModel):
    fuel_type: str
    price: float
    region: Optional[str] = None

class AdminSettingsRequest(BaseModel):
    setting_key: str
    setting_value: Dict[str, Any]
    description: Optional[str] = None

class ReportRequest(BaseModel):
    report_type: str = Field(..., description="mileage, ownership, valuation, fuel")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    vehicle_ids: Optional[list[str]] = None
    user_id: Optional[str] = None
