# app/core/middleware.py
# Auto-D Kenya - Middleware Setup
# ================================================================
# TYPE: CORE - FastAPI middleware configuration

import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and response times."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip logging for health checks to reduce noise
        if request.url.path.startswith("/health") or request.url.path.startswith("/ready") or request.url.path.startswith("/live"):
            return await call_next(request)
        
        # Skip logging for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        start_time = time.time()
        
        # Log request
        logger.info(f"→ {request.method} {request.url.path}")
        
        # Process request with error handling
        try:
            response = await call_next(request)
            
            # Log response time
            duration = time.time() - start_time
            logger.info(f"← {request.method} {request.url.path} → {response.status_code} ({duration:.3f}s)")
            
            return response
            
        except Exception as e:
            # Log detailed error information for debugging
            logger.error(f"❌ Unhandled error in request: {request.method} {request.url.path}")
            logger.error(f"   Error: {str(e)}")
            logger.error(f"   Headers: {dict(request.headers)}")
            logger.exception("Full traceback:")
            raise


def setup_middleware(app: FastAPI) -> None:
    """
    Configure all middleware for the application.
    
    ⚠️ IMPORTANT: CORS middleware is configured in main.py (FIRST middleware)
    ⚠️ All other middleware goes here (AFTER CORS)
    
    Args:
        app: FastAPI application instance
    """
    
    # ─── TRUSTED HOST MIDDLEWARE ──────────────────────────────────
    # TEMPORARILY DISABLED for debugging CORS issues
    # In production, re-enable with proper host list
    
    if settings.ENVIRONMENT == "production":
        # Temporarily allow all hosts for debugging
        # TODO: Restrict to specific domains after CORS is fixed
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"]  # Allow all hosts temporarily for debugging
        )
        logger.info("✅ TrustedHostMiddleware configured (ALLOW_ALL_HOSTS - DEBUGGING MODE)")
    else:
        logger.info("⏭️ TrustedHostMiddleware skipped (development environment)")
    
    # ─── REQUEST LOGGING MIDDLEWARE ──────────────────────────────
    app.add_middleware(RequestLoggingMiddleware)
    logger.info("✅ RequestLoggingMiddleware configured")
    
    # ─── STARTUP LOGGING ──────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("Middleware Configuration Summary:")
    logger.info(f"  Environment: {settings.ENVIRONMENT}")
    logger.info(f"  TrustedHostMiddleware: {'ENABLED (ALLOW_ALL)' if settings.ENVIRONMENT == 'production' else 'DISABLED'}")
    logger.info(f"  RequestLoggingMiddleware: ENABLED")
    logger.info("=" * 60)
