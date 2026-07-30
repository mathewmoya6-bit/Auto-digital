# app/modules/auth/schemas.py
# Auto-D Kenya - Authentication Schemas
# ================================================================
# TYPE: MODULE - Authentication Pydantic schemas

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    created_at: datetime
