from fastapi import HTTPException, Depends, Header
from typing import Optional, Dict
import logging
from app.core.database import supabase

logger = logging.getLogger(__name__)


async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict:
    """Get current user from Supabase session"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid auth header")

        token = parts[1]

        try:
            response = supabase.auth.get_user(token)
            if response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "user_metadata": response.user.user_metadata,
                }
        except Exception as e:
            logger.error(f"Supabase auth error: {e}")

        raise HTTPException(status_code=401, detail="Invalid token")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")
