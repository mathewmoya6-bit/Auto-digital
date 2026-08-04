# app/core/middleware.py
# Auto-D Kenya - Middleware Setup
# ================================================================
# TYPE: CORE - FastAPI middleware configuration

import time
import logging
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and response times."""
    
    def __init__(self, app, log_headers: bool = False, log_body: bool = False):
        """
        Initialize request logging middleware.
        
        Args:
            app: FastAPI application
            log_headers: Whether to log request headers (default: False)
            log_body: Whether to log request body (default: False)
        """
        super().__init__(app)
        self.log_headers = log_headers
        self.log_body = log_body

    async def dispatch(self, request: Request, call_next):
        # Skip logging for health checks to reduce noise
        skip_paths = ["/health", "/ready", "/live", "/ping"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)

        # Skip logging for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        start_time = time.time()
        
        # Get client info
        client_host = request.client.host if request.client else "unknown"
        
        # Build log message
        log_msg = f"→ {request.method} {request.url.path} from {client_host}"
        
        # Add request ID if available
        request_id = getattr(request.state, 'request_id', None)
        if request_id:
            log_msg = f"[{request_id}] {log_msg}"
        
        logger.info(log_msg)
        
        # Log headers if enabled
        if self.log_headers:
            headers = {k: v for k, v in request.headers.items() 
                      if k.lower() not in ['authorization', 'cookie']}  # Don't log sensitive headers
            logger.debug(f"   Headers: {headers}")

        # Process request with error handling
        try:
            response = await call_next(request)

            # Log response time
            duration = time.time() - start_time
            status_emoji = "✅" if 200 <= response.status_code < 400 else "⚠️" if 400 <= response.status_code < 500 else "❌"
            
            log_msg = f"← {request.method} {request.url.path} → {status_emoji} {response.status_code} ({duration:.3f}s)"
            if request_id:
                log_msg = f"[{request_id}] {log_msg}"
            
            # Warn about slow requests
            if duration > 1.0:
                log_msg += " 🐢 SLOW"
                logger.warning(log_msg)
            else:
                logger.info(log_msg)

            return response

        except Exception as e:
            # Log detailed error information
            duration = time.time() - start_time
            logger.error(f"❌ Unhandled error: {request.method} {request.url.path} ({duration:.3f}s)")
            logger.error(f"   Error: {str(e)}")
            logger.error(f"   Client: {client_host}")
            if self.log_headers:
                logger.error(f"   Headers: {dict(request.headers)}")
            logger.exception("Full traceback:")
            raise


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add a unique request ID to each request for tracing."""
    
    async def dispatch(self, request: Request, call_next):
        # Get request ID from header or generate new one
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Store in request state
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS for production
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware.
    Note: For production, use Redis-based rate limiting (e.g., slowapi).
    """
    
    def __init__(self, app, calls_per_minute: int = 60, exempt_paths: list = None):
        """
        Initialize rate limiter.
        
        Args:
            app: FastAPI application
            calls_per_minute: Maximum requests per minute per client IP
            exempt_paths: List of paths to exempt from rate limiting
        """
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.client_requests = {}
        self.exempt_paths = exempt_paths or ["/health", "/ready", "/live", "/ping", "/docs", "/redoc", "/openapi.json"]
        logger.info(f"🔒 Rate limiting enabled: {calls_per_minute} requests/minute")
        logger.info(f"   Exempt paths: {self.exempt_paths}")
    
    async def dispatch(self, request: Request, call_next):
        # Check if path is exempt
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        # Skip OPTIONS requests
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean up old entries
        self._cleanup_old_entries(current_time)
        
        # Check rate limit
        if client_ip in self.client_requests:
            # Filter requests within the last minute
            recent_requests = [
                t for t in self.client_requests[client_ip]
                if current_time - t < 60
            ]
            self.client_requests[client_ip] = recent_requests
            
            if len(recent_requests) >= self.calls_per_minute:
                # Rate limit exceeded
                from fastapi.responses import JSONResponse
                logger.warning(f"🚫 Rate limit exceeded for {client_ip} ({request.method} {request.url.path})")
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": "60"},
                    content={
                        "status": "error",
                        "message": "Too many requests. Please try again later.",
                        "retry_after": 60
                    }
                )
        
        # Add current request
        if client_ip not in self.client_requests:
            self.client_requests[client_ip] = []
        self.client_requests[client_ip].append(current_time)
        
        # Process request
        return await call_next(request)
    
    def _cleanup_old_entries(self, current_time: float):
        """Remove old entries from the request tracking."""
        for client_ip in list(self.client_requests.keys()):
            # Keep only requests within the last minute
            self.client_requests[client_ip] = [
                t for t in self.client_requests[client_ip] 
                if current_time - t < 60
            ]
            # Remove empty entries
            if not self.client_requests[client_ip]:
                del self.client_requests[client_ip]


def setup_middleware(app: FastAPI) -> None:
    """
    Configure all middleware for the application.

    ⚠️ IMPORTANT: CORS middleware is configured in main.py and must be
    added LAST there (i.e. AFTER this function is called), so that it
    ends up as the OUTERMOST middleware layer.

    Args:
        app: FastAPI application instance
    """
    
    # ─── REQUEST ID MIDDLEWARE (FIRST - before logging) ──────────
    app.add_middleware(RequestIDMiddleware)
    logger.info("✅ RequestIDMiddleware configured")
    
    # ─── SECURITY HEADERS MIDDLEWARE ────────────────────────────
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("✅ SecurityHeadersMiddleware configured")
    
    # ─── REQUEST LOGGING MIDDLEWARE ──────────────────────────────
    # Enable header logging in debug mode only
    log_headers = getattr(settings, "DEBUG", False)
    app.add_middleware(RequestLoggingMiddleware, log_headers=log_headers)
    logger.info(f"✅ RequestLoggingMiddleware configured (log_headers={log_headers})")
    
    # ─── RATE LIMITING MIDDLEWARE (OPTIONAL) ─────────────────────
    # Enable rate limiting in production
    if settings.ENVIRONMENT == "production":
        # Check if rate limiting is enabled via settings
        rate_limit_enabled = getattr(settings, "ENABLE_RATE_LIMITING", True)
        if rate_limit_enabled:
            calls_per_minute = getattr(settings, "RATE_LIMIT_CALLS_PER_MINUTE", 60)
            app.add_middleware(RateLimitMiddleware, calls_per_minute=calls_per_minute)
            logger.info(f"✅ RateLimitMiddleware configured ({calls_per_minute}/minute)")
        else:
            logger.info("⏭️ RateLimitMiddleware disabled by settings")
    else:
        logger.info("⏭️ RateLimitMiddleware skipped (development environment)")
    
    # ─── TRUSTED HOST MIDDLEWARE ──────────────────────────────────
    if settings.ENVIRONMENT == "production":
        # Get allowed hosts from settings
        allowed_hosts = getattr(settings, "ALLOWED_HOSTS", ["*"])
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=allowed_hosts
        )
        logger.info(f"✅ TrustedHostMiddleware configured (allowed_hosts={allowed_hosts})")
    else:
        logger.info("⏭️ TrustedHostMiddleware skipped (development environment)")

    # ─── STARTUP LOGGING ──────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("Middleware Configuration Summary:")
    logger.info(f"  Environment: {settings.ENVIRONMENT}")
    logger.info(f"  RequestIDMiddleware: ENABLED")
    logger.info(f"  SecurityHeadersMiddleware: ENABLED")
    logger.info(f"  RequestLoggingMiddleware: ENABLED (log_headers={getattr(settings, 'DEBUG', False)})")
    
    rate_limit_enabled = getattr(settings, "ENABLE_RATE_LIMITING", True)
    if settings.ENVIRONMENT == "production" and rate_limit_enabled:
        calls_per_minute = getattr(settings, "RATE_LIMIT_CALLS_PER_MINUTE", 60)
        logger.info(f"  RateLimitMiddleware: ENABLED ({calls_per_minute}/minute)")
    else:
        logger.info(f"  RateLimitMiddleware: DISABLED")
    
    allowed_hosts = getattr(settings, "ALLOWED_HOSTS", ["*"])
    logger.info(f"  TrustedHostMiddleware: {'ENABLED' if settings.ENVIRONMENT == 'production' else 'DISABLED'}")
    if settings.ENVIRONMENT == "production":
        logger.info(f"    Allowed Hosts: {allowed_hosts}")
    logger.info("=" * 60)
