# app/core/config.py
# Auto-D Kenya - Configuration Settings
# ================================================================
# TYPE: CORE - Configuration Management

import json
import os
from typing import List, Union

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

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
    DESCRIPTION: str = "Vehicle cost analysis and valuation system for Kenya"

    API_V1_PREFIX: str = "/api/v1"
    API_BASE_URL: str = os.getenv(
        "API_BASE_URL",
        "https://auto-digital.onrender.com",
    )

    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    DEBUG: bool = False
    PORT: int = 10000

    # ============================================================
    # SUPABASE
    # ============================================================

    SUPABASE_URL: str = os.getenv(
        "SUPABASE_URL",
        "https://xgkdbithhlvoqjnqvfmj.supabase.co",
    )

    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    SUPABASE_JWT_SECRET: str = os.getenv(
        "SUPABASE_JWT_SECRET",
        "",
    )

    # ============================================================
    # SECURITY
    # ============================================================

    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "change-me-in-production-use-strong-key",
    )

    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ============================================================
    # CORS
    # ============================================================

    BACKEND_CORS_ORIGINS: Union[str, List[str]] = os.getenv(
        "CORS_ORIGINS",
        ",".join(
            [
                "https://auto-d.meipressgroup.com",
                "https://auto-digital.onrender.com",
                "http://localhost:3000",
                "http://localhost:8000",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8000",
            ]
        ),
    )

    CORS_ALLOW_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS,PATCH"

    CORS_ALLOW_HEADERS: str = (
        "Authorization,Content-Type,Accept,Origin,X-Requested-With"
    )

    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_MAX_AGE: int = 86400

    # ============================================================
    # M-PESA
    # ============================================================

    MPESA_CONSUMER_KEY: str = os.getenv("MPESA_CONSUMER_KEY", "")
    MPESA_CONSUMER_SECRET: str = os.getenv("MPESA_CONSUMER_SECRET", "")
    MPESA_PASSKEY: str = os.getenv("MPESA_PASSKEY", "")
    MPESA_SHORTCODE: str = os.getenv("MPESA_SHORTCODE", "4095377")

    MPESA_ENVIRONMENT: str = os.getenv(
        "MPESA_ENVIRONMENT",
        "production",
    )

    MPESA_BASE_URL: str = os.getenv(
        "MPESA_BASE_URL",
        "https://api.safaricom.co.ke",
    )

    MPESA_CALLBACK_URL: str = os.getenv(
        "MPESA_CALLBACK_URL",
        "https://auto-digital.onrender.com/api/v1/mpesa/callback",
    )

    # Used to verify callback signatures (optional)
    MPESA_CALLBACK_SECRET: str = os.getenv(
        "MPESA_CALLBACK_SECRET",
        "",
    )

    MPESA_TIMEOUT: int = int(
        os.getenv("MPESA_TIMEOUT", "30")
    )

    MPESA_STK_TIMEOUT: int = int(
        os.getenv("MPESA_STK_TIMEOUT", "60")
    )

    MPESA_CACHE_TTL: int = int(
        os.getenv("MPESA_CACHE_TTL", "3500")
    )

    # Optional B2C/B2B settings
    MPESA_INITIATOR_NAME: str = os.getenv(
        "MPESA_INITIATOR_NAME",
        "",
    )

    MPESA_SECURITY_CREDENTIAL: str = os.getenv(
        "MPESA_SECURITY_CREDENTIAL",
        "",
    )

    MPESA_QUEUE_TIMEOUT_URL: str = os.getenv(
        "MPESA_QUEUE_TIMEOUT_URL",
        "",
    )

    MPESA_RESULT_URL: str = os.getenv(
        "MPESA_RESULT_URL",
        "",
    )

    # ============================================================
    # DEFAULT VALUES
    # ============================================================

    DEFAULT_FUEL_PRICE_PETROL: float = 214.03
    DEFAULT_FUEL_PRICE_DIESEL: float = 222.86
    DEFAULT_FUEL_PRICE_ELECTRIC: float = 30.00

    DEFAULT_ANNUAL_MILEAGE: int = 20000
    DEFAULT_DEPRECIATION_RATE: float = 0.15
    DEFAULT_INSURANCE_RATE: float = 0.045

    # ============================================================
    # LOGGING
    # ============================================================

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # ============================================================
    # HELPERS
    # ============================================================

    def get_cors_origins(self) -> List[str]:
        """Return CORS origins as a list."""

        origins = self.BACKEND_CORS_ORIGINS

        if isinstance(origins, list):
            return [o.strip() for o in origins if o.strip()]

        if isinstance(origins, str):
            try:
                parsed = json.loads(origins)

                if isinstance(parsed, list):
                    return [o.strip() for o in parsed if o.strip()]

            except json.JSONDecodeError:
                pass

            return [
                o.strip()
                for o in origins.split(",")
                if o.strip()
            ]

        return ["https://auto-d.meipressgroup.com"]

    def get_cors_methods(self) -> List[str]:
        return [
            method.strip()
            for method in self.CORS_ALLOW_METHODS.split(",")
            if method.strip()
        ]

    def get_cors_headers(self) -> List[str]:
        return [
            header.strip()
            for header in self.CORS_ALLOW_HEADERS.split(",")
            if header.strip()
        ]


settings = Settings()
