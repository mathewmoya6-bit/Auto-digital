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
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://xgkdbithhlvoqjnqvfmj.supabase.co")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhna2RiaXRoaGx2b3FqbnF2Zm1qIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI2NTE4NzQsImV4cCI6MjA5ODIyNzg3NH0.-4P2aQAlDl_4oW0C18gh7cEBzoIKeiLUmMnITz-Nt9Y")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
    
    # ─── JWT ──────────────────────────────────────────────────────
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-use-strong-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # ─── CORS ──────────────────────────────────────────────────────
    # IMPORTANT: Add all domains that need to access your API
    BACKEND_CORS_ORIGINS: str = os.getenv(
        "BACKEND_CORS_ORIGINS",
        "https://auto-d.meipressgroup.com,"
        "https://auto-digital.meipressgroup.com,"
        "https://auto-digital.onrender.com,"
        "https://auto-d.onrender.com,"
        "http://localhost:3000,"
        "http://localhost:8000,"
        "http://127.0.0.1:3000,"
        "http://127.0.0.1:8000"
    )
    CORS_ALLOW_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS,PATCH"
    CORS_ALLOW_HEADERS: str = "Authorization,Content-Type,Accept,Origin,X-Requested-With,Access-Control-Allow-Origin,Access-Control-Allow-Headers,Access-Control-Allow-Methods"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_MAX_AGE: int = 86400  # 24 hours
    
    # ─── M-PESA ──────────────────────────────────────────────────
    MPESA_CONSUMER_KEY: str = os.getenv("MPESA_CONSUMER_KEY", "")
    MPESA_CONSUMER_SECRET: str = os.getenv("MPESA_CONSUMER_SECRET", "")
    MPESA_PASSKEY: str = os.getenv("MPESA_PASSKEY", "")
    MPESA_SHORTCODE: str = os.getenv("MPESA_SHORTCODE", "4095377")
    MPESA_ENVIRONMENT: str = os.getenv("MPESA_ENVIRONMENT", "production")
    MPESA_CALLBACK_URL: str = os.getenv(
        "MPESA_CALLBACK_URL",
        "https://auto-digital.onrender.com/api/v1/mpesa/callback"
    )
    
    # ─── DEFAULTS ──────────────────────────────────────────────────
    DEFAULT_FUEL_PRICE_PETROL: float = 214.03
    DEFAULT_FUEL_PRICE_DIESEL: float = 222.86
    DEFAULT_FUEL_PRICE_ELECTRIC: float = 30.00
    DEFAULT_ANNUAL_MILEAGE: int = 20000
    DEFAULT_DEPRECIATION_RATE: float = 0.15
    DEFAULT_INSURANCE_RATE: float = 0.045
    
    # ─── LOGGING ──────────────────────────────────────────────────
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # ─── API BASE ──────────────────────────────────────────────────
    API_BASE_URL: str = os.getenv(
        "API_BASE_URL",
        "https://auto-digital.onrender.com"
    )
    
    # ─── HELPERS ──────────────────────────────────────────────────
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as list."""
        origins = [x.strip() for x in self.BACKEND_CORS_ORIGINS.split(",") if x.strip()]
        # Always include the API base URL
        if self.API_BASE_URL and self.API_BASE_URL not in origins:
            origins.append(self.API_BASE_URL)
        return origins
    
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
