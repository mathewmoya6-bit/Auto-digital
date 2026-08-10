# app/modules/valuation/repository.py
import logging
from typing import Any, Dict, List, Optional

from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class ValuationRepository:
    """Repository for vehicle valuation data access."""

    CRSP_TABLE = "vehicle_crsp_lookup"

    def __init__(self):
        self.supabase = get_supabase()
        logger.info("ValuationRepository initialized")

    def get_crsp_by_id(self, crsp_id: int) -> Optional[Dict[str, Any]]:
        """Get a CRSP record by its ID."""
        try:
            response = (
                self.supabase
                .table(self.CRSP_TABLE)
                .select("*")
                .eq("crsp_id", crsp_id)
                .limit(1)
                .execute()
            )

            if response.data:
                return response.data[0]
            return None

        except Exception as exc:
            logger.error("Error fetching CRSP by ID %s: %s", crsp_id, exc)
            return None

    def search_crsp(
        self,
        make: Optional[str] = None,
        model: Optional[str] = None,
        manufacture_year: Optional[int] = None,
        engine_capacity_id: Optional[int] = None,
        fuel: Optional[str] = None,
        transmission: Optional[str] = None,
        body_type: Optional[str] = None,
        limit: int = 25,
    ) -> List[Dict[str, Any]]:
        """Search for CRSP records with optional filters."""
        try:
            query = self.supabase.table(self.CRSP_TABLE).select("*")

            if make:
                query = query.ilike("make", f"%{make}%")
            if model:
                query = query.ilike("model", f"%{model}%")
            if manufacture_year is not None:
                query = query.eq("manufacture_year", manufacture_year)
            if engine_capacity_id is not None:
                query = query.eq("engine_capacity_id", engine_capacity_id)
            if fuel:
                query = query.ilike("fuel", f"%{fuel}%")
            if transmission:
                query = query.ilike("transmission", f"%{transmission}%")
            if body_type:
                query = query.ilike("body_type", f"%{body_type}%")

            # Order by canonical and price to get best matches first
            query = query.order("canonical_id", desc=True)
            query = query.order("crsp_kes", desc=True)
            query = query.limit(limit)

            response = query.execute()
            return response.data or []

        except Exception as exc:
            logger.error("Error searching CRSP: %s", exc)
            return []

    def get_valuation_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get valuation history for a user."""
        try:
            response = (
                self.supabase
                .table("valuation_history")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return response.data or []

        except Exception as exc:
            logger.error("Error fetching valuation history: %s", exc)
            return []

    def save_valuation_history(
        self,
        user_id: str,
        valuation_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Save a valuation to history."""
        try:
            data = {
                "user_id": user_id,
                "crsp_id": valuation_data.get("crsp_id"),
                "make": valuation_data.get("make"),
                "model": valuation_data.get("model"),
                "manufacture_year": valuation_data.get("manufacture_year"),
                "mileage": valuation_data.get("mileage", 0),
                "estimated_value": valuation_data.get("estimated_value"),
                "confidence_score": valuation_data.get("confidence_score", 0),
                "condition": valuation_data.get("condition", "good"),
                "accident_history": valuation_data.get("accident_history", "none"),
                "location": valuation_data.get("location"),
                "fuel_type": valuation_data.get("fuel_type"),
                "transmission": valuation_data.get("transmission"),
                "body_type": valuation_data.get("body_type"),
                "adjustments": valuation_data.get("adjustments", {}),
                "created_at": valuation_data.get("created_at", datetime.now().isoformat()),
            }

            # Remove None values to avoid Supabase errors
            data = {k: v for k, v in data.items() if v is not None}

            response = (
                self.supabase
                .table("valuation_history")
                .insert(data)
                .execute()
            )

            if response.data:
                return response.data[0]
            return None

        except Exception as exc:
            logger.error("Error saving valuation history: %s", exc)
            return None

    def get_valuation_stats(self, user_id: str) -> Dict[str, Any]:
        """Get valuation statistics for a user."""
        try:
            # Get all history for stats
            response = (
                self.supabase
                .table("valuation_history")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )

            history = response.data or []

            if not history:
                return {
                    "total_valuations": 0,
                    "average_value": 0.0,
                    "highest_value": 0.0,
                    "lowest_value": 0.0,
                    "total_value": 0.0,
                    "average_confidence": 0.0,
                    "last_valuation_date": None,
                    "valuations_by_make": {},
                    "valuations_by_month": {},
                }

            values = []
            confidences = []
            makes = {}
            months = {}

            for item in history:
                # Extract value
                value = item.get("estimated_value")
                if value is not None:
                    try:
                        values.append(float(value))
                    except (TypeError, ValueError):
                        pass

                # Extract confidence
                confidence = item.get("confidence_score")
                if confidence is not None:
                    try:
                        confidences.append(float(confidence))
                    except (TypeError, ValueError):
                        pass

                # Count by make
                make = item.get("make") or "Unknown"
                makes[make] = makes.get(make, 0) + 1

                # Count by month
                created_at = item.get("created_at")
                if created_at:
                    try:
                        if isinstance(created_at, str):
                            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        else:
                            dt = created_at
                        month_key = dt.strftime("%Y-%m")
                        months[month_key] = months.get(month_key, 0) + 1
                    except (TypeError, ValueError):
                        pass

            return {
                "total_valuations": len(history),
                "average_value": sum(values) / len(values) if values else 0.0,
                "highest_value": max(values) if values else 0.0,
                "lowest_value": min(values) if values else 0.0,
                "total_value": sum(values),
                "average_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
                "last_valuation_date": history[0].get("created_at") if history else None,
                "valuations_by_make": makes,
                "valuations_by_month": months,
            }

        except Exception as exc:
            logger.error("Error getting valuation stats: %s", exc)
            return {
                "total_valuations": 0,
                "average_value": 0.0,
                "highest_value": 0.0,
                "lowest_value": 0.0,
                "total_value": 0.0,
                "average_confidence": 0.0,
                "last_valuation_date": None,
                "valuations_by_make": {},
                "valuations_by_month": {},
            }
