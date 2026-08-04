# app/modules/auth/schemas.py
# Auto-D Kenya - Authentication Schemas
# ================================================================
# TYPE: MODULE - Authentication Pydantic schemas

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ================================================================
# REQUEST SCHEMAS
# ================================================================


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr
    password: str = Field(..., min_length=8)


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        description="Minimum 8 character password"
    )
    full_name: Optional[str] = Field(
        default=None,
        max_length=100
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        """
        Validate password strength.
        """

        if len(value) < 8:
            raise ValueError(
                "Password must be at least 8 characters"
            )

        return value


# ================================================================
# RESPONSE SCHEMAS
# ================================================================


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """Authenticated user response."""

    id: str
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime
