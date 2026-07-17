# backend/app/models/user.py
"""
User Models - Authentication and user profiles
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator


class User(BaseModel):
    """User model for authentication"""
    id: str = Field(..., description="Supabase user ID")
    email: EmailStr = Field(..., description="User email address")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    last_sign_in: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    email_confirmed: bool = False
    phone_confirmed: bool = False
    is_active: bool = True
    
    # Optional user metadata
    user_metadata: Optional[dict] = Field(default_factory=dict)
    app_metadata: Optional[dict] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "created_at": "2026-07-14T10:00:00Z",
                "email_confirmed": True,
                "is_active": True
            }
        }


class UserProfile(BaseModel):
    """User profile model for additional user data"""
    id: str = Field(..., description="Profile ID")
    user_id: str = Field(..., description="Supabase user ID")
    full_name: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=15)
    company: Optional[str] = Field(None, max_length=100)
    position: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=100)
    country: str = Field("Kenya", max_length=50)
    currency: str = Field("KES", max_length=3)
    
    # Preferences
    preferred_vehicle_type: Optional[str] = None
    notification_enabled: bool = True
    email_notifications: bool = True
    sms_notifications: bool = False
    
    # Profile image
    avatar_url: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    last_active: Optional[datetime] = None
    
    # Account status
    is_active: bool = True
    is_admin: bool = False
    is_verified: bool = False
    
    # Usage stats
    total_valuations: int = 0
    total_reports: int = 0
    
    @validator('phone_number')
    def validate_phone(cls, v):
        """Validate Kenyan phone numbers"""
        if v is None:
            return v
        # Remove any non-digit characters
        cleaned = ''.join(filter(str.isdigit, v))
        # Check if it's a valid Kenyan number (starting with 254 or 0)
        if cleaned.startswith('254') and len(cleaned) == 12:
            return f"+{cleaned}"
        elif cleaned.startswith('0') and len(cleaned) == 10:
            return f"+254{cleaned[1:]}"
        elif cleaned.startswith('7') or cleaned.startswith('1'):
            return f"+254{cleaned}"
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "pro_123456",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "full_name": "John Doe",
                "phone_number": "+254712345678",
                "company": "Auto-D Kenya",
                "location": "Nairobi",
                "country": "Kenya",
                "currency": "KES",
                "is_admin": False,
                "is_verified": True
            }
        }


class UserCreate(BaseModel):
    """User creation model"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v


class UserLogin(BaseModel):
    """User login model"""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """User update model"""
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    location: Optional[str] = None
    preferred_vehicle_type: Optional[str] = None
    notification_enabled: Optional[bool] = None
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    avatar_url: Optional[str] = None
    
    # Admin-only fields
    is_admin: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """User response model"""
    id: str
    email: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    location: Optional[str] = None
    country: str
    currency: str
    avatar_url: Optional[str] = None
    is_admin: bool
    is_verified: bool
    is_active: bool
    created_at: datetime
    last_active: Optional[datetime] = None
    total_valuations: int
    total_reports: int
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Authentication token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None
    user: UserResponse


class PasswordResetRequest(BaseModel):
    """Password reset request model"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation model"""
    token: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v
