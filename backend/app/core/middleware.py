# app/core/middleware.py
# Auto-D Kenya - Middleware Setup
# ================================================================
# TYPE: CORE - FastAPI middleware configuration

import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and response times."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(f"→ {request.method} {request.url.path}")
        
        # Process request
        response = await call_next(request)
        
        # Log response time
        duration = time.time() - start_time
        logger.info(f"← {request.method} {request.url.path} → {response.status_code} ({duration:.3f}s)")
        
        return response


def setup_middleware(app: FastAPI) -> None:
    """
    Configure all middleware for the application.
    
    Args:
        app: FastAPI application instance
    """
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.get_cors_methods(),
        allow_headers=settings.get_cors_headers(),
        max_age=settings.CORS_MAX_AGE
    )
    
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
    
    # Request Logging Middleware
    app.add_middleware(RequestLoggingMiddleware)
