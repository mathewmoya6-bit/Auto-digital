# app/core/logging.py
# Auto-D Kenya - Logging Configuration
# ================================================================
# TYPE: CORE - Logging setup

import logging
import sys
from logging.handlers import RotatingFileHandler

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure application logging.
    """
    # Get log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    try:
        file_handler = RotatingFileHandler(
            "auto-d.log",
            maxBytes=10_485_760,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception:
        pass
    
    # Supress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    logging.info(f"✅ Logging configured with level: {settings.LOG_LEVEL}")
