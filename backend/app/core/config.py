# config.py
# Auto-D Kenya - Configuration Settings
# ================================================================

import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # FastAPI
    PROJECT_NAME: str = "Auto-D Kenya API"
    API_V1_PREFIX: str = "/api/v1"
    PORT: int = 10000
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://xgkdbithhlvoqjnqvfmj.supabase.co")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhna2RiaXRoaGx2b3FqbnF2Zm1qIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI2NTE4NzQsImV4cCI6MjA5ODIyNzg3NH0.-4P2aQAlDl_4oW0C18gh7cEBzoIKeiLUmMnITz-Nt9Y")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "UGf98/D/Y7WQO8WZDYfPULTLcUUYMl3exPhoEutu2gizMebMiZAUJln7UMbGbdtqoYnOOd5n6N7hm8RbPR7gCg==")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DATABASE_POOL_SIZE: int = 10
    
    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # CORS - Allow all Auto-D Kenya domains
    BACKEND_CORS_ORIGINS: List[str] = [
        "https://auto-digital.meipressgroup.com",
        "https://auto-d.meipressgroup.com",
        "https://auto-digital.onrender.com",
        "https://auto-d.onrender.com",
        "http://localhost:3000",
        "http://localhost:5000",
        "http://localhost:5173",
        "http://localhost:8000"
    ]
    
    # M-Pesa
    MPESA_CONSUMER_KEY: str = os.getenv("MPESA_CONSUMER_KEY", "LI2gcJZEheN8qCfXHEXV4gdYXvOBHVnv")
    MPESA_CONSUMER_SECRET: str = os.getenv("MPESA_CONSUMER_SECRET", "aGGo8AuPJVpsZLcs")
    MPESA_PASSKEY: str = os.getenv("MPESA_PASSKEY", "7eb17a031bdfd5b4251863a1ddb72c5b9cd14f3385aa6a258c1442a0116e8277")
    MPESA_SHORTCODE: str = os.getenv("MPESA_SHORTCODE", "4095377")
    MPESA_ENVIRONMENT: str = "production"
    MPESA_CALLBACK_URL: str = "https://auto-digital.meipressgroup.com/api/v1/mpesa/callback"
    MPESA_RESULT_URL: str = "https://auto-digital.meipressgroup.com/api/v1/mpesa/result"
    MPESA_TIMEOUT_URL: str = "https://auto-digital.meipressgroup.com/api/v1/mpesa/timeout"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    RATE_LIMIT_PER_DAY: int = 5000
    
    # Default Values
    DEFAULT_FUEL_PRICE_PETROL: float = 214.03
    DEFAULT_FUEL_PRICE_DIESEL: float = 222.86
    DEFAULT_FUEL_PRICE_ELECTRIC: float = 30.00
    DEFAULT_FUEL_PRICE_LPG: float = 120.00
    DEFAULT_ANNUAL_MILEAGE: int = 20000
    DEFAULT_DEPRECIATION_RATE: float = 0.15
    DEFAULT_INSURANCE_RATE: float = 0.045
    DEFAULT_TYRE_LIFESPAN: int = 45000
    DEFAULT_SERVICE_INTERVAL: int = 10000
    
    # Depreciation Rates
    DEPRECIATION_RATE_ANNUAL: float = 0.15
    DEPRECIATION_RATE_MILEAGE_PER_KM: float = 0.000005
    DEPRECIATION_MAX_AGE: int = 20
    DEPRECIATION_MIN_VALUE: float = 0.1
    
    # Feature Flags
    ENABLE_MPESA: bool = True
    ENABLE_CACHING: bool = True
    ENABLE_ANALYTICS: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # API Base URL
    API_BASE_URL: str = "https://auto-digital.meipressgroup.com"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
