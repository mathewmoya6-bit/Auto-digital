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
            logger.exception(f"Unhandled error in request: {request.method} {request.url.path}")
            raise


def setup_middleware(app: FastAPI) -> None:
    """
    Configure all middleware for the application.
    
    ⚠️ IMPORTANT: CORS middleware is configured in main.py (FIRST middleware)
    ⚠️ All other middleware goes here (AFTER CORS)
    
    Args:
        app: FastAPI application instance
    """
    
    # Trusted Host Middleware (production only)
    if settings.ENVIRONMENT == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[
                "auto-digital.meipressgroup.com",
                "auto-d.meipressgroup.com",
                "auto-digital.onrender.com",
                "auto-d.onrender.com",
                "localhost",
                "127.0.0.1"
            ]
        )
        logger.info("✅ TrustedHostMiddleware configured")
    
    # Request Logging Middleware
    app.add_middleware(RequestLoggingMiddleware)
    logger.info("✅ RequestLoggingMiddleware configured")
