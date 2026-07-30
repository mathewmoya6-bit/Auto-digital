# database.py
# Auto-D Kenya - Database Models
# ================================================================

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON, 
    ForeignKey, DECIMAL, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql import func
from supabase import create_client, Client

from config import settings

Base = declarative_base()

# ─── SUPABASE CLIENT ──────────────────────────────────────────────

_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    """Get Supabase client instance."""
    global _supabase_client
    if _supabase_client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise ValueError("Supabase credentials not configured")
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase_client


# ─── DATABASE MODELS ──────────────────────────────────────────────

class VehicleMake(Base):
    __tablename__ = "vehicle_makes"
    
    make_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    make_name = Column(String(100), nullable=False, unique=True)
    make_country = Column(String(50))
    category_id = Column(PGUUID(as_uuid=True))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class VehicleModel(Base):
    __tablename__ = "vehicle_models"
    
    model_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    make_id = Column(PGUUID(as_uuid=True), nullable=False)
    model_name = Column(String(100), nullable=False)
    model_body_type = Column(String(50))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class VehicleGeneration(Base):
    __tablename__ = "vehicle_generations"
    
    generation_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(PGUUID(as_uuid=True), nullable=False)
    generation_code = Column(String(50))
    generation_start_year = Column(Integer)
    generation_end_year = Column(Integer)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class VehicleVariant(Base):
    __tablename__ = "vehicle_variants"
    
    variant_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generation_id = Column(PGUUID(as_uuid=True), nullable=False)
    variant_name = Column(String(100), nullable=False)
    trim_level = Column(String(50))
    engine_size_cc = Column(Integer)
    power_hp = Column(Integer)
    torque_nm = Column(Integer)
    fuel_consumption_combined = Column(Float)
    co2_emissions = Column(Float)
    seats = Column(Integer, default=5)
    doors = Column(Integer, default=4)
    fuel_type_name = Column(String(20))
    transmission_type_name = Column(String(20))
    drive_type_name = Column(String(20))
    body_type_name = Column(String(50))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Vehicle(Base):
    __tablename__ = "vehicles"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), nullable=False)
    plate = Column(String(20), nullable=False)
    make_model = Column(String(100))
    vin = Column(String(50))
    year = Column(Integer)
    mileage = Column(Integer, default=0)
    value = Column(DECIMAL(15, 2), default=0)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Service(Base):
    __tablename__ = "services"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(DECIMAL(15, 2), nullable=False)
    currency = Column(String(3), default="KES")
    icon = Column(String(50))
    active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class UserService(Base):
    __tablename__ = "user_services"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), nullable=False)
    service_id = Column(PGUUID(as_uuid=True), nullable=False)
    status = Column(String(20), default="active")
    purchased_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class MpesaPayment(Base):
    __tablename__ = "mpesa_payments"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True))
    service_id = Column(PGUUID(as_uuid=True))
    checkout_request_id = Column(String(100), nullable=False, unique=True)
    transaction_id = Column(String(100))
    phone = Column(String(20), nullable=False)
    amount = Column(DECIMAL(15, 2), nullable=False)
    status = Column(String(20), default="pending")
    description = Column(Text)
    request_id = Column(PGUUID(as_uuid=True))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class ServiceRequest(Base):
    __tablename__ = "service_requests"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), nullable=False)
    vehicle_id = Column(PGUUID(as_uuid=True))
    vehicle_plate = Column(String(20))
    service_id = Column(PGUUID(as_uuid=True))
    service_name = Column(String(100))
    amount = Column(DECIMAL(15, 2))
    notes = Column(Text)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class FuelPrice(Base):
    __tablename__ = "fuel_prices"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fuel_type = Column(String(20), nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), default="KES")
    location = Column(String(50))
    effective_date = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())


class OwnershipReport(Base):
    __tablename__ = "ownership_reports"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), nullable=False)
    variant_id = Column(PGUUID(as_uuid=True))
    purchase_price = Column(DECIMAL(15, 2))
    down_payment = Column(DECIMAL(15, 2))
    loan_term_years = Column(Integer)
    interest_rate = Column(Float)
    annual_mileage = Column(Integer)
    total_cost = Column(DECIMAL(15, 2))
    monthly_cost = Column(DECIMAL(15, 2))
    monthly_payment = Column(DECIMAL(15, 2))
    total_interest = Column(DECIMAL(15, 2))
    created_at = Column(DateTime, default=func.now())


class ValuationReport(Base):
    __tablename__ = "valuation_reports"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), nullable=False)
    variant_id = Column(PGUUID(as_uuid=True))
    market_value = Column(DECIMAL(15, 2))
    retail_value = Column(DECIMAL(15, 2))
    trade_value = Column(DECIMAL(15, 2))
    confidence_score = Column(Float)
    year = Column(Integer)
    mileage = Column(Integer)
    location = Column(String(50))
    condition = Column(String(20))
    created_at = Column(DateTime, default=func.now())
