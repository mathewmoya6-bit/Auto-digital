# backend/app/api/v1/services.py
"""
Service Prices API endpoints
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator

from app.services.service_prices_service import ServicePricesService

router = APIRouter()


class ServicePriceCreate(BaseModel):
    """Schema for creating a service price"""
    service_name: str = Field(..., min_length=1, max_length=255)
    price: float = Field(..., gt=0)
    service_type: str = Field("basic", max_length=50)
    currency: str = Field("KES", max_length=3)
    description: Optional[str] = Field(None)
    
    @validator('service_name')
    def validate_service_name(cls, v):
        if not v or not v.strip():
            raise ValueError("service_name cannot be empty")
        return v.strip()
    
    @validator('service_type')
    def validate_service_type(cls, v):
        if not v or not v.strip():
            return "basic"
        return v.strip().lower()


class ServicePriceUpdate(BaseModel):
    """Schema for updating a service price"""
    service_name: Optional[str] = Field(None, min_length=1, max_length=255)
    price: Optional[float] = Field(None, gt=0)
    service_type: Optional[str] = Field(None, max_length=50)
    currency: Optional[str] = Field(None, max_length=3)
    description: Optional[str] = Field(None)
    active: Optional[bool] = Field(None)
    
    @validator('service_name')
    def validate_service_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError("service_name cannot be empty")
        return v.strip() if v else v


@router.get("/services")
async def get_services(
    include_inactive: bool = Query(False),
    service_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    service: ServicePricesService = Depends()
):
    """Get all services with optional filters"""
    try:
        if search:
            services = service.search_services(search)
        elif service_type:
            services = service.get_services_by_type(service_type)
        else:
            services = service.get_all_services(include_inactive)
        
        return {
            "status": "success",
            "data": services,
            "count": len(services)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services/{service_id}")
async def get_service(
    service_id: str,
    service: ServicePricesService = Depends()
):
    """Get service by ID (UUID)"""
    try:
        result = service.get_service_by_id(service_id)
        if not result:
            raise HTTPException(status_code=404, detail="Service not found")
        
        return {
            "status": "success",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/services")
async def create_service(
    data: ServicePriceCreate,
    service: ServicePricesService = Depends()
):
    """Create a new service price"""
    try:
        result = service.create_service(
            service_name=data.service_name,
            price=data.price,
            service_type=data.service_type,
            currency=data.currency,
            description=data.description
        )
        
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create service")
        
        return {
            "status": "success",
            "data": result,
            "message": f"Created service: {data.service_name}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/services/{service_id}")
async def update_service(
    service_id: str,
    data: ServicePriceUpdate,
    service: ServicePricesService = Depends()
):
    """Update a service price"""
    try:
        # Only include fields that were provided
        updates = data.dict(exclude_unset=True)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        result = service.update_service(service_id, updates)
        
        if not result:
            raise HTTPException(status_code=404, detail="Service not found")
        
        return {
            "status": "success",
            "data": result,
            "message": f"Updated service {service_id}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/services/{service_id}")
async def delete_service(
    service_id: str,
    hard_delete: bool = Query(False),
    service: ServicePricesService = Depends()
):
    """Delete a service price"""
    try:
        result = service.delete_service(service_id, hard_delete)
        
        if not result:
            raise HTTPException(status_code=404, detail="Service not found")
        
        return {
            "status": "success",
            "message": f"Service {service_id} {'permanently deleted' if hard_delete else 'deactivated'}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services/summary/pricing")
async def get_pricing_summary(
    service: ServicePricesService = Depends()
):
    """Get pricing summary"""
    try:
        summary = service.get_pricing_summary()
        return {
            "status": "success",
            "data": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services/comparison/types")
async def get_type_comparison(
    service: ServicePricesService = Depends()
):
    """Compare pricing across service types"""
    try:
        comparison = service.get_type_comparison()
        return {
            "status": "success",
            "data": comparison
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services/types")
async def get_service_types(
    service: ServicePricesService = Depends()
):
    """Get all service types"""
    try:
        types = service.get_service_types()
        return {
            "status": "success",
            "data": types
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/services/bulk")
async def bulk_create_services(
    services: List[ServicePriceCreate],
    service: ServicePricesService = Depends()
):
    """Bulk create services"""
    try:
        # Convert to dict
        services_data = [s.dict() for s in services]
        
        results = service.bulk_create_services(services_data)
        
        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services/price-range")
async def get_services_by_price_range(
    min_price: float = Query(..., gt=0),
    max_price: float = Query(..., gt=0),
    service: ServicePricesService = Depends()
):
    """Get services within a price range"""
    try:
        if min_price > max_price:
            raise HTTPException(status_code=400, detail="min_price must be less than max_price")
        
        services = service.get_services_by_price_range(min_price, max_price)
        
        return {
            "status": "success",
            "data": services,
            "count": len(services)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
