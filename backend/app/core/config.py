# backend/app/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://xgkdbithhlvoqjnqvfmj.supabase.co")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhna2RiaXRoaGx2b3FqbnF2Zm1qIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI2NTE4NzQsImV4cCI6MjA5ODIyNzg3NH0.-4P2aQAlDl_4oW0C18gh7cEBzoIKeiLUmMnITz-Nt9Y")
    
    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-secret-key-here")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Auto-D API"
    
    # CORS
    BACKEND_CORS_ORIGINS: list = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
