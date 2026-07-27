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
                query = query.eq("is_active", True)
            
            response = query.order("service_name").execute()
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Error getting all services: {e}")
            return []

    def get_service_by_id(self, service_id: int) -> Optional[Dict[str, Any]]:
        """Get service by ID"""
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
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
            
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"Error getting service by name {service_name}: {e}")
            return None

    def create_service(
        self,
        service_name: str,
        price: float,
        service_id: Optional[int] = None,
        currency: str = "KES",
        billing_cycle: str = "monthly",
        tier: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new service price"""
        try:
            # Validate required fields
            if not service_name:
                raise ValueError("service_name is required")
            
            if price is None or price <= 0:
                raise ValueError("Price must be greater than 0")
            
            # Check if service already exists with same name and tier
            existing = (
                supabase
                .table(self.table)
                .select("id")
                .ilike("service_name", service_name)
                .eq("tier", tier)
                .eq("billing_cycle", billing_cycle)
                .eq("is_active", True)
                .execute()
            )
            
            if existing.data:
                raise ValueError(
                    f"Service '{service_name}' with tier '{tier}' and "
                    f"cycle '{billing_cycle}' already exists"
                )
            
            # Prepare data
            data = {
                "service_name": service_name.strip(),
                "price": float(price),
                "currency": currency,
                "billing_cycle": billing_cycle,
                "is_active": True,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Add optional fields
            if service_id:
                data["service_id"] = service_id
            if tier:
                data["tier"] = tier
            if description:
                data["description"] = description
            if metadata:
                data["metadata"] = metadata
            
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
        service_id: int,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a service price"""
        try:
            # Validate service exists
            existing = self.get_service_by_id(service_id)
            if not existing:
                raise ValueError(f"Service with ID {service_id} not found")
            
            # Validate required fields if being updated
            if "service_name" in updates and not updates["service_name"]:
                raise ValueError("service_name cannot be empty")
            
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

    def delete_service(self, service_id: int, hard_delete: bool = False) -> bool:
        """Delete or deactivate a service"""
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
                        "is_active": False,
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

    def get_services_by_tier(self, tier: str) -> List[Dict[str, Any]]:
        """Get all services for a specific tier"""
        try:
            response = (
                supabase
                .table(self.table)
                .select("*")
                .eq("tier", tier)
                .eq("is_active", True)
                .order("price")
                .execute()
            )
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Error getting services by tier {tier}: {e}")
            return []

    def get_services_by_cycle(self, billing_cycle: str) -> List[Dict[str, Any]]:
        """Get all services by billing cycle"""
        try:
            response = (
                supabase
                .table(self.table)
                .select("*")
                .eq("billing_cycle", billing_cycle)
                .eq("is_active", True)
                .order("price")
                .execute()
            )
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Error getting services by cycle {billing_cycle}: {e}")
            return []

    def get_service_pricing_summary(self) -> Dict[str, Any]:
        """Get pricing summary for services"""
        try:
            response = (
                supabase
                .table(self.table)
                .select("*")
                .eq("is_active", True)
                .execute()
            )
            
            services = response.data if response.data else []
            
            if not services:
                return {
                    "total_services": 0,
                    "unique_names": 0,
                    "price_range": {"min": 0, "max": 0},
                    "average_price": 0,
                    "tiers": {},
                    "billing_cycles": {}
                }
            
            # Calculate statistics
            prices = [s["price"] for s in services]
            
            # Group by tier
            tier_summary = {}
            for s in services:
                tier = s.get("tier", "default")
                if tier not in tier_summary:
                    tier_summary[tier] = {
                        "count": 0,
                        "min_price": float("inf"),
                        "max_price": 0,
                        "total_price": 0
                    }
                tier_summary[tier]["count"] += 1
                tier_summary[tier]["min_price"] = min(
                    tier_summary[tier]["min_price"], 
                    s["price"]
                )
                tier_summary[tier]["max_price"] = max(
                    tier_summary[tier]["max_price"], 
                    s["price"]
                )
                tier_summary[tier]["total_price"] += s["price"]
            
            # Calculate averages
            for tier, data in tier_summary.items():
                data["avg_price"] = round(
                    data["total_price"] / data["count"], 
                    2
                )
            
            # Group by billing cycle
            cycle_summary = {}
            for s in services:
                cycle = s.get("billing_cycle", "monthly")
                if cycle not in cycle_summary:
                    cycle_summary[cycle] = {
                        "count": 0,
                        "total_price": 0
                    }
                cycle_summary[cycle]["count"] += 1
                cycle_summary[cycle]["total_price"] += s["price"]
            
            for cycle, data in cycle_summary.items():
                data["avg_price"] = round(
                    data["total_price"] / data["count"], 
                    2
                )
            
            return {
                "total_services": len(services),
                "unique_names": len(set(s["service_name"] for s in services)),
                "price_range": {
                    "min": min(prices) if prices else 0,
                    "max": max(prices) if prices else 0
                },
                "average_price": round(sum(prices) / len(prices), 2) if prices else 0,
                "tiers": tier_summary,
                "billing_cycles": cycle_summary
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
                
                if not service_name:
                    results["failed"].append({
                        "data": service_data,
                        "error": "Missing service_name"
                    })
                    continue
                
                if not price or price <= 0:
                    results["failed"].append({
                        "data": service_data,
                        "error": "Invalid price"
                    })
                    continue
                
                result = self.create_service(
                    service_name=service_name,
                    price=price,
                    service_id=service_data.get("service_id"),
                    currency=service_data.get("currency", "KES"),
                    billing_cycle=service_data.get("billing_cycle", "monthly"),
                    tier=service_data.get("tier"),
                    description=service_data.get("description"),
                    metadata=service_data.get("metadata")
                )
                
                if result:
                    results["success"].append(result)
                else:
                    results["failed"].append({
                        "data": service_data,
                        "error": "Failed to create"
                    })
                    
            except Exception as e:
                results["failed"].append({
                    "data": service_data,
                    "error": str(e)
                })
        
        return results
