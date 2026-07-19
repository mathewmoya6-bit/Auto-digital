# backend/app/core/config.py
"""
Configuration - Application settings
"""

import os
import json
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # ─── FastAPI Configuration ──────────────────────────────────────
    PROJECT_NAME: str = "Auto-D Kenya API"
    API_V1_PREFIX: str = "/api/v1"
    PORT: int = 10000
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    API_VERSION: str = "4.0.0"
    
    # ─── Server URLs ──────────────────────────────────────────────────
    API_BASE_URL: str = Field(
        default="https://auto-digital.onrender.com",
        env="API_BASE_URL"
    )
    FRONTEND_URL: str = Field(
        default="https://auto-d.meipressgroup.com",
        env="FRONTEND_URL"
    )
    
    # ─── Supabase Configuration ──────────────────────────────────────
    SUPABASE_URL: str = Field(
        default="https://xgkdbithhlvoqjnqvfmj.supabase.co",
        env="SUPABASE_URL"
    )
    SUPABASE_KEY: str = Field(..., env="SUPABASE_KEY")
    SUPABASE_JWT_SECRET: Optional[str] = None
    
    # ─── Database Configuration ──────────────────────────────────────
    DATABASE_URL: Optional[str] = None
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # ─── JWT Authentication ──────────────────────────────────────────
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # ─── Admin Credentials ──────────────────────────────────────────
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = Field(default="admin123", env="ADMIN_PASSWORD")
    ADMIN_EMAIL: str = "admin@auto-d.ke"
    
    # ─── CORS Configuration ──────────────────────────────────────────
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=[
            "https://auto-digital.onrender.com",
            "https://auto-d.meipressgroup.com",
            "https://auto-d-kenya-backend.onrender.com",
            "https://auto-d.onrender.com",
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5000",
            "http://localhost:8000",
            "http://127.0.0.1:5500",
            "https://auto-d-kenya.github.io",
        ],
        env="BACKEND_CORS_ORIGINS"
    )
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_MAX_AGE: int = 86400
    CORS_ALLOW_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS,PATCH"
    CORS_ALLOW_HEADERS: str = "Authorization,Content-Type,Accept,Origin,X-Requested-With"
    
    # ─── M-PESA Configuration ──────────────────────────────────────
    # These are the environment variables the mpesa_service.py expects
    MPESA_ENV: str = Field(
        default="sandbox",
        env="MPESA_ENV"
    )
    MPESA_CONSUMER_KEY: Optional[str] = Field(
        None,
        env="MPESA_CONSUMER_KEY"
    )
    MPESA_CONSUMER_SECRET: Optional[str] = Field(
        None,
        env="MPESA_CONSUMER_SECRET"
    )
    MPESA_PASSKEY: Optional[str] = Field(
        None,
        env="MPESA_PASSKEY"
    )
    MPESA_SHORTCODE: str = Field(
        default="4095377",
        env="MPESA_SHORTCODE"
    )
    CALLBACK_BASE_URL: str = Field(
        default="https://auto-digital.onrender.com",
        env="CALLBACK_BASE_URL"
    )
    
    # ─── M-PESA Callback URLs ──────────────────────────────────────
    MPESA_CALLBACK_URL: str = Field(
        default="https://auto-digital.onrender.com/api/v1/mpesa/callback",
        env="MPESA_CALLBACK_URL"
    )
    MPESA_RESULT_URL: str = Field(
        default="https://auto-digital.onrender.com/api/v1/mpesa/result",
        env="MPESA_RESULT_URL"
    )
    MPESA_TIMEOUT_URL: str = Field(
        default="https://auto-digital.onrender.com/api/v1/mpesa/timeout",
        env="MPESA_TIMEOUT_URL"
    )
    
    # ─── Rate Limiting ──────────────────────────────────────────────
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    RATE_LIMIT_PER_DAY: int = 5000
    RATE_LIMIT_STRATEGY: str = "fixed-window"
    RATE_LIMIT_STORAGE_URL: str = "memory://"
    
    # ─── Redis ──────────────────────────────────────────────────────
    REDIS_ENABLED: bool = False
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    REDIS_SSL: bool = False
    
    # ─── Feature Flags ──────────────────────────────────────────────
    ENABLE_MPESA: bool = True
    ENABLE_GOOGLE_AUTH: bool = True
    ENABLE_OFFLINE_MODE: bool = False
    ENABLE_ANALYTICS: bool = True
    ENABLE_EMAIL_NOTIFICATIONS: bool = True
    ENABLE_CACHING: bool = True
    ENABLE_DOCS: bool = False
    
    # ─── Default Values ──────────────────────────────────────────────
    DEFAULT_FUEL_PRICE_PETROL: float = 203.47
    DEFAULT_FUEL_PRICE_DIESEL: float = 195.67
    DEFAULT_FUEL_PRICE_ELECTRIC: float = 30.00
    DEFAULT_FUEL_PRICE_LPG: float = 120.00
    DEFAULT_ANNUAL_MILEAGE: int = 20000
    DEFAULT_DEPRECIATION_RATE: float = 0.15
    DEFAULT_INSURANCE_RATE: float = 0.045
    DEFAULT_TYRE_LIFESPAN: int = 45000
    DEFAULT_SERVICE_INTERVAL: int = 10000
    
    # ─── Vehicle Cost Engine Parameters ─────────────────────────────
    FUEL_CONSUMPTION_FACTOR_URBAN: float = 1.15
    FUEL_CONSUMPTION_FACTOR_HIGHWAY: float = 0.85
    FUEL_CONSUMPTION_FACTOR_MIXED: float = 1.0
    DEPRECIATION_RATE_SUV_A: float = 0.12
    DEPRECIATION_RATE_SUV_B: float = 0.15
    DEPRECIATION_RATE_SUV_C: float = 0.18
    DEPRECIATION_RATE_SUV_D: float = 0.20
    DEPRECIATION_RATE_SEDAN_A: float = 0.10
    DEPRECIATION_RATE_SEDAN_B: float = 0.13
    DEPRECIATION_RATE_SEDAN_C: float = 0.16
    DEPRECIATION_RATE_SEDAN_D: float = 0.19
    DEPRECIATION_RATE_PICKUP_A: float = 0.11
    DEPRECIATION_RATE_PICKUP_B: float = 0.14
    DEPRECIATION_RATE_PICKUP_C: float = 0.17
    DEPRECIATION_RATE_LUXURY_A: float = 0.20
    DEPRECIATION_RATE_LUXURY_B: float = 0.25
    DEPRECIATION_RATE_LUXURY_C: float = 0.30
    
    # ─── Logging ──────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "auto-d.log"
    LOG_MAX_BYTES: int = 10485760
    LOG_BACKUP_COUNT: int = 5
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # ─── Performance Tuning ──────────────────────────────────────────
    WORKERS: int = 4
    THREADS: int = 2
    TIMEOUT: int = 120
    KEEPALIVE: int = 5
    MAX_REQUESTS: int = 1000
    MAX_REQUESTS_JITTER: int = 100
    
    # ─── Maintenance ──────────────────────────────────────────────────
    MAINTENANCE_MODE: bool = False
    MAINTENANCE_MESSAGE: str = "Auto-D Kenya is undergoing scheduled maintenance. We'll be back soon!"
    
    # ─── Email Configuration ────────────────────────────────────────
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: str = "Auto-D Kenya"
    
    # ─── Security ────────────────────────────────────────────────────
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    PASSWORD_RESET_EXPIRATION_HOURS: int = 1
    VERIFICATION_TOKEN_EXPIRATION_HOURS: int = 24
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 30
    
    # ─── File Upload ──────────────────────────────────────────────────
    MAX_UPLOAD_SIZE: int = 10485760
    MAX_PHOTO_UPLOADS: int = 8
    ALLOWED_IMAGE_TYPES: str = "image/jpeg,image/png,image/webp,image/gif"
    
    # ─── API Keys ──────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = Field(
        default="https://auto-digital.onrender.com/api/v1/auth/google/callback",
        env="GOOGLE_REDIRECT_URI"
    )
    GA_MEASUREMENT_ID: Optional[str] = None
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: str = "production"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    
    # ─── Backup ──────────────────────────────────────────────────────
    BACKUP_ENABLED: bool = True
    BACKUP_INTERVAL_HOURS: int = 24
    BACKUP_RETENTION_DAYS: int = 30
    BACKUP_S3_BUCKET: Optional[str] = None
    BACKUP_S3_REGION: str = "us-east-1"
    
    # ─── Supabase Table Names ──────────────────────────────────────
    TABLE_VEHICLE_MAKES: str = "vehicle_makes"
    TABLE_VEHICLE_MODELS: str = "vehicle_models"
    TABLE_VEHICLE_VARIANTS: str = "vehicle_variants"
    TABLE_FUEL_PRICES: str = "fuel_prices"
    TABLE_INSURANCE_RATES: str = "insurance_rates"
    TABLE_SERVICE_INTERVALS: str = "service_intervals"
    TABLE_REPAIR_CLASSES: str = "repair_classes"
    TABLE_DEPRECIATION_RATES: str = "depreciation_rates"
    TABLE_OWNERSHIP_SETTINGS: str = "ownership_settings"
    TABLE_VEHICLE_VALUES: str = "vehicle_values"
    TABLE_USERS: str = "users"
    TABLE_USER_PROFILES: str = "user_profiles"
    TABLE_MILEAGE_REPORTS: str = "mileage_reports"
    TABLE_OWNERSHIP_REPORTS: str = "ownership_reports"
    TABLE_VALUATION_REPORTS: str = "valuation_reports"
    TABLE_PAYMENTS: str = "payments"
    TABLE_SERVICE_ACCESS: str = "service_access"
    TABLE_SERVICE_PRICES: str = "service_prices"
    TABLE_AUDIT_LOGS: str = "audit_logs"
    
    # ─── API Documentation ──────────────────────────────────────────
    API_DOCS_URL: str = "/docs"
    API_REDOC_URL: str = "/redoc"
    API_OPENAPI_URL: str = "/openapi.json"
    
    # ─── Swagger/OpenAPI ────────────────────────────────────────────
    SWAGGER_ENABLED: bool = False
    SWAGGER_TITLE: str = "Auto-D Kenya API"
    SWAGGER_DESCRIPTION: str = "Vehicle cost analysis and valuation system for Kenya"
    SWAGGER_CONTACT_NAME: str = "Auto-D Support"
    SWAGGER_CONTACT_EMAIL: str = "support@auto-d.ke"
    SWAGGER_LICENSE_NAME: str = "Proprietary"
    
    # ─── Session ──────────────────────────────────────────────────────
    SESSION_TYPE: str = "filesystem"
    PERMANENT_SESSION_LIFETIME: int = 86400
    SESSION_COOKIE_NAME: str = "auto-d-session"
    
    # ─── Templates & Static ──────────────────────────────────────────
    TEMPLATES_FOLDER: str = "app/templates"
    STATIC_FOLDER: str = "app/static"
    STATIC_URL: str = "/static"
    
    # ─── Testing ────────────────────────────────────────────────────
    TESTING: bool = False
    TEST_DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/autod_test"
    
    # ─── Health Check ──────────────────────────────────────────────
    HEALTH_CHECK_PATH: str = "/health"
    READINESS_CHECK_PATH: str = "/ready"
    LIVENESS_CHECK_PATH: str = "/live"
    
    # ─── Metrics ────────────────────────────────────────────────────
    METRICS_ENABLED: bool = True
    METRICS_PATH: str = "/metrics"
    PROMETHEUS_MULTIPROC_DIR: str = "/tmp/prometheus"
    
    # ─── Compression ────────────────────────────────────────────────
    COMPRESS_ENABLED: bool = True
    COMPRESS_MIMETYPES: str = "application/json,application/javascript,text/css,text/html,text/plain"
    
    # ─── Cache Control ──────────────────────────────────────────────
    CACHE_CONTROL_MAX_AGE: int = 3600
    CACHE_CONTROL_STALE_WHILE_REVALIDATE: int = 86400
    
    class Config:
        """Pydantic config"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"
    
    def parse_cors_origins(self) -> List[str]:
        """Parse CORS origins from environment variable"""
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            try:
                return json.loads(self.BACKEND_CORS_ORIGINS)
            except json.JSONDecodeError:
                return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",")]
        return self.BACKEND_CORS_ORIGINS
    
    def get_api_url(self) -> str:
        """Get the full API base URL"""
        return self.API_BASE_URL
    
    def get_frontend_url(self) -> str:
        """Get the frontend URL"""
        return self.FRONTEND_URL
    
    def get_mpesa_config(self) -> dict:
        """Get M-Pesa configuration as a dictionary"""
        return {
            "environment": self.MPESA_ENV,
            "shortcode": self.MPESA_SHORTCODE,
            "consumer_key": self.MPESA_CONSUMER_KEY,
            "consumer_secret": self.MPESA_CONSUMER_SECRET,
            "passkey": self.MPESA_PASSKEY,
            "callback_url": self.MPESA_CALLBACK_URL,
            "result_url": self.MPESA_RESULT_URL,
            "timeout_url": self.MPESA_TIMEOUT_URL,
            "enabled": self.ENABLE_MPESA
        }
    
    def is_mpesa_configured(self) -> bool:
        """Check if M-Pesa is fully configured"""
        return all([
            self.MPESA_CONSUMER_KEY,
            self.MPESA_CONSUMER_SECRET,
            self.MPESA_PASSKEY,
            self.MPESA_SHORTCODE
        ])


# Create settings instance
settings = Settings()

# Parse CORS origins if needed
if isinstance(settings.BACKEND_CORS_ORIGINS, str):
    try:
        settings.BACKEND_CORS_ORIGINS = json.loads(settings.BACKEND_CORS_ORIGINS)
    except json.JSONDecodeError:
        settings.BACKEND_CORS_ORIGINS = [origin.strip() for origin in settings.BACKEND_CORS_ORIGINS.split(",")]

# Log configuration on startup (only in debug mode)
if settings.DEBUG:
    print(f"🔗 API Base URL: {settings.API_BASE_URL}")
    print(f"🌐 Frontend URL: {settings.FRONTEND_URL}")
    print(f"📡 Supabase URL: {settings.SUPABASE_URL}")
    print(f"🔒 CORS Origins: {settings.BACKEND_CORS_ORIGINS}")
    print(f"📱 M-Pesa Shortcode: {settings.MPESA_SHORTCODE}")
    print(f"📱 M-Pesa Environment: {settings.MPESA_ENV}")
    print(f"📱 M-Pesa Configured: {settings.is_mpesa_configured()}")
