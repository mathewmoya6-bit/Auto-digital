# backend/app/repositories/service_repository.py
"""
Service Repository - Data access layer for service prices
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from app.core.database import supabase
import logging

logger = logging.getLogger(__name__)


class ServiceRepository:
    """Repository for service price operations"""

    def __init__(self):
        self.table = "service_prices"

    # ---------------------------------------------------------
    # CRUD Operations
    # ---------------------------------------------------------

    def get_all_services(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Get all services"""
        try:
            query = supabase.table(self.table).select("*")
            
            if not include_inactive:
                query = query.eq("active", True)
            
            response = query.order("service_name").execute()
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Error getting all services: {e}")
            return []

    def get_service_by_id(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get service by ID (UUID)"""
        try:
            response = (
                supabase
                .table(self.table)
                .select("*")
                .eq("id", service_id)
                .limit(1)
                .execute()
            )
            
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"Error getting service by ID {service_id}: {e}")
            return None

    def get_service_by_name(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get service by name"""
        try:
            response = (
                supabase
                .table(self.table)
                .select("*")
                .ilike("service_name", service_name)
                .eq("active", True)
                .limit(1)
                .execute()
            )
            
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"Error getting service by name {service_name}: {e}")
            return None

    def get_services_by_type(self, service_type: str) -> List[Dict[str, Any]]:
        """Get all services for a specific service type"""
        try:
            response = (
                supabase
                .table(self.table)
                .select("*")
                .eq("service_type", service_type)
                .eq("active", True)
                .order("price")
                .execute()
            )
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Error getting services by type {service_type}: {e}")
            return []

    def create_service(
        self,
        service_name: str,
        price: float,
        service_type: str = "basic",
        currency: str = "KES",
        description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new service price
        
        Args:
            service_name: Name of the service (required)
            price: Price amount (required)
            service_type: Type of service (basic, premium, etc.)
            currency: Currency code (default: KES)
            description: Service description
        """
        try:
            # Validate required fields
            if not service_name or not service_name.strip():
                raise ValueError("service_name is required and cannot be empty")
            
            if price is None or price <= 0:
                raise ValueError("Price must be greater than 0")
            
            # Check if service already exists with same name and type
            existing = (
                supabase
                .table(self.table)
                .select("id")
                .ilike("service_name", service_name.strip())
                .eq("service_type", service_type)
                .eq("active", True)
                .execute()
            )
            
            if existing.data:
                raise ValueError(
                    f"Service '{service_name}' with type '{service_type}' already exists"
                )
            
            # Prepare data
            data = {
                "service_name": service_name.strip(),
                "service_type": service_type,
                "price": float(price),
                "currency": currency,
                "description": description,
                "active": True,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Insert
            response = (
                supabase
                .table(self.table)
                .insert(data)
                .execute()
            )
            
            if response.data:
                logger.info(f"Created service: {service_name} at {price} {currency}")
                return response.data[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating service: {e}")
            raise

    def update_service(
        self,
        service_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a service price
        
        Args:
            service_id: UUID of the service
            updates: Dictionary of fields to update
        """
        try:
            # Validate service exists
            existing = self.get_service_by_id(service_id)
            if not existing:
                raise ValueError(f"Service with ID {service_id} not found")
            
            # Validate required fields if being updated
            if "service_name" in updates:
                if not updates["service_name"] or not updates["service_name"].strip():
                    raise ValueError("service_name cannot be empty")
                updates["service_name"] = updates["service_name"].strip()
            
            if "price" in updates and updates["price"] <= 0:
                raise ValueError("Price must be greater than 0")
            
            # Add updated_at
            updates["updated_at"] = datetime.now().isoformat()
            
            # Remove None values
            updates = {k: v for k, v in updates.items() if v is not None}
            
            if not updates:
                return existing
            
            # Update
            response = (
                supabase
                .table(self.table)
                .update(updates)
                .eq("id", service_id)
                .execute()
            )
            
            if response.data:
                logger.info(f"Updated service {service_id}")
                return response.data[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating service {service_id}: {e}")
            raise

    def delete_service(self, service_id: str, hard_delete: bool = False) -> bool:
        """
        Delete or deactivate a service
        
        Args:
            service_id: UUID of the service
            hard_delete: If True, permanently delete; if False, soft delete
        """
        try:
            if hard_delete:
                # Permanent delete
                response = (
                    supabase
                    .table(self.table)
                    .delete()
                    .eq("id", service_id)
                    .execute()
                )
            else:
                # Soft delete (deactivate)
                response = (
                    supabase
                    .table(self.table)
                    .update({
                        "active": False,
                        "updated_at": datetime.now().isoformat()
                    })
                    .eq("id", service_id)
                    .execute()
                )
            
            return len(response.data) > 0
            
        except Exception as e:
            logger.error(f"Error deleting service {service_id}: {e}")
            return False

    # ---------------------------------------------------------
    # Query Methods
    # ---------------------------------------------------------

    def get_service_types(self) -> List[str]:
        """Get all unique service types"""
        try:
            response = (
                supabase
                .table(self.table)
                .select("service_type")
                .eq("active", True)
                .execute()
            )
            
            if not response.data:
                return []
            
            types = list(set([item["service_type"] for item in response.data if item.get("service_type")]))
            return sorted(types)
            
        except Exception as e:
            logger.error(f"Error getting service types: {e}")
            return []

    def get_active_services(self) -> List[Dict[str, Any]]:
        """Get all active services"""
        return self.get_all_services(include_inactive=False)

    def get_inactive_services(self) -> List[Dict[str, Any]]:
        """Get all inactive services"""
        try:
            response = (
                supabase
                .table(self.table)
                .select("*")
                .eq("active", False)
                .order("service_name")
                .execute()
            )
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Error getting inactive services: {e}")
            return []

    def get_service_pricing_summary(self) -> Dict[str, Any]:
        """Get pricing summary for services"""
        try:
            response = (
                supabase
                .table(self.table)
                .select("*")
                .eq("active", True)
                .execute()
            )
            
            services = response.data if response.data else []
            
            if not services:
                return {
                    "total_services": 0,
                    "unique_names": 0,
                    "price_range": {"min": 0, "max": 0},
                    "average_price": 0,
                    "service_types": {}
                }
            
            # Calculate statistics
            prices = [s["price"] for s in services]
            
            # Group by service_type
            type_summary = {}
            for s in services:
                service_type = s.get("service_type", "default")
                if service_type not in type_summary:
                    type_summary[service_type] = {
                        "count": 0,
                        "min_price": float("inf"),
                        "max_price": 0,
                        "total_price": 0,
                        "services": []
                    }
                type_summary[service_type]["count"] += 1
                type_summary[service_type]["min_price"] = min(
                    type_summary[service_type]["min_price"], 
                    s["price"]
                )
                type_summary[service_type]["max_price"] = max(
                    type_summary[service_type]["max_price"], 
                    s["price"]
                )
                type_summary[service_type]["total_price"] += s["price"]
                type_summary[service_type]["services"].append(s["service_name"])
            
            # Calculate averages
            for service_type, data in type_summary.items():
                data["avg_price"] = round(
                    data["total_price"] / data["count"], 
                    2
                )
                data["services"] = sorted(data["services"])
            
            return {
                "total_services": len(services),
                "unique_names": len(set(s["service_name"] for s in services)),
                "price_range": {
                    "min": min(prices) if prices else 0,
                    "max": max(prices) if prices else 0
                },
                "average_price": round(sum(prices) / len(prices), 2) if prices else 0,
                "service_types": type_summary
            }
            
        except Exception as e:
            logger.error(f"Error getting service pricing summary: {e}")
            return {}

    # ---------------------------------------------------------
    # Bulk Operations
    # ---------------------------------------------------------

    def bulk_create_services(self, services: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk create services"""
        results = {
            "success": [],
            "failed": [],
            "total": len(services)
        }
        
        for service_data in services:
            try:
                # Extract required fields
                service_name = service_data.get("service_name")
                price = service_data.get("price")
                
                if not service_name or not service_name.strip():
                    results["failed"].append({
                        "data": service_data,
                        "error": "Missing or empty service_name"
                    })
                    continue
                
                if not price or price <= 0:
                    results["failed"].append({
                        "data": service_data,
                        "error": "Invalid price (must be > 0)"
                    })
                    continue
                
                result = self.create_service(
                    service_name=service_name.strip(),
                    price=price,
                    service_type=service_data.get("service_type", "basic"),
                    currency=service_data.get("currency", "KES"),
                    description=service_data.get("description")
                )
                
                if result:
                    results["success"].append(result)
                else:
                    results["failed"].append({
                        "data": service_data,
                        "error": "Failed to create service"
                    })
                    
            except Exception as e:
                results["failed"].append({
                    "data": service_data,
                    "error": str(e)
                })
        
        return results

    # ---------------------------------------------------------
    # Search and Filter
    # ---------------------------------------------------------

    def search_services(self, search_term: str) -> List[Dict[str, Any]]:
        """Search services by name or description"""
        try:
            response = (
                supabase
                .table(self.table)
                .select("*")
                .eq("active", True)
                .or_(
                    f"service_name.ilike.%{search_term}%,"
                    f"description.ilike.%{search_term}%"
                )
                .order("service_name")
                .execute()
            )
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Error searching services: {e}")
            return []

    def get_services_by_price_range(
        self, 
        min_price: float, 
        max_price: float
    ) -> List[Dict[str, Any]]:
        """Get services within a price range"""
        try:
            response = (
                supabase
                .table(self.table)
                .select("*")
                .eq("active", True)
                .gte("price", min_price)
                .lte("price", max_price)
                .order("price")
                .execute()
            )
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Error getting services by price range: {e}")
            return []
