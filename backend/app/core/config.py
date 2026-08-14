# app/core/config.py
# ================================================================
# Auto-D Kenya - Configuration
# ================================================================

import json
import secrets
from datetime import timedelta
from typing import List, Optional

from pydantic_settings import BaseSettings
from pydantic import model_validator


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    """

    # ============================================================
    # APPLICATION
    # ============================================================

    PROJECT_NAME: str = "Auto-D Kenya"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Vehicle Valuation & Digital Services Platform"

    # Current environment
    ENVIRONMENT: str = "development"

    # API base path
    API_V1_PREFIX: str = "/api/v1"

    # Server port
    PORT: int = 8000

    # Debug mode (enables auto-reload)
    DEBUG: bool = False

    # Base URL of the API (used for generating links)
    API_BASE_URL: str = "http://localhost:8000"


    # ============================================================
    # SUPABASE
    # ============================================================

    # Supabase project URL
    SUPABASE_URL: Optional[str] = None

    # Supabase anonymous key (for client-side)
    SUPABASE_ANON_KEY: Optional[str] = None

    # Supabase service role key (for server-side/admin)
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None

    # Supabase JWT secret (used for signing tokens)
    SUPABASE_JWT_SECRET: Optional[str] = None


    # ============================================================
    # SECURITY
    # ============================================================

    # JWT secret key (falls back to SUPABASE_JWT_SECRET)
    SECRET_KEY: Optional[str] = None

    # JWT signing/verification algorithm used by app/core/security.py
    # for internal Auto-D tokens (create_access_token, create_refresh_token,
    # decode_token). Supabase-issued tokens use ES256/RS256 and are handled
    # separately in decode_token() via unverified-claims extraction — this
    # ALGORITHM setting only applies to internal HS256 tokens.
    ALGORITHM: str = "HS256"

    # Internal access/refresh token lifetimes, read directly (no getattr
    # fallback) by create_access_token / create_refresh_token in security.py.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = []
    CORS_ALLOW_METHODS: str = "*"
    CORS_ALLOW_HEADERS: str = "*"


    # ============================================================
    # RATE LIMITING
    # ============================================================

    # Read directly (no getattr fallback) by get_rate_limiter() in
    # app/core/dependencies.py.
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Used via getattr(...) in app/core/middleware.py — defined explicitly
    # here too so behavior doesn't silently depend on the getattr default.
    ENABLE_RATE_LIMITING: bool = True
    RATE_LIMIT_CALLS_PER_MINUTE: int = 60
    ALLOWED_HOSTS: List[str] = ["*"]


    # ============================================================
    # M-PESA
    # ============================================================

    # Enable M-Pesa
    MPESA_ENABLED: bool = True

    # Environment: sandbox | production
    MPESA_ENVIRONMENT: str = "sandbox"

    # API credentials
    MPESA_CONSUMER_KEY: Optional[str] = None
    MPESA_CONSUMER_SECRET: Optional[str] = None

    # Passkey (for STK Push)
    MPESA_PASSKEY: Optional[str] = None

    # Business shortcode
    MPESA_SHORTCODE: Optional[str] = None

    # Callback URL (STK Push response)
    MPESA_CALLBACK_URL: str = ""

    # Timeout in seconds
    MPESA_TIMEOUT: int = 30
    MPESA_STK_TIMEOUT: int = 60

    # Payment expiry in minutes
    PAYMENT_EXPIRY_MINUTES: int = 10

    # Callback secret (auto-generated)
    MPESA_CALLBACK_SECRET: Optional[str] = None


    # ============================================================
    # SERVICE ACCESS
    # ============================================================

    # Number of days a service purchase remains valid
    SERVICE_ACCESS_DAYS: int = 30


    # ============================================================
    # SCRAPER SETTINGS
    # ============================================================

    # Enable/disable external data scraping
    SCRAPER_ENABLED: bool = True

    # HTTP request timeout (seconds)
    SCRAPER_TIMEOUT: int = 30

    # Maximum concurrent scraper requests
    SCRAPER_MAX_CONCURRENT: int = 5

    # Default User-Agent
    SCRAPER_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/137.0 Safari/537.36"
    )


    # ============================================================
    # LOGGING
    # ============================================================

    # Logging level
    LOG_LEVEL: str = "INFO"

    # Standard log format
    LOG_FORMAT: str = (
        "%(asctime)s - %(name)s - "
        "%(levelname)s - %(message)s"
    )

    # Log incoming API requests
    LOG_REQUESTS: bool = True

    # Enable SQL logging (normally False)
    LOG_SQL: bool = False


    # ============================================================
    # API DOCUMENTATION
    # ============================================================

    # Enable OpenAPI documentation
    ENABLE_DOCS: bool = True

    # Swagger UI endpoint
    API_DOCS_URL: str = "/docs"

    # ReDoc endpoint
    API_REDOC_URL: str = "/redoc"

    # OpenAPI JSON endpoint
    API_OPENAPI_URL: str = "/openapi.json"


    # ============================================================
    # VALIDATION
    # ============================================================

    @model_validator(mode="after")
    def validate_settings(self):
        """
        Validate configuration after loading environment variables.
        """

        # --------------------------------------------------------
        # Normalize environment names
        # --------------------------------------------------------
        self.ENVIRONMENT = self.ENVIRONMENT.lower()
        self.MPESA_ENVIRONMENT = self.MPESA_ENVIRONMENT.lower()

        # --------------------------------------------------------
        # Supabase Configuration
        # --------------------------------------------------------
        if self.is_production:

            if not self.SUPABASE_URL:
                raise ValueError(
                    "SUPABASE_URL environment variable is required."
                )

            if not self.SUPABASE_SERVICE_ROLE_KEY:
                raise ValueError(
                    "SUPABASE_SERVICE_ROLE_KEY environment variable is required."
                )

        # --------------------------------------------------------
        # JWT Secret
        # --------------------------------------------------------
        if not self.SECRET_KEY:

            if self.SUPABASE_JWT_SECRET:
                self.SECRET_KEY = self.SUPABASE_JWT_SECRET

            elif self.is_production:
                raise ValueError(
                    "SECRET_KEY or SUPABASE_JWT_SECRET must be configured."
                )

            else:
                self.SECRET_KEY = secrets.token_urlsafe(32)

        # --------------------------------------------------------
        # M-Pesa Callback Secret
        # --------------------------------------------------------
        if not self.MPESA_CALLBACK_SECRET:
            self.MPESA_CALLBACK_SECRET = secrets.token_urlsafe(32)

        return self


    # ============================================================
    # HELPERS
    # ============================================================

    @property
    def mpesa_configured(self) -> bool:
        """
        Returns True when the minimum M-Pesa configuration
        required for STK Push is available.
        """
        return all(
            [
                self.MPESA_ENABLED,
                bool(self.MPESA_CONSUMER_KEY),
                bool(self.MPESA_CONSUMER_SECRET),
                bool(self.MPESA_PASSKEY),
                bool(self.MPESA_SHORTCODE),
            ]
        )

    @property
    def is_production(self) -> bool:
        """Return True when running in production."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Return True when running in development."""
        return self.ENVIRONMENT == "development"

    def get_cors_origins(self) -> List[str]:
        """
        Parse CORS origins supplied as either a JSON array
        or a comma-separated string.
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
        """Return allowed CORS methods."""
        return [
            method.strip()
            for method in self.CORS_ALLOW_METHODS.split(",")
            if method.strip()
        ]

    def get_cors_headers(self) -> List[str]:
        """Return allowed CORS headers."""
        return [
            header.strip()
            for header in self.CORS_ALLOW_HEADERS.split(",")
            if header.strip()
        ]

    def get_jwt_secret(self) -> str:
        """
        Return the JWT signing secret.
        """
        return self.SECRET_KEY or self.SUPABASE_JWT_SECRET

    def get_mpesa_base_url(self) -> str:
        """
        Return the Safaricom API endpoint.
        """
        if self.MPESA_ENVIRONMENT == "sandbox":
            return "https://sandbox.safaricom.co.ke"

        return "https://api.safaricom.co.ke"

    def get_callback_url(self) -> str:
        """
        Return the STK callback URL.
        """
        return self.MPESA_CALLBACK_URL.rstrip("/")

    def get_service_access_expiry(self) -> timedelta:
        """
        Return the default service access duration.
        """
        return timedelta(days=self.SERVICE_ACCESS_DAYS)

    def get_payment_expiry_minutes(self) -> int:
        """
        Return payment expiry time in minutes.
        """
        return self.PAYMENT_EXPIRY_MINUTES

    def get_mpesa_timeout(self) -> int:
        """
        Return M-Pesa API timeout.
        """
        return self.MPESA_TIMEOUT

    def get_stk_timeout(self) -> int:
        """
        Return STK Push timeout.
        """
        return self.MPESA_STK_TIMEOUT


# ================================================================
# SETTINGS INSTANCE
# ================================================================

settings = Settings()


# ================================================================
# EXPORTS
# ================================================================

__all__ = [
    "settings",
    "Settings",
]
