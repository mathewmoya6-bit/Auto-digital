# config.py
# Auto-D Kenya - Configuration Settings
# ================================================================
# TYPE: SERVICE - Configuration management

import os
from typing import List, Optional, Union
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ─── FASTAPI ───────────────────────────────────────────────────
    PROJECT_NAME: str = "Auto-D Kenya API"
    API_V1_PREFIX: str = "/api/v1"
    PORT: int = 10000
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    
    # ─── SUPABASE ──────────────────────────────────────────────────
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://xgkdbithhlvoqjnqvfmj.supabase.co")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhna2RiaXRoaGx2b3FqbnF2Zm1qIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI2NTE4NzQsImV4cCI6MjA5ODIyNzg3NH0.-4P2aQAlDl_4oW0C18gh7cEBzoIKeiLUmMnITz-Nt9Y")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "UGf98/D/Y7WQO8WZDYfPULTLcUUYMl3exPhoEutu2gizMebMiZAUJln7UMbGbdtqoYnOOd5n6N7hm8RbPR7gCg==")
    
    # ─── DATABASE ──────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # ─── JWT AUTHENTICATION ───────────────────────────────────────
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # ─── CORS ──────────────────────────────────────────────────────
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
    
    # ─── M-PESA DARAJA API ────────────────────────────────────────
    MPESA_CONSUMER_KEY: str = os.getenv("MPESA_CONSUMER_KEY", "LI2gcJZEheN8qCfXHEXV4gdYXvOBHVnv")
    MPESA_CONSUMER_SECRET: str = os.getenv("MPESA_CONSUMER_SECRET", "aGGo8AuPJVpsZLcs")
    MPESA_PASSKEY: str = os.getenv("MPESA_PASSKEY", "7eb17a031bdfd5b4251863a1ddb72c5b9cd14f3385aa6a258c1442a0116e8277")
    MPESA_SHORTCODE: str = os.getenv("MPESA_SHORTCODE", "4095377")
    MPESA_ENVIRONMENT: str = "production"
    MPESA_CALLBACK_URL: str = "https://auto-digital.meipressgroup.com/api/v1/mpesa/callback"
    MPESA_RESULT_URL: str = "https://auto-digital.meipressgroup.com/api/v1/mpesa/result"
    MPESA_TIMEOUT_URL: str = "https://auto-digital.meipressgroup.com/api/v1/mpesa/timeout"
    
    # ─── RATE LIMITING ─────────────────────────────────────────────
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    RATE_LIMIT_PER_DAY: int = 5000
    RATE_LIMIT_STRATEGY: str = "fixed-window"
    RATE_LIMIT_STORAGE_URL: str = "memory://"
    
    # ─── REDIS ─────────────────────────────────────────────────────
    REDIS_ENABLED: bool = False
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""
    REDIS_SSL: bool = False
    
    # ─── FEATURE FLAGS ─────────────────────────────────────────────
    ENABLE_MPESA: bool = True
    ENABLE_GOOGLE_AUTH: bool = True
    ENABLE_OFFLINE_MODE: bool = False
    ENABLE_ANALYTICS: bool = True
    ENABLE_EMAIL_NOTIFICATIONS: bool = True
    ENABLE_CACHING: bool = True
    ENABLE_DOCS: bool = False
    
    # ─── DEFAULT VALUES ────────────────────────────────────────────
    DEFAULT_FUEL_PRICE_PETROL: float = 214.03
    DEFAULT_FUEL_PRICE_DIESEL: float = 222.86
    DEFAULT_FUEL_PRICE_ELECTRIC: float = 30.00
    DEFAULT_FUEL_PRICE_LPG: float = 120.00
    DEFAULT_ANNUAL_MILEAGE: int = 20000
    DEFAULT_DEPRECIATION_RATE: float = 0.15
    DEFAULT_INSURANCE_RATE: float = 0.045
    DEFAULT_TYRE_LIFESPAN: int = 45000
    DEFAULT_SERVICE_INTERVAL: int = 10000
    
    # ─── VEHICLE COST ENGINE PARAMETERS ──────────────────────────
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
    
    DEPRECIATION_RATE_ANNUAL: float = 0.15
    DEPRECIATION_RATE_MILEAGE_PER_KM: float = 0.000005
    DEPRECIATION_MAX_AGE: int = 20
    DEPRECIATION_MIN_VALUE: float = 0.1
    
    # ─── SCRAPER CONFIGURATION ────────────────────────────────────
    SCRAPE_ENABLED: bool = True
    SCRAPE_INTERVAL_HOURS: int = 24
    MAX_SCRAPE_PAGES: int = 5
    SCRAPE_TIMEOUT_SECONDS: int = 30
    SCRAPE_RETRY_ATTEMPTS: int = 3
    SCRAPE_BATCH_SIZE: int = 100
    SCRAPE_DEDUPLICATE: bool = True
    SCRAPE_MIN_PRICE: int = 10000
    SCRAPE_MAX_PRICE: int = 100000000
    
    # ─── SOURCE PRIORITIES ────────────────────────────────────────
    SOURCE_JIJI_PRIORITY: int = 1
    SOURCE_CHEKI_PRIORITY: int = 2
    SOURCE_AUTOCHEK_PRIORITY: int = 3
    SOURCE_BEEPBEEP_PRIORITY: int = 4
    SOURCE_PIGIAME_PRIORITY: int = 5
    
    # ─── SOURCE URLs ──────────────────────────────────────────────
    SOURCE_JIJI_URL: str = "https://jiji.co.ke"
    SOURCE_CHEKI_URL: str = "https://www.cheki.co.ke"
    SOURCE_AUTOCHEK_URL: str = "https://www.autochek.co.ke"
    SOURCE_BEEPBEEP_URL: str = "https://www.beepbeep.co.ke"
    SOURCE_PIGIAME_URL: str = "https://www.pigiame.co.ke"
    
    # ─── PRICE ALIGNMENT CONFIG ──────────────────────────────────
    PRICE_ALIGNMENT_ENABLED: bool = True
    PRICE_ALIGNMENT_CONFIDENCE_THRESHOLD: float = 0.5
    PRICE_ALIGNMENT_MIN_SAMPLE_SIZE: int = 3
    PRICE_ALIGNMENT_MAX_AGE_DAYS: int = 30
    PRICE_ALIGNMENT_WEIGHT_SOURCE: float = 0.3
    PRICE_ALIGNMENT_WEIGHT_RECENCY: float = 0.25
    PRICE_ALIGNMENT_WEIGHT_SAMPLE_SIZE: float = 0.25
    PRICE_ALIGNMENT_WEIGHT_CONSISTENCY: float = 0.2
    
    # ─── VALUATION DEFAULT PARAMETERS ────────────────────────────
    DEFAULT_BASE_PRICE: int = 3500000
    DEFAULT_CONFIDENCE_SCORE: float = 0.5
    DEFAULT_CONDITION: str = "good"
    DEFAULT_COUNTY: str = "Nairobi"
    DEFAULT_VALUATION_YEAR: int = 2024
    
    # ─── MARKET INTELLIGENCE ──────────────────────────────────────
    MARKET_INTELLIGENCE_ENABLED: bool = True
    MARKET_TREND_LOOKBACK_DAYS: int = 90
    MARKET_SEASONALITY_ENABLED: bool = True
    MARKET_DEMAND_INDEX_ENABLED: bool = True
    MARKET_DEPRECIATION_CURVE_ENABLED: bool = True
    MARKET_ANALYSIS_INTERVAL_HOURS: int = 6
    
    # ─── LOCATION FACTORS ─────────────────────────────────────────
    LOCATION_FACTOR_ENABLED: bool = True
    LOCATION_FACTOR_DEFAULT: float = 1.0
    LOCATION_FACTOR_UPDATE_INTERVAL_DAYS: int = 30
    
    # ─── VEHICLE MATCHING ─────────────────────────────────────────
    VEHICLE_MATCHING_ENABLED: bool = True
    VEHICLE_MATCHING_CONFIDENCE_THRESHOLD: float = 0.7
    VEHICLE_MATCHING_USE_ALIASES: bool = True
    VEHICLE_MATCHING_USE_RULES: bool = True
    
    # ─── PRICE CONFIDENCE ─────────────────────────────────────────
    PRICE_CONFIDENCE_ENABLED: bool = True
    PRICE_CONFIDENCE_MIN_SAMPLE: int = 3
    PRICE_CONFIDENCE_MAX_SAMPLE: int = 100
    PRICE_CONFIDENCE_TIMEOUT_HOURS: int = 24
    
    # ─── SCRAPER WORKER CONFIG ────────────────────────────────────
    SCRAPER_WORKER_JIJI_ENABLED: bool = True
    SCRAPER_WORKER_CHEKI_ENABLED: bool = True
    SCRAPER_WORKER_AUTOCHEK_ENABLED: bool = True
    SCRAPER_WORKER_BEEPBEEP_ENABLED: bool = True
    SCRAPER_WORKER_PIGIAME_ENABLED: bool = True
    
    # ─── SCRAPER RATE LIMITS ──────────────────────────────────────
    SCRAPER_RATE_LIMIT_JIJI: int = 10
    SCRAPER_RATE_LIMIT_CHEKI: int = 10
    SCRAPER_RATE_LIMIT_AUTOCHEK: int = 5
    SCRAPER_RATE_LIMIT_BEEPBEEP: int = 5
    SCRAPER_RATE_LIMIT_PIGIAME: int = 5
    
    # ─── SCRAPER USER AGENTS ──────────────────────────────────────
    SCRAPER_USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    # ─── PRICE ALIGNMENT ENDPOINTS ────────────────────────────────
    PRICE_ALIGN_ENDPOINT: str = "/api/v1/price/align"
    PRICE_ANALYZE_ENDPOINT: str = "/api/v1/price/analyze"
    PRICE_HISTORY_ENDPOINT: str = "/api/v1/price/history"
    PRICE_TREND_ENDPOINT: str = "/api/v1/price/trend"
    PRICE_DISTRIBUTION_ENDPOINT: str = "/api/v1/price/distribution"
    
    # ─── MARKET ENDPOINTS ─────────────────────────────────────────
    MARKET_SCRAPE_ENDPOINT: str = "/api/v1/market/scrape"
    MARKET_INSIGHTS_ENDPOINT: str = "/api/v1/market/insights"
    MARKET_LOCATION_FACTORS_ENDPOINT: str = "/api/v1/market/location/factors"
    MARKET_SOURCES_ENDPOINT: str = "/api/v1/market/sources/status"
    MARKET_MAKES_ENDPOINT: str = "/api/v1/market/makes"
    MARKET_MODELS_ENDPOINT: str = "/api/v1/market/models/{make_id}"
    
    # ─── CACHE CONFIG ─────────────────────────────────────────────
    CACHE_PRICE_ALIGNMENT_TTL: int = 3600
    CACHE_MARKET_INSIGHTS_TTL: int = 7200
    CACHE_VEHICLE_SEARCH_TTL: int = 300
    
    # ─── BULK UPDATE CONFIG ──────────────────────────────────────
    BULK_UPDATE_ENABLED: bool = True
    BULK_UPDATE_BATCH_SIZE: int = 50
    BULK_UPDATE_INTERVAL_HOURS: int = 12
    BULK_UPDATE_TIMEOUT_SECONDS: int = 300
    
    # ─── API BASE URL ─────────────────────────────────────────────
    API_BASE_URL: str = "https://auto-digital.meipressgroup.com"
    
    # ─── EMAIL CONFIGURATION ──────────────────────────────────────
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "notifications@auto-d.ke")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "notifications@auto-d.ke")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "Auto-D Kenya")
    
    # ─── SECURITY ─────────────────────────────────────────────────
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    PASSWORD_RESET_EXPIRATION_HOURS: int = 1
    VERIFICATION_TOKEN_EXPIRATION_HOURS: int = 24
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 30
    
    # ─── FILE UPLOAD LIMITS ──────────────────────────────────────
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    MAX_PHOTO_UPLOADS: int = 8
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    
    # ─── LOGGING ──────────────────────────────────────────────────
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = "auto-d.log"
    LOG_MAX_BYTES: int = 10485760
    LOG_BACKUP_COUNT: int = 5
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # ─── PERFORMANCE TUNING ──────────────────────────────────────
    WORKERS: int = 4
    THREADS: int = 2
    TIMEOUT: int = 120
    KEEPALIVE: int = 5
    MAX_REQUESTS: int = 1000
    MAX_REQUESTS_JITTER: int = 100
    
    # ─── MAINTENANCE MODE ────────────────────────────────────────
    MAINTENANCE_MODE: bool = False
    MAINTENANCE_MESSAGE: str = "Auto-D Kenya is undergoing scheduled maintenance. We'll be back soon!"
    
    # ─── SUPABASE TABLE NAMES ─────────────────────────────────────
    TABLE_VEHICLE_MAKES: str = "vehicle_makes"
    TABLE_VEHICLE_MODELS: str = "vehicle_models"
    TABLE_VEHICLE_GENERATIONS: str = "vehicle_generations"
    TABLE_VEHICLE_VARIANTS: str = "vehicle_variants"
    TABLE_VEHICLE_IMAGES: str = "vehicle_images"
    TABLE_VEHICLE_ALIASES: str = "vehicle_aliases"
    TABLE_VEHICLE_MATCH_RULES: str = "vehicle_match_rules"
    TABLE_MARKET_LISTINGS: str = "market_listings"
    TABLE_MARKET_PRICES: str = "market_prices"
    TABLE_VALUATION_HISTORY: str = "valuation_history"
    TABLE_MARKET_TRENDS: str = "market_trends"
    TABLE_COUNTY_STATISTICS: str = "county_statistics"
    TABLE_PRICE_CONFIDENCE: str = "price_confidence"
    TABLE_DEALERS: str = "dealers"
    TABLE_LOCATION_PRICE_FACTORS: str = "location_price_factors"
    TABLE_CONDITION_PRICE_FACTORS: str = "condition_price_factors"
    TABLE_SCRAPER_JOBS: str = "scraper_jobs"
    TABLE_SCRAPER_WORKERS: str = "scraper_workers"
    TABLE_SERVICES: str = "services"
    TABLE_USER_SERVICES: str = "user_services"
    TABLE_SERVICE_REQUESTS: str = "service_requests"
    TABLE_MPESA_PAYMENTS: str = "mpesa_payments"
    TABLE_USER_VEHICLES: str = "user_vehicles"
    TABLE_FUEL_PRICES: str = "fuel_prices"
    TABLE_INSURANCE_RATES: str = "insurance_rates"
    TABLE_SERVICE_INTERVALS: str = "service_intervals"
    TABLE_REPAIR_CLASSES: str = "repair_classes"
    TABLE_DEPRECIATION_RATES: str = "depreciation_rates"
    TABLE_OWNERSHIP_SETTINGS: str = "ownership_settings"
    TABLE_USERS: str = "users"
    TABLE_USER_PROFILES: str = "user_profiles"
    TABLE_MILEAGE_REPORTS: str = "mileage_reports"
    TABLE_OWNERSHIP_REPORTS: str = "ownership_reports"
    TABLE_VALUATION_REPORTS: str = "valuation_reports"
    TABLE_PAYMENTS: str = "payments"
    TABLE_AUDIT_LOGS: str = "audit_logs"
    
    # ─── API DOCS ──────────────────────────────────────────────────
    SWAGGER_ENABLED: bool = False
    SWAGGER_TITLE: str = "Auto-D Kenya API"
    SWAGGER_DESCRIPTION: str = "Vehicle cost analysis and valuation system for Kenya"
    SWAGGER_CONTACT_NAME: str = "Auto-D Support"
    SWAGGER_CONTACT_EMAIL: str = "support@auto-d.ke"
    SWAGGER_LICENSE_NAME: str = "Proprietary"
    
    # ─── ADDITIONAL CORS ──────────────────────────────────────────
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_MAX_AGE: int = 86400
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    CORS_ALLOW_HEADERS: List[str] = ["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"]
    
    # ─── SESSION ──────────────────────────────────────────────────
    SESSION_TYPE: str = "filesystem"
    PERMANENT_SESSION_LIFETIME: int = 86400
    SESSION_COOKIE_NAME: str = "auto-d-session"
    
    # ─── TEMPLATES ────────────────────────────────────────────────
    TEMPLATES_FOLDER: str = "app/templates"
    STATIC_FOLDER: str = "app/static"
    STATIC_URL: str = "/static"
    
    # ─── TESTING ──────────────────────────────────────────────────
    TESTING: bool = False
    TEST_DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/autod_test"
    
    # ─── METRICS ──────────────────────────────────────────────────
    METRICS_ENABLED: bool = True
    METRICS_PATH: str = "/metrics"
    PROMETHEUS_MULTIPROC_DIR: str = "/tmp/prometheus"
    
    # ─── COMPRESSION ──────────────────────────────────────────────
    COMPRESS_ENABLED: bool = True
    COMPRESS_MIMETYPES: List[str] = [
        "application/json",
        "application/javascript",
        "text/css",
        "text/html",
        "text/plain"
    ]
    
    # ─── CACHE CONTROL ────────────────────────────────────────────
    CACHE_CONTROL_MAX_AGE: int = 3600
    CACHE_CONTROL_STALE_WHILE_REVALIDATE: int = 86400
    
    class Config:
        """Pydantic config for Settings."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        # Allow extra fields to prevent validation errors
        extra = "ignore"


# ─── CREATE SETTINGS INSTANCE ────────────────────────────────────

settings = Settings()
