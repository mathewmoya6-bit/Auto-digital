# app/integrations/openai.py
# Auto-D Kenya - OpenAI Integration
# ================================================================
# TYPE: INTEGRATION - OpenAI client

import logging
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)


class OpenAIClient:
    """OpenAI client for AI features."""
    
    def __init__(self):
        self.api_key = None  # Would be loaded from config
        self.base_url = "https://api.openai.com/v1"
    
    async def generate_description(self, vehicle_data: Dict[str, Any]) -> str:
        """Generate a vehicle description using AI."""
        if not self.api_key:
            return "AI description not available"
        
        try:
            prompt = f"Generate a compelling description for a {vehicle_data.get('year', '')} {vehicle_data.get('make', '')} {vehicle_data.get('model', '')} with {vehicle_data.get('mileage', 0)} km."
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [
                            {"role": "system", "content": "You are a vehicle expert."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 150
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                else:
                    return "AI description generation failed"
                    
        except Exception as e:
            logger.error(f"OpenAI error: {str(e)}")
            return "AI description generation failed"
