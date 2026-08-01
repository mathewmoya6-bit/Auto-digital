# app/modules/ownership/__init__.py
"""Ownership (TCO) module for Auto-D Kenya"""

from app.modules.ownership.router import router
from app.modules.ownership.schemas import (
    TCORequest,
    TCOResponse,
)
from app.modules.ownership.service import OwnershipService

__all__ = [
    "router",
    "TCORequest",
    "TCOResponse",
    "OwnershipService",
]
