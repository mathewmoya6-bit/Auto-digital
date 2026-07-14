"""
Application configuration
Auto-D Kenya Backend
"""

import os

from dotenv import load_dotenv


# Load .env for local development
load_dotenv()


class Config:

    # Flask
    SECRET_KEY = os.getenv(
        "FLASK_SECRET_KEY",
        "development-secret-key"
    )


    # Environment
    MPESA_ENV = os.getenv(
        "MPESA_ENV",
        "production"
    )


    # M-Pesa Daraja
    MPESA_CONSUMER_KEY = os.getenv(
        "MPESA_CONSUMER_KEY"
    )

    MPESA_CONSUMER_SECRET = os.getenv(
        "MPESA_CONSUMER_SECRET"
    )

    MPESA_SHORTCODE = os.getenv(
        "MPESA_SHORTCODE"
    )

    MPESA_PASSKEY = os.getenv(
        "MPESA_PASSKEY"
    )

    MPESA_CALLBACK_URL = os.getenv(
        "MPESA_CALLBACK_URL"
    )


    # Frontend
    FRONTEND_URL = os.getenv(
        "FRONTEND_URL",
        "https://auto-d.meipressgroup.com"
    )


    # Server
    PORT = int(
        os.getenv(
            "PORT",
            5000
        )
    )
