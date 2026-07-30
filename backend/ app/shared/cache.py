# app/shared/cache.py
# Auto-D Kenya - Cache Service
# ================================================================
# TYPE: SHARED - Caching utilities

import json
import logging
from typing import Optional, Any
from datetime import datetime, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Simple in-memory cache service."""
    
    def __init__(self):
        self.cache = {}
        self.default_ttl = 3600  # 1 hour
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        if key in self.cache:
            data = self.cache[key]
            if data.get("expires_at") and datetime.utcnow() < data.get("expires_at"):
                return data.get("value")
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set a value in cache."""
        ttl = ttl or self.default_ttl
        self.cache[key] = {
            "value": value,
            "expires_at": datetime.utcnow() + timedelta(seconds=ttl)
        }
    
    def delete(self, key: str) -> None:
        """Delete a value from cache."""
        if key in self.cache:
            del self.cache[key]
    
    def clear(self) -> None:
        """Clear all cache."""
        self.cache.clear()
    
    def get_or_set(self, key: str, callback: callable, ttl: int = None) -> Any:
        """Get a value from cache or set it if not exists."""
        value = self.get(key)
        if value is None:
            value = callback()
            self.set(key, value, ttl)
        return value
