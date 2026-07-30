# schemas.py
# Auto-D Kenya - Pydantic Schemas
# ================================================================

import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator


# ─── AUTH ──────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    created_at: datetime


# ─── VEHICLES ──────────────────────────────────────────────────────

class VehicleRequest(BaseModel):
    plate: str
    make_model: Optional[str] = None
    vin: Optional[str] = None
    year: Optional[int] = None
    mileage: Optional[int] = 0


class VehicleResponse(BaseModel):
    id: str
    plate: str
    make_model: Optional[str]
    vin: Optional[str]
    year: Optional[int]
    mileage: int
    value: float
    verified: bool
    created_at: datetime


# ─── SERVICES ──────────────────────────────────────────────────────

class ServiceResponse(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str]
    price: float
    currency: str
    icon: Optional[str]
    active: bool
    purchased: bool = False


# ─── M-PESA ────────────────────────────────────────────────────────

class MpesaPaymentRequest(BaseModel):
    phone: str
    service_id: str
    description: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    amount: Optional[float] = None
    
    @validator('phone')
    def validate_phone(cls, v):
        # Remove non-digits
        phone = re.sub(r'\D', '', v)
        # Remove country code if present
        if phone.startswith('254'):
            phone = phone[3:]
        if phone.startswith('0'):
            phone = phone[1:]
        if not re.match(r'^(7\d{8}|11\d{7})$', phone):
            raise ValueError('Invalid phone number. Must be a Safaricom number (07X or 011X)')
        return phone


class MpesaPaymentResponse(BaseModel):
    checkout_request_id: str
    message: str
    status: str


class MpesaCallbackRequest(BaseModel):
    Body: Optional[Dict[str, Any]] = None
    stkCallback: Optional[Dict[str, Any]] = None


# ─── VALUATION ────────────────────────────────────────────────────

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
    fuel_type_factor: float
    body_type_factor: float
    vehicle_name: str
    year: int
    mileage: float
    location: str
    condition: str


# ─── RUNNING COST ──────────────────────────────────────────────────

class RunningCostRequest(BaseModel):
    variant_id: str
    distance: float = 150
    annual_mileage: float = 20000
    fuel_price: float = 200
    trip_type: str = "mixed"
    driving_style: str = "normal"
    usage_type: str = "private"
    location: str = "nairobi"
    condition: str = "good"
    year: int = 2024
    financed: bool = False
    down_payment_percent: float = 30
    interest_rate: float = 16
    loan_term: int = 4
    years: int = 5
    include_insurance: bool = True
    include_maintenance: bool = True
    include_tyres: bool = True
    include_depreciation: bool = True


class RunningCostResponse(BaseModel):
    variant_id: str
    distance: float
    annual_mileage: float
    fuel_price: float
    tripTotal: float
    tripCostPerKm: float
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
    fiveYearData: List[Dict[str, Any]]
    total5YearCost: float
    remainingValue: float
    ageAdjustedCost: float
    monthlyFuel: float
    monthlyService: float
    monthlyInsurance: float
    monthlyTyre: float
    monthlyDepreciation: float
    annualFuel: float
    annualService: float
    annualInsurance: float
    annualTyre: float
    annualDepreciation: float


# ─── OWNERSHIP COST ──────────────────────────────────────────────

class OwnershipCostRequest(BaseModel):
    variant_id: str
    purchase_price: float = 4500000
    down_payment: float = 1000000
    loan_term_years: int = 3
    interest_rate: float = 14
    annual_mileage: float = 20000
    fuel_price: float = 200
    insurance_rate: float = 3
    maintenance_cost_per_km: float = 1.5
    tyre_cost_per_km: float = 0.8
    include_depreciation: bool = True
    include_insurance: bool = True
    include_maintenance: bool = True
    include_tyres: bool = True


class OwnershipCostResponse(BaseModel):
    variant_id: str
    total_cost: float
    monthly_cost: float
    monthly_payment: float
    total_interest: float
    components: List[Dict[str, Any]]
    loan_details: Dict[str, Any]


# ─── MILEAGE ──────────────────────────────────────────────────────

class MileageRequest(BaseModel):
    variant_id: str
    distance: float = 150
    annual_mileage: float = 20000
    fuel_price: float = 200


class MileageResponse(BaseModel):
    variant_id: str
    distance: float
    fuel_consumption: float
    fuel_cost: float
    cost_per_km: float
    annual_fuel_cost: float
    co2_emissions: float


# ─── SERVICE REQUEST ─────────────────────────────────────────────

class ServiceRequestCreate(BaseModel):
    vehicle_id: str
    service_id: str
    notes: Optional[str] = None


class ServiceRequestResponse(BaseModel):
    id: str
    user_id: str
    vehicle_id: Optional[str]
    vehicle_plate: Optional[str]
    service_id: str
    service_name: str
    amount: float
    notes: Optional[str]
    status: str
    created_at: datetime


# ─── FUEL PRICES ──────────────────────────────────────────────────

class FuelPriceResponse(BaseModel):
    fuel_type: str
    price: float
    currency: str
    location: Optional[str]
    effective_date: datetime
