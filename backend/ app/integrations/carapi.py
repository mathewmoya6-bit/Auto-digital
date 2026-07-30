# app/integrations/carapi.py
# Auto-D Kenya - CarAPI Integration
# ================================================================
# TYPE: INTEGRATION - CarAPI client

import logging
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)


class CarAPIClient:
    """CarAPI client for vehicle data."""
    
    def __init__(self):
        self.api_key = None  # Would be loaded from config
        self.base_url = "https://api.carapi.com/v1"
    
    async def get_vehicle_data(self, make: str, model: str, year: int = None) -> Dict[str, Any]:
        """Get vehicle data from CarAPI."""
        try:
            params = {
                "make": make,
                "model": model
            }
            if year:
                params["year"] = year
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/vehicles",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": response.text}
                    
        except Exception as e:
            logger.error(f"CarAPI error: {str(e)}")
            return {"error": str(e)}
