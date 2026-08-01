# app/modules/admin/__init__.py
# Auto-D Kenya - Admin Module
# ================================================================

from .router import router
from .schemas import *

__all__ = [
    "router",
]
