"""
Auto-D Kenya
Vehicle Master Service
Business Logic Layer
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.core.exceptions import (
    NotFoundException,
    ValidationException,
)
from app.modules.vehicle_master.repository import VehicleMasterRepository
from app.modules.vehicle_master.audit import AuditService

logger = logging.getLogger(__name__)


class VehicleMasterService:
    """Business logic for Vehicle Master Database."""

    def __init__(self):
        self.repository = VehicleMasterRepository()
        self.audit = AuditService()

    # ==========================================================
    # DASHBOARD
    # ==========================================================

    async def get_dashboard(self) -> Dict[str, Any]:
        """Get dashboard statistics."""
        stats = await self.repository.statistics()
        stats["last_updated"] = datetime.utcnow()
        return stats

    # ==========================================================
    # VEHICLE LOOKUP
    # ==========================================================

    async def get_vehicle(self, variant_id: int) -> Dict[str, Any]:
        """Get complete vehicle by variant ID."""
        vehicle = await self.repository.get_vehicle(variant_id)
        if not vehicle:
            raise NotFoundException(f"Vehicle with variant_id {variant_id} not found")
        return vehicle

    # ==========================================================
    # SEARCH
    # ==========================================================

    async def search(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        year: Optional[int] = None,
        fuel: Optional[str] = None,
        transmission: Optional[str] = None,
        body_type: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        """Search the master vehicle database."""
        return await self.repository.search(
            make=make,
            model=model,
            year=year,
            fuel=fuel,
            transmission=transmission,
            body_type=body_type,
            page=page,
            per_page=per_page,
        )

    # ==========================================================
    # UPDATE COMPLETE VEHICLE
    # ==========================================================

    async def update_vehicle(
        self,
        variant_id: int,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update complete vehicle with validation."""
        vehicle = await self.repository.get_vehicle(variant_id)
        if vehicle is None:
            raise NotFoundException(f"Vehicle with variant_id {variant_id} not found")

        # Track changes for audit
        changes = {}

        if "vehicle" in data and data["vehicle"]:
            result = await self.repository.update_variant(
                variant_id,
                data["vehicle"],
            )
            if result:
                changes["vehicle"] = data["vehicle"]

        if "specification" in data and data["specification"]:
            result = await self.repository.update_specifications(
                variant_id,
                data["specification"],
            )
            if result:
                changes["specification"] = data["specification"]

        if "pricing" in data and data["pricing"]:
            # Validate price
            if "crsp_kes" in data["pricing"]:
                if data["pricing"]["crsp_kes"] <= 0:
                    raise ValidationException("CRSP must be greater than zero")
            
            result = await self.repository.update_base_price(
                variant_id,
                data["pricing"],
            )
            if result:
                changes["pricing"] = data["pricing"]

        # Log audit
        await self.audit.log_update(
            variant_id=variant_id,
            changes=changes,
            action="update_vehicle",
        )

        return await self.repository.get_vehicle(variant_id)

    # ==========================================================
    # UPDATE BASE PRICE
    # ==========================================================

    async def update_base_price(
        self,
        variant_id: int,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update base price with validation."""
        vehicle = await self.repository.get_vehicle(variant_id)
        if vehicle is None:
            raise NotFoundException(f"Vehicle with variant_id {variant_id} not found")

        if "crsp_kes" in values:
            if values["crsp_kes"] <= 0:
                raise ValidationException("CRSP must be greater than zero")

        await self.repository.update_base_price(variant_id, values)

        await self.audit.log_update(
            variant_id=variant_id,
            changes={"pricing": values},
            action="update_pricing",
        )

        return await self.repository.get_vehicle(variant_id)

    # ==========================================================
    # UPDATE SPECIFICATIONS
    # ==========================================================

    async def update_specifications(
        self,
        variant_id: int,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update specifications."""
        vehicle = await self.repository.get_vehicle(variant_id)
        if vehicle is None:
            raise NotFoundException(f"Vehicle with variant_id {variant_id} not found")

        await self.repository.update_specifications(variant_id, values)

        await self.audit.log_update(
            variant_id=variant_id,
            changes={"specification": values},
            action="update_specifications",
        )

        return await self.repository.get_vehicle(variant_id)

    # ==========================================================
    # UPDATE VARIANT
    # ==========================================================

    async def update_variant(
        self,
        variant_id: int,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update variant."""
        vehicle = await self.repository.get_vehicle(variant_id)
        if vehicle is None:
            raise NotFoundException(f"Vehicle with variant_id {variant_id} not found")

        await self.repository.update_variant(variant_id, values)

        await self.audit.log_update(
            variant_id=variant_id,
            changes={"vehicle": values},
            action="update_variant",
        )

        return await self.repository.get_vehicle(variant_id)

    # ==========================================================
    # DEACTIVATE
    # ==========================================================

    async def deactivate_vehicle(self, variant_id: int) -> Dict[str, Any]:
        """Soft-delete vehicle."""
        vehicle = await self.repository.get_vehicle(variant_id)
        if vehicle is None:
            raise NotFoundException(f"Vehicle with variant_id {variant_id} not found")

        await self.repository.deactivate_variant(variant_id)

        await self.audit.log_update(
            variant_id=variant_id,
            changes={"is_active": False},
            action="deactivate_vehicle",
        )

        return {
            "success": True,
            "message": f"Vehicle {variant_id} deactivated successfully",
        }

    # ==========================================================
    # VALIDATION
    # ==========================================================

    async def vehicle_exists(self, variant_id: int) -> bool:
        """Check if vehicle exists."""
        vehicle = await self.repository.get_vehicle(variant_id)
        return vehicle is not None

    # ==========================================================
    # BULK OPERATIONS
    # ==========================================================

    async def bulk_update_prices(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk update base prices."""
        updated = await self.repository.bulk_update_prices(updates)
        
        await self.audit.log_bulk_action(
            action="bulk_update_prices",
            count=updated,
            details={"total": len(updates), "updated": updated},
        )
        
        return {
            "success": True,
            "updated": updated,
            "total": len(updates),
        }
