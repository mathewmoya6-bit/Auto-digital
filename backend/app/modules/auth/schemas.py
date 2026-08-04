# Auto-D Kenya - Authentication Schemas
# ================================================================

from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator
)


class LoginRequest(BaseModel):

    email: EmailStr
    password: str


class RegisterRequest(BaseModel):

    email: EmailStr

    password: str = Field(
        ...,
        min_length=8
    )

    full_name: Optional[str] = None


    @field_validator("password")
    @classmethod
    def validate_password(cls, value):

        if len(value) < 8:
            raise ValueError(
                "Password must be at least 8 characters"
            )

        return value



class TokenResponse(BaseModel):

    access_token: str

    token_type: str = "bearer"

    expires_in: int



class UserResponse(BaseModel):

    id: str

    email: str

    full_name: Optional[str] = None

    created_at: datetime


    class Config:

        from_attributes = True
