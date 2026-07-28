"""
Auto-D Kenya - FastAPI Application
Vehicle cost analysis and valuation system
"""

import os
import sys
import json
import logging
import traceback
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.database import supabase

# ─── Configure Logging FIRST ─────────────────────────────────────────
try:
    log_level_name = getattr(settings, "LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
except Exception:
    log_level = logging.INFO

log_format = getattr(settings, "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logging.basicConfig(
    level=log_level,
    format=log_format,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("🚀 Auto-D Kenya API Starting...")
logger.info(f"📋 Log Level: {logging.getLevelName(log_level)}")
logger.info("=" * 60)


# ─── Helper function to safely import routers ──────────────────────
def load_router(module_path: str, router_name: str = "router"):
    """
    Attempt to import a router from a module.
    If it fails, log the error and raise the exception to stop the app.
    """
    try:
        # Dynamically import the module
        module = __import__(module_path, fromlist=[router_name])
        router = getattr(module, router_name)
        logger.info(f"✅ Router loaded: {module_path}")
        return router
    except Exception as e:
        logger.error(f"❌ Failed to load router from {module_path}: {e}")
        logger.error(traceback.format_exc())
        # Re-raise the exception to stop the app
        raise


# ─── Import Routers using the helper ──────────────────────────────
logger.info("📦 Loading routers...")

try:
    # Load all routers. If ANY fail, the app will stop and show the error.
    auth_router = load_router("app.api.v1.auth")
    vehicles_router = load_router("app.api.v1.vehicles")
    valuation_router = load_router("app.api.v1.valuation")
    mileage_router = load_router("app.api.v1.mileage")
    ownership_router = load_router("app.api.v1.ownership")
    fuel_router = load_router("app.api.v1.fuel")
    running_cost_router = load_router("app.api.v1.running_cost")
    admin_router = load_router("app.api.v1.admin")
    reports_router = load_router("app.api.v1.reports")
    services_router = load_router("app.api.v1.services")
    price_alignment_router = load_router("app.api.v1.price_alignment")
    market_router = load_router("app.api.v1.market")
    scraper_router = load_router("app.api.v1.scraper")
    mpesa_router = load_router("app.api.v1.mpesa")
    
    logger.info("✅ All routers loaded successfully!")

except Exception as e:
    logger.critical(f"❌ Application failed to start due to router import error: {e}")
    # Re-raise to ensure the application exits with a non-zero code
    sys.exit(1)


# ─── Lifespan Context Manager ──────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # ... (keep your existing lifespan code as is) ...
    logger.info(f"🚀 Starting {settings.PROJECT_NAME}...")
    logger.info(f"📍 Environment: {settings.ENVIRONMENT}")
    # ... rest of your lifespan code ...
    yield
    logger.info(f"🛑 Shutting down {settings.PROJECT_NAME}...")


# ─── Initialize FastAPI App ────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.SWAGGER_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url=settings.API_DOCS_URL if settings.ENABLE_DOCS else None,
    redoc_url=settings.API_REDOC_URL if settings.ENABLE_DOCS else None,
    openapi_url=settings.API_OPENAPI_URL if settings.ENABLE_DOCS else None,
    contact={
        "name": settings.SWAGGER_CONTACT_NAME,
        "email": settings.SWAGGER_CONTACT_EMAIL,
    },
    license_info={
        "name": settings.SWAGGER_LICENSE_NAME,
    },
    lifespan=lifespan,
)


# ─── CORS Configuration ────────────────────────────────────────────
# ... (keep your existing CORS code as is) ...
cors_origins = settings.get_cors_origins() if hasattr(settings, 'get_cors_origins') else settings.BACKEND_CORS_ORIGINS
logger.info(f"🔒 Configuring CORS with origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["*"],
    max_age=settings.CORS_MAX_AGE,
)

logger.info("✅ CORS configured successfully")


# ─── Exception Handlers ────────────────────────────────────────────
# ... (keep your existing exception handlers as is) ...


# ─── Include Routers ───────────────────────────────────────────────
api_prefix = getattr(settings, "API_V1_PREFIX", "/api/v1")

# Register routers with their prefixes
app.include_router(auth_router, prefix=f"{api_prefix}/auth", tags=["Authentication"])
app.include_router(vehicles_router, prefix=f"{api_prefix}/vehicles", tags=["Vehicles"])
app.include_router(valuation_router, prefix=f"{api_prefix}/valuation", tags=["Valuation"])
app.include_router(mileage_router, prefix=f"{api_prefix}/mileage", tags=["Mileage"])
app.include_router(running_cost_router, prefix=f"{api_prefix}/running-cost", tags=["Running Cost"])
app.include_router(ownership_router, prefix=f"{api_prefix}/ownership", tags=["Ownership"])
app.include_router(fuel_router, prefix=f"{api_prefix}/fuel", tags=["Fuel"])
app.include_router(admin_router, prefix=f"{api_prefix}/admin", tags=["Admin"])
app.include_router(reports_router, prefix=f"{api_prefix}/reports", tags=["Reports"])
app.include_router(services_router, prefix=f"{api_prefix}/services", tags=["Service Prices"])
app.include_router(price_alignment_router, prefix=f"{api_prefix}/price", tags=["Price Alignment"])
app.include_router(market_router, prefix=f"{api_prefix}/market", tags=["Market Data"])
app.include_router(scraper_router, prefix=f"{api_prefix}/scraper", tags=["Market Scraper"])
app.include_router(mpesa_router, prefix=f"{api_prefix}/mpesa", tags=["M-Pesa"])

logger.info("✅ All routers registered successfully")
logger.info(f"📚 API Documentation available at {settings.API_DOCS_URL}")


# ─── Health Check Endpoints ──────────────────────────────────────
# ... (keep your existing health check endpoints as is) ...


# ─── Main Entry Point ─────────────────────────────────────────────
if __name__ == "__main__":
    # ... (keep your existing main entry point code as is) ...
    pass
