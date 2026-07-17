# backend/app/schemas/response.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class CostComponent(BaseModel):
    component: str
    amount: float
    description: Optional[str] = None

class RunningCostResponse(BaseModel):
    fuel: float
    service: float
    tyres: float
    insurance: float
    repairs: float
    depreciation: float
    finance: float
    misc: float
    total: float
    cost_per_km: float
    components: List[CostComponent]

class MileageRateResponse(BaseModel):
    total_rate: float
    fuel_rate: float
    maintenance_rate: float
    tyre_rate: float
    insurance_rate: float
    depreciation_rate: float
    finance_rate: float
    misc_rate: float
    total_running_cost: float
    distance: float
    vehicle_details: Optional[Dict[str, Any]] = None

class OwnershipCostResponse(BaseModel):
    total_cost: float
    annual_cost: float
    cost_per_km: float
    breakdown: Dict[str, float]
    year_by_year: List[Dict[str, Any]]

class ValuationResponse(BaseModel):
    trade_value: float
    dealer_value: float
    retail_value: float
    quick_sale: float
    insurance_value: float
    depreciation_rate: float
    estimated_life: int

class VehicleDetailResponse(BaseModel):
    variant_id: str
    make: Optional[str]
    model: Optional[str]
    variant: str
    year: int
    engine_cc: float
    fuel_type: str
    transmission: str
    fuel_consumption: float
    insurance_group: int
    service_interval: int
    tyre_size: Optional[str]
    market_value: float
    depreciation_class: str
    tyre_cost: float
    service_cost: float

class FuelPriceResponse(BaseModel):
    fuel_type: str
    price: float
    updated_at: str

class ReportResponse(BaseModel):
    report_type: str
    generated_at: str
    data: Dict[str, Any]
    summary: Dict[str, Any]
