"""
Auto-D Kenya - FastAPI Application
Vehicle cost analysis and valuation system
"""

import os
import sys
import json
import logging
import traceback
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from importlib import import_module

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
    Attempt to import a router from a module using importlib.
    If it fails, log the error and raise a clear exception.
    """
    try:
        module = import_module(module_path)
        router = getattr(module, router_name)
        logger.info(f"✅ Router loaded: {module_path}")
        return router
    except Exception as e:
        logger.error(f"❌ Failed to load router from {module_path}: {e}")
        logger.error(traceback.format_exc())
        raise RuntimeError(f"Router loading failed for {module_path}: {e}")


# ─── Helper function to check table exists ──────────────────────────
def table_exists(table_name: str) -> bool:
    """Check if a Supabase table exists and has data"""
    try:
        response = supabase.table(table_name).select("count", count="exact").limit(1).execute()
        return True
    except Exception:
        return False


def get_table_count(table_name: str) -> int:
    """Get count of records in a Supabase table"""
    try:
        response = supabase.table(table_name).select("count", count="exact").limit(1).execute()
        return response.count if hasattr(response, 'count') else 0
    except Exception:
        return 0


# ─── Import Routers using the helper ──────────────────────────────
logger.info("📦 Loading routers...")

try:
    # Authentication - matches OpenAPI: /login, /register, /me, /logout
    auth_router = load_router("app.api.v1.auth")
    
    # Vehicles - matches OpenAPI: /makes, /models/{make_id}, /variants/{model_id}, /{variant_id}
    vehicles_router = load_router("app.api.v1.vehicles")
    
    # Valuation - matches OpenAPI: /variant/{variant_id}, /compare/{variant_id}
    valuation_router = load_router("app.api.v1.valuation")
    
    # Running Cost - matches OpenAPI: /ping
    running_cost_router = load_router("app.api.v1.running_cost")
    
    # Ownership - matches OpenAPI: /calculate
    ownership_router = load_router("app.api.v1.ownership")
    
    # Fuel - matches OpenAPI: /prices, /prices/{fuel_type}, /defaults
    fuel_router = load_router("app.api.v1.fuel")
    
    # Admin - matches OpenAPI: /fuel-prices, /dashboard
    admin_router = load_router("app.api.v1.admin")
    
    # Reports - matches OpenAPI: /valuation, /market-insights, /ownership-cost
    reports_router = load_router("app.api.v1.reports")
    
    # Service Prices - matches OpenAPI: /, /{service_id}, /types, /summary/pricing, etc.
    services_router = load_router("app.api.v1.services")
    
    # Price Alignment - matches OpenAPI: /history, /analyze, /align, /trend
    price_alignment_router = load_router("app.api.v1.price_alignment")
    
    # Market Data - matches OpenAPI: /insights, /scrape, /location/factors
    market_router = load_router("app.api.v1.market")
    
    # Market Scraper - matches OpenAPI: /run, /autochek, /jiji, /carapi, /status, /sources, /health
    scraper_router = load_router("app.api.v1.scraper")
    
    # M-Pesa - matches OpenAPI: /mpesa/health, /mpesa/services, /mpesa/stkpush, etc.
    mpesa_router = load_router("app.api.v1.mpesa")
    
    # ⚠️ IMPORTANT: These routers are NOT in the current OpenAPI spec
    # They may need to be removed or their endpoints moved to other routers
    # mileage_router = load_router("app.api.v1.mileage")  # No /mileage in OpenAPI
    
    logger.info("✅ All routers loaded successfully!")

except Exception as e:
    logger.critical(f"❌ Application failed to start: {e}")
    raise


# ─── Lifespan Context Manager ──────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    logger.info(f"🚀 Starting {settings.PROJECT_NAME}...")
    logger.info(f"📍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🔗 API Base URL: {settings.API_BASE_URL}")
    logger.info(f"📱 M-Pesa Environment: {getattr(settings, 'MPESA_ENV', 'sandbox')}")
    logger.info(f"📱 M-Pesa Shortcode: {getattr(settings, 'MPESA_SHORTCODE', '4095377')}")

    # Check Supabase connection
    try:
        response = supabase.table("vehicle_makes").select("count", count="exact").limit(1).execute()
        logger.info("✅ Supabase connection successful")
    except Exception as e:
        logger.error(f"❌ Supabase connection failed: {e}")
    
    # Check M-Pesa configuration
    mpesa_configured = bool(
        getattr(settings, 'MPESA_CONSUMER_KEY', '') and 
        getattr(settings, 'MPESA_CONSUMER_SECRET', '') and 
        getattr(settings, 'MPESA_PASSKEY', '')
    )
    if mpesa_configured:
        logger.info("✅ M-Pesa configuration loaded")
    else:
        logger.warning("⚠️ M-Pesa configuration incomplete - payment endpoints may not work")
    
    # Check tables using helper functions
    service_count = get_table_count("service_prices")
    if service_count > 0:
        logger.info(f"✅ Service prices table found: {service_count} services")
    else:
        logger.warning("⚠️ Service prices table not found or empty")
    
    market_exists = table_exists("market_prices")
    if market_exists:
        logger.info("✅ Market prices table found")
    else:
        logger.warning("⚠️ Market prices table not found")
    
    fuel_exists = table_exists("fuel_prices")
    if fuel_exists:
        logger.info("✅ Fuel prices table found")
    else:
        logger.warning("⚠️ Fuel prices table not found")
    
    logger.info("=" * 60)
    logger.info("✅ Application is ready to serve requests")
    logger.info("=" * 60)
    
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
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "message": "Validation error",
            "errors": exc.errors(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


# ─── Include Routers ───────────────────────────────────────────────
api_prefix = getattr(settings, "API_V1_PREFIX", "/api/v1")

# ═══════════════════════════════════════════════════════════════════
# ROUTER REGISTRATION - MATCHING OPENAPI SPEC
# ═══════════════════════════════════════════════════════════════════

# Authentication - /login, /register, /me, /logout
app.include_router(auth_router, prefix=api_prefix, tags=["Authentication"])

# Vehicles - /makes, /models/{make_id}, /variants/{model_id}, /{variant_id}
app.include_router(vehicles_router, prefix=api_prefix, tags=["Vehicles"])

# Running Cost - /ping
app.include_router(running_cost_router, prefix=api_prefix, tags=["Running Cost"])

# Ownership - /calculate
app.include_router(ownership_router, prefix=api_prefix, tags=["Ownership"])

# Valuation - /variant/{variant_id}, /compare/{variant_id}
app.include_router(valuation_router, prefix=api_prefix, tags=["Valuation"])

# Price Alignment - /history, /analyze, /align, /trend
app.include_router(price_alignment_router, prefix=api_prefix, tags=["Price Alignment"])

# Fuel - /prices, /prices/{fuel_type}, /defaults
app.include_router(fuel_router, prefix=api_prefix, tags=["Fuel"])

# Admin - /fuel-prices, /dashboard
app.include_router(admin_router, prefix=api_prefix, tags=["Admin"])

# Reports - /valuation, /market-insights, /ownership-cost
app.include_router(reports_router, prefix=api_prefix, tags=["Reports"])

# Service Prices - /, /{service_id}, /types, /summary/pricing, /comparison/types, /price-range, /bulk
app.include_router(services_router, prefix=api_prefix, tags=["Service Prices"])

# Market Data - /insights, /scrape, /location/factors
app.include_router(market_router, prefix=api_prefix, tags=["Market Data"])

# Market Scraper - /run, /autochek, /jiji, /carapi, /status, /sources, /health
app.include_router(scraper_router, prefix=api_prefix, tags=["Market Scraper"])

# M-Pesa - /mpesa/health, /mpesa/shortcode, /mpesa/services, /mpesa/stkpush, etc.
app.include_router(mpesa_router, prefix=api_prefix, tags=["M-Pesa"])

logger.info("✅ All routers registered successfully")
logger.info(f"📚 API Documentation available at {settings.API_DOCS_URL}")


# ─── Health Check Endpoints ──────────────────────────────────────
@app.get("/health")
@app.get("/api/health")
async def health_check():
    """
    Health check endpoint - lightweight, doesn't hit database.
    This should be fast and always return quickly.
    """
    mpesa_configured = all([
        getattr(settings, "MPESA_CONSUMER_KEY", ""),
        getattr(settings, "MPESA_CONSUMER_SECRET", ""),
        getattr(settings, "MPESA_PASSKEY", "")
    ])
    
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mpesa": "configured" if mpesa_configured else "not_configured",
        "mpesa_shortcode": getattr(settings, "MPESA_SHORTCODE", "4095377"),
        "environment": getattr(settings, "ENVIRONMENT", "production"),
        "version": getattr(settings, "API_VERSION", "4.0.0"),
        "docs_enabled": settings.ENABLE_DOCS,
        "docs_url": settings.API_DOCS_URL if settings.ENABLE_DOCS else None,
    }


@app.get("/ready")
@app.get("/api/ready")
async def readiness_check():
    """
    Readiness check endpoint - checks database connectivity.
    """
    supabase_status = "connected"
    service_prices_exist = False
    service_count = 0
    
    try:
        response = supabase.table("vehicle_makes").select("count", count="exact").limit(1).execute()
    except Exception as e:
        supabase_status = f"error: {str(e)}"
        logger.error(f"Supabase readiness check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "reason": "Database connection failed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    try:
        response = supabase.table("service_prices").select("count", count="exact").limit(1).execute()
        service_prices_exist = True
        service_count = response.count if hasattr(response, 'count') else 0
    except Exception:
        pass
    
    return {
        "status": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "supabase": supabase_status,
        "service_prices_table": "exists" if service_prices_exist else "not_found",
        "service_count": service_count,
    }


@app.get("/live")
@app.get("/api/live")
async def liveness_check():
    """Liveness check endpoint - simple and fast"""
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/ping")
async def ping():
    """Simple ping endpoint for testing connectivity"""
    return {
        "pong": datetime.now(timezone.utc).isoformat(),
        "status": "alive"
    }


@app.get("/")
async def root():
    """Root endpoint with API information"""
    mpesa_configured = all([
        getattr(settings, "MPESA_CONSUMER_KEY", ""),
        getattr(settings, "MPESA_CONSUMER_SECRET", ""),
        getattr(settings, "MPESA_PASSKEY", "")
    ])
    
    return {
        "name": getattr(settings, "PROJECT_NAME", "Auto-D Kenya API"),
        "version": getattr(settings, "API_VERSION", "4.0.0"),
        "environment": getattr(settings, "ENVIRONMENT", "production"),
        "status": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "documentation": settings.API_DOCS_URL if settings.ENABLE_DOCS else "disabled",
        "api_prefix": getattr(settings, "API_V1_PREFIX", "/api/v1"),
        "features": {
            "mpesa": getattr(settings, "ENABLE_MPESA", True),
            "mpesa_shortcode": getattr(settings, "MPESA_SHORTCODE", "4095377"),
            "mpesa_configured": mpesa_configured,
            "price_alignment": True,
            "market_data": True,
            "market_scraper": True,
            "service_prices": True,
            "docs": settings.ENABLE_DOCS
        },
        "endpoints": {
            "auth": {
                "login": f"{api_prefix}/login",
                "register": f"{api_prefix}/register",
                "me": f"{api_prefix}/me",
                "logout": f"{api_prefix}/logout"
            },
            "vehicles": {
                "makes": f"{api_prefix}/makes",
                "models": f"{api_prefix}/models/{{make_id}}",
                "variants": f"{api_prefix}/variants/{{model_id}}",
                "vehicle": f"{api_prefix}/{{variant_id}}"
            },
            "valuation": {
                "variant": f"{api_prefix}/variant/{{variant_id}}",
                "compare": f"{api_prefix}/compare/{{variant_id}}"
            },
            "running_cost": {
                "ping": f"{api_prefix}/ping"
            },
            "ownership": {
                "calculate": f"{api_prefix}/calculate"
            },
            "fuel": {
                "prices": f"{api_prefix}/prices",
                "price": f"{api_prefix}/prices/{{fuel_type}}",
                "defaults": f"{api_prefix}/defaults"
            },
            "mpesa": {
                "health": f"{api_prefix}/mpesa/health",
                "services": f"{api_prefix}/mpesa/services",
                "user_services": f"{api_prefix}/mpesa/user/services",
                "stkpush": f"{api_prefix}/mpesa/stkpush",
                "status": f"{api_prefix}/mpesa/status/{{checkout_request_id}}",
                "confirm": f"{api_prefix}/mpesa/confirm/{{checkout_request_id}}",
                "payments": f"{api_prefix}/mpesa/payments"
            }
        }
    }


@app.get("/info")
async def info():
    """
    Get application information.
    Sensitive information like Supabase URL is not exposed.
    """
    mpesa_configured = all([
        getattr(settings, "MPESA_CONSUMER_KEY", ""),
        getattr(settings, "MPESA_CONSUMER_SECRET", ""),
        getattr(settings, "MPESA_PASSKEY", "")
    ])
    
    return {
        "name": getattr(settings, "PROJECT_NAME", "Auto-D Kenya API"),
        "version": getattr(settings, "API_VERSION", "4.0.0"),
        "environment": getattr(settings, "ENVIRONMENT", "production"),
        "docs_enabled": settings.ENABLE_DOCS,
        "docs_url": settings.API_DOCS_URL if settings.ENABLE_DOCS else None,
        "features": {
            "mpesa": getattr(settings, "ENABLE_MPESA", True),
            "mpesa_shortcode": getattr(settings, "MPESA_SHORTCODE", "4095377"),
            "mpesa_environment": getattr(settings, "MPESA_ENV", "sandbox"),
            "mpesa_configured": mpesa_configured,
            "price_alignment": True,
            "market_data": True,
            "market_scraper": True,
            "service_prices": True,
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ─── Main Entry Point ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    debug = getattr(settings, "DEBUG", False)
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info("=" * 60)
    logger.info(f"🚀 Starting server on {host}:{port}")
    logger.info(f"🐛 Debug mode: {debug}")
    logger.info(f"📱 M-Pesa Shortcode: {getattr(settings, 'MPESA_SHORTCODE', '4095377')}")
    logger.info(f"📡 API Base URL: {getattr(settings, 'API_BASE_URL', 'http://localhost:' + str(port))}")
    logger.info(f"📚 Docs enabled: {settings.ENABLE_DOCS}")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level=log_level_name.lower() if isinstance(log_level_name, str) else "info",
    )
