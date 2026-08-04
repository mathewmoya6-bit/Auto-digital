# Auto-D Kenya - Configuration Settings
# ================================================================

import json
from typing import List, Union

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

    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_JWT_SECRET: str = ""


    # ============================================================
    # SECURITY
    # ============================================================

    SECRET_KEY: str

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

    MPESA_TIMEOUT: int = 30
    MPESA_STK_TIMEOUT: int = 60


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


    # ============================================================
    # VALIDATION
    # ============================================================

    @model_validator(mode="after")
    def validate_security(self):

        if not self.SUPABASE_KEY:
            raise ValueError(
                "SUPABASE_KEY environment variable missing"
            )

        if not self.SECRET_KEY:
            raise ValueError(
                "SECRET_KEY environment variable missing"
            )

        return self


    # ============================================================
    # HELPERS
    # ============================================================

    def get_cors_origins(self) -> List[str]:

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


    def get_cors_methods(self):

        return [
            x.strip()
            for x in self.CORS_ALLOW_METHODS.split(",")
            if x.strip()
        ]


    def get_cors_headers(self):

        return [
            x.strip()
            for x in self.CORS_ALLOW_HEADERS.split(",")
            if x.strip()
        ]


settings = Settings()
