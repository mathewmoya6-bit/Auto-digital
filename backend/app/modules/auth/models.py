# app/modules/auth/models.py
# Auto-D Kenya - Authentication Models
# ================================================================
# TYPE: MODULE - Authentication database models

# Auth models are managed by Supabase Auth
# This file is a placeholder for future custom models

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class UserProfile(BaseModel):
    """User profile model."""
    id: str
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_verified: bool = False
    is_active: bool = True
