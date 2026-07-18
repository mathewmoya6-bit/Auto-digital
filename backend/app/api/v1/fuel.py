# backend/app/api/v1/fuel.py
"""
Fuel API - Fuel price endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from app.services.fuel_service import FuelService
from app.core.security import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
fuel_service = FuelService()


@router.get("/prices")
async def get_fuel_prices(
    current_user: dict = Depends(get_current_user)
):
    """Get all fuel prices"""
    try:
        prices = fuel_service.get_all_fuel_prices()
        return prices
    except Exception as e:
        logger.error(f"Error fetching fuel prices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch fuel prices"
        )


@router.get("/prices/{fuel_type}")
async def get_fuel_price(
    fuel_type: str,
    current_user: dict = Depends(get_current_user)
):
    """Get price for a specific fuel type"""
    try:
        price = fuel_service.get_fuel_price(fuel_type)
        if not price:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fuel type '{fuel_type}' not found"
            )
        return price
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching fuel price for {fuel_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch fuel price"
        )


@router.get("/defaults")
async def get_default_fuel_prices(
    current_user: dict = Depends(get_current_user)
):
    """Get default fuel prices from settings"""
    try:
        defaults = fuel_service.get_default_fuel_prices()
        return defaults
    except Exception as e:
        logger.error(f"Error fetching default fuel prices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch default fuel prices"
        )
