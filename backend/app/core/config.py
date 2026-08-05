# app/core/config.py
# ================================================================
# Auto-D Kenya - Configuration Settings
# ================================================================

import json
import secrets
from datetime import timedelta
from typing import List, Optional, Union

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Global application settings.

    Values are loaded from environment variables and .env.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ============================================================
    # APPLICATION
    # ============================================================

    PROJECT_NAME: str = "Auto-D Kenya API"

    VERSION: str = "2.0.0"

    DESCRIPTION: str = (
        "Vehicle Valuation, Ownership Verification, "
        "Mileage Verification and Running Cost Platform"
    )

    API_V1_PREFIX: str = "/api/v1"

    API_BASE_URL: str = "https://auto-digital.onrender.com"

    ENVIRONMENT: str = "production"

    DEBUG: bool = False

    PORT: int = 10000

    # ============================================================
    # SUPABASE
    # ============================================================

    SUPABASE_URL: str = ""

    SUPABASE_KEY: str = ""

    SUPABASE_SERVICE_ROLE_KEY: str = ""

    SUPABASE_JWT_SECRET: str = ""

    # ============================================================
    # SECURITY
    # ============================================================

    SECRET_KEY: Optional[str] = None

    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    PASSWORD_MIN_LENGTH: int = 8

    # ============================================================
    # API SECURITY
    # ============================================================

    PUBLIC_API_KEY: str = ""

    INTERNAL_API_KEY: str = ""

    API_REQUEST_TIMEOUT: int = 30

    # ============================================================
    # CORS
    # ============================================================

    BACKEND_CORS_ORIGINS: Union[str, List[str]] = (
        "https://auto-d.meipressgroup.com,"
        "https://auto-digital.onrender.com,"
        "http://localhost:3000,"
        "http://localhost:5173,"
        "http://localhost:8000"
    )

    CORS_ALLOW_METHODS: str = (
        "GET,POST,PUT,DELETE,PATCH,OPTIONS"
    )

    CORS_ALLOW_HEADERS: str = (
        "Authorization,"
        "Content-Type,"
        "Accept,"
        "Origin,"
        "X-Requested-With"
    )

    CORS_ALLOW_CREDENTIALS: bool = True

    # ============================================================
    # M-PESA CONFIGURATION
    # ============================================================

    # Master switch
    MPESA_ENABLED: bool = True

    # Environment
    MPESA_ENVIRONMENT: str = "production"

    # API Credentials
    MPESA_CONSUMER_KEY: str = ""
    MPESA_CONSUMER_SECRET: str = ""
    MPESA_PASSKEY: str = ""

    # Business Details
    MPESA_SHORTCODE: str = "4095377"
    MPESA_TILL_NUMBER: str = ""
    MPESA_INITIATOR_NAME: str = ""
    MPESA_INITIATOR_PASSWORD: str = ""

    # API URLs
    MPESA_BASE_URL: str = "https://api.safaricom.co.ke"

    MPESA_CALLBACK_URL: str = (
        "https://auto-digital.onrender.com"
        "/api/v1/mpesa/callback"
    )

    MPESA_RESULT_URL: str = ""

    MPESA_QUEUE_TIMEOUT_URL: str = ""

    MPESA_CALLBACK_SECRET: str = ""

    MPESA_API_VERSION: str = "v1"

    # Timeouts
    MPESA_TIMEOUT: int = 30
    MPESA_STK_TIMEOUT: int = 60
    MPESA_ACCESS_TOKEN_CACHE_MINUTES: int = 50

    # Payment Behaviour
    PAYMENT_EXPIRY_MINUTES: int = 30

    SERVICE_ACCESS_DAYS: int = 365

    # Retry Settings
    MPESA_MAX_RETRIES: int = 3
    MPESA_RETRY_DELAY_SECONDS: int = 5

    # ============================================================
    # RATE LIMITING
    # ============================================================

    RATE_LIMIT_REQUESTS: int = 5

    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ============================================================
    # DEFAULT VEHICLE VALUES
    # ============================================================

    DEFAULT_FUEL_PRICE_PETROL: float = 214.03

    DEFAULT_FUEL_PRICE_DIESEL: float = 222.86

    DEFAULT_FUEL_PRICE_ELECTRIC: float = 30.00

    DEFAULT_ANNUAL_MILEAGE: int = 20000

    DEFAULT_DEPRECIATION_RATE: float = 0.15

    DEFAULT_INSURANCE_RATE: float = 0.045

    # ============================================================
    # VALUATION SETTINGS
    # ============================================================

    DEFAULT_MARKET_VARIANCE: float = 0.05

    DEFAULT_MAX_VEHICLE_AGE: int = 30

    DEFAULT_MINIMUM_VALUE: float = 50000.0

    # ============================================================
    # SCRAPER SETTINGS
    # ============================================================

    SCRAPER_ENABLED: bool = True

    SCRAPER_TIMEOUT: int = 30

    SCRAPER_MAX_CONCURRENT: int = 5

    SCRAPER_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/137.0 Safari/537.36"
    )

    # ============================================================
    # LOGGING
    # ============================================================

    LOG_LEVEL: str = "INFO"

    LOG_FORMAT: str = (
        "%(asctime)s - %(name)s - "
        "%(levelname)s - %(message)s"
    )

    LOG_REQUESTS: bool = True

    LOG_SQL: bool = False

    # ============================================================
    # API DOCUMENTATION
    # ============================================================

    ENABLE_DOCS: bool = True

    API_DOCS_URL: str = "/docs"

    API_REDOC_URL: str = "/redoc"

    API_OPENAPI_URL: str = "/openapi.json"

    # ============================================================
    # VALIDATION
    # ============================================================

    @model_validator(mode="after")
    def validate_settings(self):
        """
        Validate configuration after loading from the environment.
        """

        # --------------------------------------------------------
        # Supabase
        # --------------------------------------------------------
        if self.ENVIRONMENT.lower() == "production":
            if not self.SUPABASE_URL:
                raise ValueError("SUPABASE_URL environment variable is required.")

            if not self.SUPABASE_KEY:
                raise ValueError("SUPABASE_KEY environment variable is required.")

        # --------------------------------------------------------
        # JWT Secret
        # --------------------------------------------------------
        if not self.SECRET_KEY:
            if self.SUPABASE_JWT_SECRET:
                self.SECRET_KEY = self.SUPABASE_JWT_SECRET
            elif self.ENVIRONMENT.lower() == "production":
                raise ValueError(
                    "SECRET_KEY or SUPABASE_JWT_SECRET must be configured."
                )
            else:
                self.SECRET_KEY = secrets.token_urlsafe(32)

        # --------------------------------------------------------
        # Callback Secret
        # --------------------------------------------------------
        if not self.MPESA_CALLBACK_SECRET:
            self.MPESA_CALLBACK_SECRET = secrets.token_urlsafe(32)

        # --------------------------------------------------------
        # Normalize Environment
        # --------------------------------------------------------
        self.ENVIRONMENT = self.ENVIRONMENT.lower()
        self.MPESA_ENVIRONMENT = self.MPESA_ENVIRONMENT.lower()

        return self

    # ============================================================
    # HELPERS
    # ============================================================

    @property
    def mpesa_configured(self) -> bool:
        """
        Returns True if the minimum configuration required to use
        M-Pesa exists.
        """
        return (
            self.MPESA_ENABLED
            and bool(self.MPESA_CONSUMER_KEY)
            and bool(self.MPESA_CONSUMER_SECRET)
            and bool(self.MPESA_PASSKEY)
            and bool(self.MPESA_SHORTCODE)
        )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    def get_cors_origins(self) -> List[str]:
        """
        Parse CORS origins whether supplied as JSON or comma-separated text.
        """
        origins = self.BACKEND_CORS_ORIGINS

        if isinstance(origins, list):
            return origins

        try:
            parsed = json.loads(origins)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass

        return [
            origin.strip()
            for origin in origins.split(",")
            if origin.strip()
        ]

    def get_cors_methods(self) -> List[str]:
        """
        Parse CORS allowed methods.
        """
        return [
            method.strip()
            for method in self.CORS_ALLOW_METHODS.split(",")
            if method.strip()
        ]

    def get_cors_headers(self) -> List[str]:
        """
        Parse CORS allowed headers.
        """
        return [
            header.strip()
            for header in self.CORS_ALLOW_HEADERS.split(",")
            if header.strip()
        ]

    def get_jwt_secret(self) -> str:
        """
        Returns the JWT signing secret.
        """
        return self.SECRET_KEY or self.SUPABASE_JWT_SECRET or ""

    def get_mpesa_base_url(self) -> str:
        """
        Returns the appropriate Safaricom API endpoint.
        """
        if self.MPESA_ENVIRONMENT == "sandbox":
            return "https://sandbox.safaricom.co.ke"

        return "https://api.safaricom.co.ke"

    def get_callback_url(self) -> str:
        """
        Returns the callback URL used for STK Push.
        """
        return self.MPESA_CALLBACK_URL.rstrip("/")

    def get_service_access_expiry(self) -> timedelta:
        """
        Default service access duration after successful payment.
        """
        return timedelta(days=self.SERVICE_ACCESS_DAYS)

    def get_payment_expiry_minutes(self) -> int:
        """
        Returns the payment expiry time in minutes.
        """
        return self.PAYMENT_EXPIRY_MINUTES

    def get_mpesa_timeout(self) -> int:
        """
        Returns the M-Pesa API timeout in seconds.
        """
        return self.MPESA_TIMEOUT

    def get_stk_timeout(self) -> int:
        """
        Returns the STK Push timeout in seconds.
        """
        return self.MPESA_STK_TIMEOUT


# ================================================================
# SETTINGS INSTANCE
# ================================================================

settings = Settings()
