# Auto-D Kenya - Configuration Settings
# ================================================================

import json
import secrets
from typing import List, Union, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration.
    Values are loaded from environment variables.
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
    VERSION: str = "1.0.0"
    DESCRIPTION: str = (
        "Vehicle cost analysis and valuation system for Kenya"
    )

    API_V1_PREFIX: str = "/api/v1"

    API_BASE_URL: str = (
        "https://auto-digital.onrender.com"
    )

    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    PORT: int = 10000


    # ============================================================
    # SUPABASE
    # ============================================================

    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""


    # ============================================================
    # SECURITY
    # ============================================================

    SECRET_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30


    # ============================================================
    # CORS
    # ============================================================

    BACKEND_CORS_ORIGINS: Union[str, List[str]] = (
        "https://auto-d.meipressgroup.com,"
        "https://auto-digital.onrender.com,"
        "http://localhost:3000,"
        "http://localhost:8000"
    )

    CORS_ALLOW_METHODS: str = (
        "GET,POST,PUT,DELETE,OPTIONS,PATCH"
    )

    CORS_ALLOW_HEADERS: str = (
        "Authorization,Content-Type,Accept,Origin"
    )

    CORS_ALLOW_CREDENTIALS: bool = True


    # ============================================================
    # MPESA
    # ============================================================

    MPESA_CONSUMER_KEY: str = ""
    MPESA_CONSUMER_SECRET: str = ""
    MPESA_PASSKEY: str = ""

    MPESA_SHORTCODE: str = "4095377"

    MPESA_ENVIRONMENT: str = "production"

    MPESA_BASE_URL: str = (
        "https://api.safaricom.co.ke"
    )

    MPESA_CALLBACK_URL: str = (
        "https://auto-digital.onrender.com"
        "/api/v1/mpesa/callback"
    )

    # ─── M-Pesa Callback Secret ──────────────────────────────────
    MPESA_CALLBACK_SECRET: str = ""
    
    # ─── M-Pesa Timeouts ─────────────────────────────────────────
    MPESA_TIMEOUT: int = 30
    MPESA_STK_TIMEOUT: int = 60
    
    # ─── M-Pesa API Version ──────────────────────────────────────
    MPESA_API_VERSION: str = "v1"


    # ============================================================
    # DEFAULT VEHICLE VALUES
    # ============================================================

    DEFAULT_FUEL_PRICE_PETROL: float = 214.03
    DEFAULT_FUEL_PRICE_DIESEL: float = 222.86
    DEFAULT_FUEL_PRICE_ELECTRIC: float = 30.0

    DEFAULT_ANNUAL_MILEAGE: int = 20000

    DEFAULT_DEPRECIATION_RATE: float = 0.15

    DEFAULT_INSURANCE_RATE: float = 0.045


    # ============================================================
    # LOGGING
    # ============================================================

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


    # ============================================================
    # DOCUMENTATION
    # ============================================================

    ENABLE_DOCS: bool = True
    API_DOCS_URL: str = "/docs"
    API_REDOC_URL: str = "/redoc"
    API_OPENAPI_URL: str = "/openapi.json"


    # ============================================================
    # VALIDATION
    # ============================================================

    @model_validator(mode="after")
    def validate_security(self):
        """Validate required security settings."""
        
        # ─── Validate Supabase credentials ──────────────────────
        if not self.SUPABASE_KEY and self.ENVIRONMENT == "production":
            raise ValueError(
                "SUPABASE_KEY environment variable missing"
            )
        
        if not self.SUPABASE_URL and self.ENVIRONMENT == "production":
            raise ValueError(
                "SUPABASE_URL environment variable missing"
            )
        
        # ─── Use SUPABASE_JWT_SECRET as fallback for SECRET_KEY ──
        if not self.SECRET_KEY:
            if self.SUPABASE_JWT_SECRET:
                self.SECRET_KEY = self.SUPABASE_JWT_SECRET
                print("✅ Using SUPABASE_JWT_SECRET as SECRET_KEY")
            elif self.ENVIRONMENT == "production":
                raise ValueError(
                    "Neither SECRET_KEY nor SUPABASE_JWT_SECRET is set"
                )
            else:
                # Generate a temporary key for development
                self.SECRET_KEY = secrets.token_urlsafe(32)
                print("⚠️  WARNING: Generated temporary SECRET_KEY for development")
        
        # ─── M-Pesa validation (warning only) ────────────────────
        if self.ENVIRONMENT == "production":
            if not self.MPESA_CONSUMER_KEY or not self.MPESA_CONSUMER_SECRET:
                print("⚠️  WARNING: M-Pesa credentials not fully configured")
            
            if not self.MPESA_CALLBACK_SECRET:
                print("⚠️  WARNING: MPESA_CALLBACK_SECRET not set - using default")
                # Generate a default secret
                self.MPESA_CALLBACK_SECRET = secrets.token_urlsafe(32)

        return self


    # ============================================================
    # HELPERS
    # ============================================================

    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from string or list."""
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
            item.strip()
            for item in origins.split(",")
            if item.strip()
        ]


    def get_cors_methods(self) -> List[str]:
        """Parse CORS methods from string."""
        return [
            x.strip()
            for x in self.CORS_ALLOW_METHODS.split(",")
            if x.strip()
        ]


    def get_cors_headers(self) -> List[str]:
        """Parse CORS headers from string."""
        return [
            x.strip()
            for x in self.CORS_ALLOW_HEADERS.split(",")
            if x.strip()
        ]


    def get_jwt_secret(self) -> str:
        """Get the JWT secret to use."""
        if self.SUPABASE_JWT_SECRET:
            return self.SUPABASE_JWT_SECRET
        return self.SECRET_KEY or ""


# ─── Create settings instance ──────────────────────────────────────
settings = Settings()
