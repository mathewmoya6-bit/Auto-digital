# app/core/config.py
# Auto-D Kenya - Configuration Settings
# ================================================================
# TYPE: CORE - Configuration management

import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # ─── APP ──────────────────────────────────────────────────────
    PROJECT_NAME: str = "Auto-D Kenya API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Vehicle cost analysis and valuation system for Kenya"
    API_V1_PREFIX: str = "/api/v1"
    PORT: int = 10000
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    
    # ─── SUPABASE ──────────────────────────────────────────────────
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
    
    # ─── JWT ──────────────────────────────────────────────────────
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # ─── CORS ──────────────────────────────────────────────────────
    BACKEND_CORS_ORIGINS: str = (
        "https://auto-digital.meipressgroup.com,"
        "https://auto-d.meipressgroup.com,"
        "https://auto-digital.onrender.com,"
        "https://auto-d.onrender.com"
    )
    CORS_ALLOW_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS,PATCH"
    CORS_ALLOW_HEADERS: str = "Authorization,Content-Type,Accept,Origin,X-Requested-With"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_MAX_AGE: int = 86400
    
    # ─── M-PESA ──────────────────────────────────────────────────
    MPESA_CONSUMER_KEY: str = os.getenv("MPESA_CONSUMER_KEY", "")
    MPESA_CONSUMER_SECRET: str = os.getenv("MPESA_CONSUMER_SECRET", "")
    MPESA_PASSKEY: str = os.getenv("MPESA_PASSKEY", "")
    MPESA_SHORTCODE: str = os.getenv("MPESA_SHORTCODE", "4095377")
    MPESA_ENVIRONMENT: str = "production"
    MPESA_CALLBACK_URL: str = "https://auto-digital.meipressgroup.com/api/v1/mpesa/callback"
    
    # ─── DEFAULTS ──────────────────────────────────────────────────
    DEFAULT_FUEL_PRICE_PETROL: float = 214.03
    DEFAULT_FUEL_PRICE_DIESEL: float = 222.86
    DEFAULT_FUEL_PRICE_ELECTRIC: float = 30.00
    DEFAULT_ANNUAL_MILEAGE: int = 20000
    DEFAULT_DEPRECIATION_RATE: float = 0.15
    DEFAULT_INSURANCE_RATE: float = 0.045
    
    # ─── LOGGING ──────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    
    # ─── API BASE ──────────────────────────────────────────────────
    API_BASE_URL: str = "https://auto-digital.meipressgroup.com"
    
    # ─── HELPERS ──────────────────────────────────────────────────
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as list."""
        return [x.strip() for x in self.BACKEND_CORS_ORIGINS.split(",") if x.strip()]
    
    def get_cors_methods(self) -> List[str]:
        """Get CORS methods as list."""
        return [x.strip() for x in self.CORS_ALLOW_METHODS.split(",") if x.strip()]
    
    def get_cors_headers(self) -> List[str]:
        """Get CORS headers as list."""
        return [x.strip() for x in self.CORS_ALLOW_HEADERS.split(",") if x.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
