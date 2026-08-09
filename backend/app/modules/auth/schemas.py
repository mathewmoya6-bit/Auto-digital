# app/modules/auth/schemas.py
# Auto-D Kenya - Authentication Schemas
# ================================================================
# TYPE: MODULE - Pydantic request/response models

from typing import Optional
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    account_type: Optional[str] = "individual"  # "individual" | "corporate" | "admin" | "staff" | "agent"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: Optional[str] = None
    user_id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str = "user"
    is_active: bool = True
    account_type: Optional[str] = "individual"

    class Config:
        extra = "allow"  # tolerate extra profile fields (phone, county, etc.) without validation errors
