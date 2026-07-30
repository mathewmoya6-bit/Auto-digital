# app/modules/admin/__init__.py
# Auto-D Kenya - Admin Module
# ================================================================

"""Admin module for Auto-D Kenya."""

from .router import router
from .service import AdminService

__all__ = [
    "router",
    "AdminService"
]
