# backend/app/services/service_prices_service.py
"""
Service Prices Service - Business logic for service price operations
"""

from typing import Optional, List, Dict, Any
from app.repositories.service_repository import ServiceRepository
import logging

logger = logging.getLogger(__name__)


class ServicePricesService:
    """Service for service price operations"""
    
    def __init__(self):
        self.repository = ServiceRepository()
    
    def get_all_services(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Get all services"""
        return self.repository.get_all_services(include_inactive)
    
    def get_active_services(self) -> List[Dict[str, Any]]:
        """Get all active services"""
        return self.repository.get_active_services()
    
    def get_service_by_id(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get service by ID (UUID)"""
        return self.repository.get_service_by_id(service_id)
    
    def get_service_by_name(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get service by name"""
        return self.repository.get_service_by_name(service_name)
    
    def get_services_by_type(self, service_type: str) -> List[Dict[str, Any]]:
        """Get services by type"""
        return self.repository.get_services_by_type(service_type)
    
    def create_service(
        self,
        service_name: str,
        price: float,
        service_type: str = "basic",
        currency: str = "KES",
        description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new service price"""
        try:
            # Validate
            if not service_name or not service_name.strip():
                raise ValueError("service_name is required and cannot be empty")
            
            if price <= 0:
                raise ValueError("Price must be greater than 0")
            
            return self.repository.create_service(
                service_name=service_name.strip(),
                price=price,
                service_type=service_type,
                currency=currency,
                description=description
            )
            
        except Exception as e:
            logger.error(f"Error creating service: {e}")
            raise
    
    def update_service(
        self,
        service_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a service price"""
        try:
            # Validate service_name if provided
            if "service_name" in updates:
                if not updates["service_name"] or not updates["service_name"].strip():
                    raise ValueError("service_name cannot be empty")
            
            # Validate price if provided
            if "price" in updates and updates["price"] <= 0:
                raise ValueError("Price must be greater than 0")
            
            return self.repository.update_service(service_id, updates)
            
        except Exception as e:
            logger.error(f"Error updating service {service_id}: {e}")
            raise
    
    def delete_service(self, service_id: str, hard_delete: bool = False) -> bool:
        """Delete a service"""
        return self.repository.delete_service(service_id, hard_delete)
    
    def get_service_types(self) -> List[str]:
        """Get all service types"""
        return self.repository.get_service_types()
    
    def get_pricing_summary(self) -> Dict[str, Any]:
        """Get pricing summary"""
        return self.repository.get_service_pricing_summary()
    
    def bulk_create_services(self, services: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk create services"""
        return self.repository.bulk_create_services(services)
    
    def search_services(self, search_term: str) -> List[Dict[str, Any]]:
        """Search services"""
        return self.repository.search_services(search_term)
    
    def get_services_by_price_range(
        self, 
        min_price: float, 
        max_price: float
    ) -> List[Dict[str, Any]]:
        """Get services within price range"""
        return self.repository.get_services_by_price_range(min_price, max_price)
    
    def get_type_comparison(self) -> Dict[str, Any]:
        """Compare pricing across service types"""
        types = self.get_service_types()
        comparison = {}
        
        for service_type in types:
            services = self.get_services_by_type(service_type)
            if services:
                prices = [s["price"] for s in services]
                comparison[service_type] = {
                    "count": len(services),
                    "min_price": min(prices),
                    "max_price": max(prices),
                    "avg_price": round(sum(prices) / len(prices), 2),
                    "services": [s["service_name"] for s in services]
                }
        
        return comparison
