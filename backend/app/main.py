# backend/app/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import logging
import os
from typing import List

from app.core.config import settings
from app.core.database import supabase_client
from app.api.v1 import auth, vehicles, valuation, mileage, ownership, fuel, admin, reports

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.ENVIRONMENT == "production" else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events"""
    logger.info(f"Starting Auto-D API in {settings.ENVIRONMENT} mode...")
    logger.info(f"Supabase URL: {settings.SUPABASE_URL}")
    yield
    logger.info("Shutting down Auto-D API...")

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Vehicle cost analysis and valuation system",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(vehicles.router, prefix="/api/v1/vehicles", tags=["Vehicles"])
app.include_router(valuation.router, prefix="/api/v1/valuation", tags=["Valuation"])
app.include_router(mileage.router, prefix="/api/v1/mileage", tags=["Mileage"])
app.include_router(ownership.router, prefix="/api/v1/ownership", tags=["Ownership"])
app.include_router(fuel.router, prefix="/api/v1/fuel", tags=["Fuel"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])

@app.get("/")
async def root():
    return {
        "message": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "documentation": "/docs" if settings.DEBUG else "Documentation not available in production"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=port,
        reload=settings.DEBUG
    )
