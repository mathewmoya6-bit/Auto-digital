"""
Fuel Repository - Data access layer for fuel prices
Production Ready
"""

from datetime import date, timedelta
from typing import Optional, List, Dict, Any
import logging

from app.core.database import supabase

logger = logging.getLogger(__name__)


class FuelRepository:
    """Repository for fuel price operations"""

    def __init__(self):
        self.table = "fuel_prices"

    # ---------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------

    def _get_fuel_type_id(self, fuel_type: str) -> Optional[int]:
        """Lookup fuel type ID."""
        try:
            response = (
                supabase
                .table("fuel_types")
                .select("id")
                .ilike("name", fuel_type.strip())
                .limit(1)
                .execute()
            )

            if response.data:
                return response.data[0]["id"]

            logger.warning(f"Fuel type '{fuel_type}' not found.")
            return None

        except Exception as e:
            logger.exception(e)
            return None

    def _get_fuel_type_name(self, fuel_type_id: int) -> Optional[str]:
        """Get fuel type name by ID."""
        try:
            response = (
                supabase
                .table("fuel_types")
                .select("name")
                .eq("id", fuel_type_id)
                .limit(1)
                .execute()
            )

            if response.data:
                return response.data[0]["name"]

            return None

        except Exception as e:
            logger.exception(e)
            return None

    # ---------------------------------------------------------

    def get_all_fuel_prices(self, region: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns latest active fuel prices.
        Optionally filter by region.
        """
        try:
            query = (
                supabase
                .table(self.table)
                .select("""
                    *,
                    fuel_types(name)
                """)
                .is_("effective_to", None)
            )

            if region:
                query = query.eq("region", region)

            response = query.order("fuel_type_id").execute()

            # Transform data to include fuel_type name at top level
            result = []
            for item in response.data:
                item_copy = item.copy()
                if item.get("fuel_types"):
                    item_copy["fuel_type"] = item["fuel_types"].get("name")
                else:
                    # Try to get fuel type name from ID
                    fuel_type_name = self._get_fuel_type_name(item.get("fuel_type_id"))
                    if fuel_type_name:
                        item_copy["fuel_type"] = fuel_type_name
                result.append(item_copy)

            return result

        except Exception as e:
            logger.exception(e)
            return []

    # ---------------------------------------------------------

    def get_fuel_price(
        self,
        fuel_type: str,
        region: str = "Kenya"
    ) -> Optional[Dict[str, Any]]:
        """Get current price for a specific fuel type and region."""
        fuel_type_id = self._get_fuel_type_id(fuel_type)

        if fuel_type_id is None:
            return None

        try:
            response = (
                supabase
                .table(self.table)
                .select("""
                    *,
                    fuel_types(name)
                """)
                .eq("fuel_type_id", fuel_type_id)
                .eq("region", region)
                .is_("effective_to", None)
                .limit(1)
                .execute()
            )

            if response.data:
                item = response.data[0]
                if item.get("fuel_types"):
                    item["fuel_type"] = item["fuel_types"].get("name")
                return item

            return None

        except Exception as e:
            logger.exception(e)
            return None

    # ---------------------------------------------------------

    def get_fuel_prices_by_region(
        self,
        region: str
    ) -> List[Dict[str, Any]]:
        """Get all active fuel prices for a specific region."""
        try:
            response = (
                supabase
                .table(self.table)
                .select("""
                    *,
                    fuel_types(name)
                """)
                .eq("region", region)
                .is_("effective_to", None)
                .order("fuel_type_id")
                .execute()
            )

            # Transform data to include fuel_type name
            result = []
            for item in response.data:
                item_copy = item.copy()
                if item.get("fuel_types"):
                    item_copy["fuel_type"] = item["fuel_types"].get("name")
                else:
                    fuel_type_name = self._get_fuel_type_name(item.get("fuel_type_id"))
                    if fuel_type_name:
                        item_copy["fuel_type"] = fuel_type_name
                result.append(item_copy)

            return result

        except Exception as e:
            logger.exception(e)
            return []

    # ---------------------------------------------------------

    def upsert_fuel_price(
        self,
        fuel_type: str,
        price: float,
        region: str = "Kenya",
        source: str = "Admin",
        unit: str = "Litre"
    ) -> Optional[Dict[str, Any]]:
        """
        Insert or update a fuel price.
        Closes previous active price and creates a new one.
        """
        fuel_type_id = self._get_fuel_type_id(fuel_type)

        if fuel_type_id is None:
            raise ValueError(f"Unknown fuel type: {fuel_type}")

        if price <= 0:
            raise ValueError("Price must be greater than 0")

        try:
            # Close previous active price for this fuel type and region
            (
                supabase
                .table(self.table)
                .update({
                    "effective_to": date.today() - timedelta(days=1)
                })
                .eq("fuel_type_id", fuel_type_id)
                .eq("region", region)
                .is_("effective_to", None)
                .execute()
            )

            # Insert new active price
            payload = {
                "fuel_type_id": fuel_type_id,
                "region": region,
                "price_per_unit": float(price),
                "effective_from": date.today(),
                "effective_to": None,
                "source": source,
                "unit": unit
            }

            response = (
                supabase
                .table(self.table)
                .insert(payload)
                .execute()
            )

            if response.data:
                # Add fuel_type name to response
                item = response.data[0]
                item["fuel_type"] = fuel_type
                logger.info(f"Updated {fuel_type} price to {price} in {region}")
                return item

            return None

        except Exception as e:
            logger.exception(e)
            return None

    # ---------------------------------------------------------

    def delete_fuel_price(
        self,
        fuel_type: str,
        region: str = "Kenya"
    ) -> bool:
        """Soft delete a fuel price by setting effective_to to yesterday."""
        fuel_type_id = self._get_fuel_type_id(fuel_type)

        if fuel_type_id is None:
            return False

        try:
            # Soft delete - set effective_to to yesterday
            response = (
                supabase
                .table(self.table)
                .update({
                    "effective_to": date.today() - timedelta(days=1)
                })
                .eq("fuel_type_id", fuel_type_id)
                .eq("region", region)
                .is_("effective_to", None)
                .execute()
            )

            return len(response.data) > 0

        except Exception as e:
            logger.exception(e)
            return False

    # ---------------------------------------------------------

    def hard_delete_fuel_price(
        self,
        fuel_type: str,
        region: str = "Kenya"
    ) -> bool:
        """Permanently delete a fuel price."""
        fuel_type_id = self._get_fuel_type_id(fuel_type)

        if fuel_type_id is None:
            return False

        try:
            response = (
                supabase
                .table(self.table)
                .delete()
                .eq("fuel_type_id", fuel_type_id)
                .eq("region", region)
                .execute()
            )

            return len(response.data) > 0

        except Exception as e:
            logger.exception(e)
            return False

    # ---------------------------------------------------------

    def get_fuel_price_history(
        self,
        fuel_type: str,
        region: str = "Kenya",
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Get historical fuel prices for a specific fuel type and region."""
        fuel_type_id = self._get_fuel_type_id(fuel_type)

        if fuel_type_id is None:
            return []

        try:
            response = (
                supabase
                .table(self.table)
                .select("""
                    *,
                    fuel_types(name)
                """)
                .eq("fuel_type_id", fuel_type_id)
                .eq("region", region)
                .order("effective_from", desc=True)
                .limit(limit)
                .execute()
            )

            # Transform data
            result = []
            for item in response.data:
                item_copy = item.copy()
                if item.get("fuel_types"):
                    item_copy["fuel_type"] = item["fuel_types"].get("name")
                result.append(item_copy)

            return result

        except Exception as e:
            logger.exception(e)
            return []

    # ---------------------------------------------------------

    def get_all_regions(self) -> List[str]:
        """Get all unique regions with fuel prices."""
        try:
            response = (
                supabase
                .table(self.table)
                .select("region")
                .is_("effective_to", None)
                .execute()
            )

            if not response.data:
                return []

            regions = list(set([item["region"] for item in response.data if item.get("region")]))
            return sorted(regions)

        except Exception as e:
            logger.exception(e)
            return []

    # ---------------------------------------------------------

    def get_all_fuel_types(self) -> List[str]:
        """Get all fuel types from the fuel_types table."""
        try:
            response = (
                supabase
                .table("fuel_types")
                .select("name")
                .order("name")
                .execute()
            )

            if not response.data:
                return []

            return [item["name"] for item in response.data]

        except Exception as e:
            logger.exception(e)
            return []

    # ---------------------------------------------------------

    def get_latest_prices_by_region(self, region: str) -> Dict[str, Dict[str, Any]]:
        """Get latest prices for all fuel types in a region."""
        try:
            response = (
                supabase
                .table(self.table)
                .select("""
                    *,
                    fuel_types(name)
                """)
                .eq("region", region)
                .is_("effective_to", None)
                .order("fuel_type_id")
                .execute()
            )

            if not response.data:
                return {}

            # Transform to dict keyed by fuel_type
            result = {}
            for item in response.data:
                fuel_type_name = None
                if item.get("fuel_types"):
                    fuel_type_name = item["fuel_types"].get("name")
                else:
                    fuel_type_name = self._get_fuel_type_name(item.get("fuel_type_id"))

                if fuel_type_name:
                    item_copy = item.copy()
                    item_copy["fuel_type"] = fuel_type_name
                    result[fuel_type_name] = item_copy

            return result

        except Exception as e:
            logger.exception(e)
            return {}

    # ---------------------------------------------------------

    def get_price_statistics(self, region: Optional[str] = None) -> Dict[str, Any]:
        """Get price statistics for fuel prices."""
        try:
            query = (
                supabase
                .table(self.table)
                .select("price_per_unit, region, fuel_type_id")
                .is_("effective_to", None)
            )

            if region:
                query = query.eq("region", region)

            response = query.execute()

            if not response.data:
                return {
                    "total_records": 0,
                    "fuel_types": [],
                    "regions": [],
                    "price_range": {"min": 0, "max": 0},
                    "average_price": 0,
                    "total_regions": 0
                }

            prices = [item["price_per_unit"] for item in response.data]
            regions = list(set([item["region"] for item in response.data if item.get("region")]))

            # Get fuel type names
            fuel_type_ids = list(set([item["fuel_type_id"] for item in response.data if item.get("fuel_type_id")]))
            fuel_types = []
            for ft_id in fuel_type_ids:
                name = self._get_fuel_type_name(ft_id)
                if name:
                    fuel_types.append(name)

            return {
                "total_records": len(response.data),
                "fuel_types": sorted(fuel_types),
                "regions": sorted(regions),
                "total_regions": len(regions),
                "price_range": {
                    "min": min(prices) if prices else 0,
                    "max": max(prices) if prices else 0
                },
                "average_price": round(sum(prices) / len(prices), 2) if prices else 0
            }

        except Exception as e:
            logger.exception(e)
            return {}

    # ---------------------------------------------------------

    def bulk_upsert_fuel_prices(
        self,
        prices: List[Dict[str, Any]],
        region: str = "Kenya",
        source: str = "bulk"
    ) -> Dict[str, Any]:
        """Bulk upsert fuel prices."""
        results = {
            "success": [],
            "failed": [],
            "total": len(prices)
        }

        for price_data in prices:
            try:
                fuel_type = price_data.get("fuel_type")
                price = price_data.get("price") or price_data.get("price_per_unit")

                if not fuel_type or not price:
                    results["failed"].append({
                        "data": price_data,
                        "error": "Missing fuel_type or price"
                    })
                    continue

                result = self.upsert_fuel_price(
                    fuel_type=fuel_type,
                    price=float(price),
                    region=price_data.get("region", region),
                    source=price_data.get("source", source),
                    unit=price_data.get("unit", "Litre")
                )

                if result:
                    results["success"].append(result)
                else:
                    results["failed"].append({
                        "data": price_data,
                        "error": "Failed to upsert"
                    })

            except Exception as e:
                results["failed"].append({
                    "data": price_data,
                    "error": str(e)
                })

        return results

    # ---------------------------------------------------------

    def get_price_by_date(
        self,
        fuel_type: str,
        target_date: date,
        region: str = "Kenya"
    ) -> Optional[Dict[str, Any]]:
        """Get fuel price as it was on a specific date."""
        fuel_type_id = self._get_fuel_type_id(fuel_type)

        if fuel_type_id is None:
            return None

        try:
            response = (
                supabase
                .table(self.table)
                .select("""
                    *,
                    fuel_types(name)
                """)
                .eq("fuel_type_id", fuel_type_id)
                .eq("region", region)
                .lte("effective_from", target_date.isoformat())
                .filter("effective_to", "gte", target_date.isoformat())
                .limit(1)
                .execute()
            )

            if response.data:
                item = response.data[0]
                if item.get("fuel_types"):
                    item["fuel_type"] = item["fuel_types"].get("name")
                return item

            return None

        except Exception as e:
            logger.exception(e)
            return None

    # ---------------------------------------------------------

    def get_price_trend(
        self,
        fuel_type: str,
        region: str = "Kenya",
        days: int = 30
    ) -> Dict[str, Any]:
        """Get price trend for a fuel type over time."""
        fuel_type_id = self._get_fuel_type_id(fuel_type)

        if fuel_type_id is None:
            return {
                "status": "error",
                "message": f"Fuel type '{fuel_type}' not found"
            }

        try:
            start_date = date.today() - timedelta(days=days)

            response = (
                supabase
                .table(self.table)
                .select("price_per_unit, effective_from")
                .eq("fuel_type_id", fuel_type_id)
                .eq("region", region)
                .gte("effective_from", start_date.isoformat())
                .order("effective_from")
                .execute()
            )

            if not response.data or len(response.data) < 2:
                return {
                    "status": "insufficient_data",
                    "message": "Not enough data for trend analysis",
                    "data_points": len(response.data)
                }

            prices = [item["price_per_unit"] for item in response.data]
            dates = [item["effective_from"] for item in response.data]

            # Calculate trend
            first_price = prices[0]
            last_price = prices[-1]
            percent_change = ((last_price - first_price) / first_price) * 100 if first_price > 0 else 0

            # Determine direction
            if percent_change > 3:
                direction = "up"
            elif percent_change < -3:
                direction = "down"
            else:
                direction = "stable"

            return {
                "status": "success",
                "fuel_type": fuel_type,
                "region": region,
                "period": {
                    "start": dates[0] if dates else None,
                    "end": dates[-1] if dates else None,
                    "days": len(prices)
                },
                "statistics": {
                    "current_price": last_price,
                    "first_price": first_price,
                    "min_price": min(prices),
                    "max_price": max(prices),
                    "average_price": round(sum(prices) / len(prices), 2)
                },
                "trend": {
                    "direction": direction,
                    "percent_change": round(percent_change, 2)
                },
                "history": [
                    {"date": d, "price": p} for d, p in zip(dates, prices)
                ]
            }

        except Exception as e:
            logger.exception(e)
            return {
                "status": "error",
                "message": str(e)
            }

    # ---------------------------------------------------------

    def get_region_comparison(self, fuel_type: str) -> Dict[str, Any]:
        """Compare prices for a fuel type across regions."""
        fuel_type_id = self._get_fuel_type_id(fuel_type)

        if fuel_type_id is None:
            return {
                "status": "error",
                "message": f"Fuel type '{fuel_type}' not found"
            }

        try:
            response = (
                supabase
                .table(self.table)
                .select("price_per_unit, region")
                .eq("fuel_type_id", fuel_type_id)
                .is_("effective_to", None)
                .execute()
            )

            if not response.data:
                return {
                    "status": "no_data",
                    "message": "No active prices found for this fuel type"
                }

            region_prices = {}
            for item in response.data:
                region_prices[item["region"]] = item["price_per_unit"]

            prices = list(region_prices.values())
            avg_price = sum(prices) / len(prices) if prices else 0

            return {
                "status": "success",
                "fuel_type": fuel_type,
                "regions": region_prices,
                "statistics": {
                    "average_price": round(avg_price, 2),
                    "min_price": min(prices) if prices else 0,
                    "max_price": max(prices) if prices else 0,
                    "price_range": max(prices) - min(prices) if prices else 0,
                    "total_regions": len(region_prices)
                }
            }

        except Exception as e:
            logger.exception(e)
            return {
                "status": "error",
                "message": str(e)
            }
