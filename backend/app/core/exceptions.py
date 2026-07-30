# app/core/exceptions.py
# Auto-D Kenya - Exception Handlers
# ================================================================
# TYPE: CORE - Global exception handling

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception."""
    def __init__(self, message: str, status_code: int = 400, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundException(AppException):
    """Resource not found exception."""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class UnauthorizedException(AppException):
    """Unauthorized access exception."""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


class ForbiddenException(AppException):
    """Forbidden access exception."""
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403)


class ValidationException(AppException):
    """Validation error exception."""
    def __init__(self, message: str = "Validation error", details: dict = None):
        super().__init__(message, status_code=422, details=details or {})


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Configure global exception handlers.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """Handle application exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.__class__.__name__,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle unhandled exceptions."""
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "message": str(exc) if settings.DEBUG else "An unexpected error occurred",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
