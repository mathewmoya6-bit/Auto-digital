# backend/app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from app.core.database import supabase
from app.core.security import create_access_token, get_current_user

router = APIRouter()
security = HTTPBearer()

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str

@router.post("/login")
async def login(request: LoginRequest):
    """Login with email and password"""
    try:
        # Authenticate with Supabase
        response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Create JWT token
        token = create_access_token({
            "sub": response.user.id,
            "email": response.user.email
        })
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": response.user.id,
                "email": response.user.email
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.post("/register")
async def register(request: RegisterRequest):
    """Register a new user"""
    try:
        # Register with Supabase
        response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password
        })
        
        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed"
            )
        
        # Create user profile
        supabase.table("user_profiles").insert({
            "user_id": response.user.id,
            "full_name": request.full_name,
            "email": request.email
        }).execute()
        
        # Create JWT token
        token = create_access_token({
            "sub": response.user.id,
            "email": response.user.email
        })
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "full_name": request.full_name
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout current user"""
    return {"message": "Logged out successfully"}
