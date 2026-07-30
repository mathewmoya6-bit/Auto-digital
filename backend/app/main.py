# app/main.py
# Auto-D Kenya - Application Entry Point
# ================================================================
# TYPE: ROUTES - Main application entry point

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import init_db
from app.core.middleware import setup_middleware
from app.core.exceptions import setup_exception_handlers

# Import module routers
from app.modules.auth.router import router as auth_router
from app.modules.vehicles.router import router as vehicles_router
from app.modules.valuation.router import router as valuation_router
from app.modules.mpesa.router import router as mpesa_router
from app.modules.reports.router import router as reports_router
from app.modules.scraper.router import router as scraper_router
from app.modules.market.router import router as market_router

# ─── LOGGING ──────────────────────────────────────────────────────

logger = logging.getLogger(__name__)


# ─── LIFESPAN MANAGER ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"{settings.PROJECT_NAME} starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"API Base URL: {settings.API_BASE_URL}")
    
    # Initialize database
    await init_db()
    logger.info("✅ Database initialized")
    
    yield
    
    # Shutdown
    logger.info(f"{settings.PROJECT_NAME} shutting down...")


# ─── CREATE APP ──────────────────────────────────────────────────

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan
)


# ─── MIDDLEWARE ──────────────────────────────────────────────────

setup_middleware(app)


# ─── EXCEPTION HANDLERS ──────────────────────────────────────────

setup_exception_handlers(app)


# ─── ROUTES ──────────────────────────────────────────────────────

app.include_router(auth_router, prefix=settings.API_V1_PREFIX, tags=["Authentication"])
app.include_router(vehicles_router, prefix=settings.API_V1_PREFIX, tags=["Vehicles"])
app.include_router(valuation_router, prefix=settings.API_V1_PREFIX, tags=["Valuation"])
app.include_router(mpesa_router, prefix=settings.API_V1_PREFIX, tags=["M-Pesa"])
app.include_router(reports_router, prefix=settings.API_V1_PREFIX, tags=["Reports"])
app.include_router(scraper_router, prefix=settings.API_V1_PREFIX, tags=["Scraper"])
app.include_router(market_router, prefix=settings.API_V1_PREFIX, tags=["Market"])


# ─── HEALTH CHECK ────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION,
        "service": settings.PROJECT_NAME
    }


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Readiness check endpoint."""
    return {"status": "ready"}


@app.get("/live", tags=["Health"])
async def liveness_check():
    """Liveness check endpoint."""
    return {"status": "alive"}


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "api_prefix": settings.API_V1_PREFIX,
        "base_url": settings.API_BASE_URL
    }


# ─── STARTUP ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )
