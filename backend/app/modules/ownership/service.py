# app/modules/ownership/service.py
"""
Auto-D Kenya - Ownership / Total Cost of Ownership Service

Clean architecture:
    Router -> OwnershipService -> OwnershipRepository -> Supabase

The service performs calculations. Database access belongs in repository.py.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.modules.ownership.schemas import TCORequest
from app.modules.ownership.repository import OwnershipRepository

logger = logging.getLogger(__name__)


class OwnershipService:
    """Calculate Auto-D Total Cost of Ownership."""

    def __init__(self, repository: Optional[OwnershipRepository] = None):
        self.repository = repository or OwnershipRepository()

    # ------------------------------------------------------------------
    # Safe type conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _float(value: Any, default: float = 0.0) -> float:
        if value is None:
            return default
        try:
            if isinstance(value, str):
                value = value.strip().replace(",", "")
                if not value:
                    return default
            return float(value)
        except (TypeError, ValueError):
            logger.warning("Invalid numeric value %r; using %s", value, default)
            return default

    @staticmethod
    def _int(value: Any, default: int = 0) -> int:
        if value is None:
            return default
        try:
            if isinstance(value, str):
                value = value.strip().replace(",", "")
                if not value:
                    return default
            return int(float(value))
        except (TypeError, ValueError):
            logger.warning("Invalid integer value %r; using %s", value, default)
            return default

    # ------------------------------------------------------------------
    # Main TCO calculation
    # ------------------------------------------------------------------

    async def calculate_tco(
        self,
        request: TCORequest,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        crsp_id = self._int(request.vehicle_crsp_id)
        vehicle = await self.repository.get_vehicle_crsp(crsp_id)

        if not vehicle:
            raise ValueError(
                f"No vehicle found for vehicle_crsp_id={crsp_id}"
            )

        annual_mileage = self._float(request.annual_mileage, 15000.0)
        purchase_price = self._float(request.purchase_price, 0.0)
        down_payment = self._float(request.down_payment, 0.0)
        interest_rate = self._float(request.interest_rate, 0.0)
        loan_years = max(self._int(request.loan_term_years, 5), 1)

        vehicle_year = self._int(
            request.vehicle_year,
            self._int(vehicle.get("manufacture_year"), datetime.now().year),
        )

        vehicle_type = str(
            request.vehicle_type or "ice"
        ).strip().lower()

        purchase_type = str(
            request.purchase_type or "cash"
        ).strip().lower()

        condition = str(
            request.vehicle_condition or "used"
        ).strip().lower()

        fuel_type = str(
            request.fuel_type
            or vehicle.get("fuel")
            or "petrol"
        ).strip().lower()

        # CRSP price is the fallback purchase price.
        crsp_price = self._float(vehicle.get("crsp_kes"), 0.0)

        if purchase_price <= 0:
            purchase_price = crsp_price

        if purchase_price <= 0:
            raise ValueError(
                f"Vehicle {crsp_id} has no valid purchase/CRSP price."
            )

        # Condition adjustment.
        condition_factor = {
            "new": 1.00,
            "used": 0.85,
        }.get(condition, 1.00)

        adjusted_purchase_price = purchase_price * condition_factor

        # Powertrain adjustment.
        powertrain_factor = {
            "ice": 1.00,
            "hybrid": 0.95,
            "ev": 0.90,
            "electric": 0.90,
        }.get(vehicle_type, 1.00)

        adjusted_purchase_price *= powertrain_factor

        # Engine capacity must use numeric engine_capacity_cc.
        engine_cc = self._float(
            vehicle.get("engine_capacity_cc"),
            1800.0,
        )
        engine_litres = engine_cc / 1000.0

        fuel_efficiency = self._calculate_fuel_efficiency(
            engine_litres=engine_litres,
            vehicle_year=vehicle_year,
            fuel_type=fuel_type,
        )

        # Database-driven Auto-D cost inputs.
        cost_inputs = await self.repository.get_cost_inputs(
            fuel_type=fuel_type,
            vehicle_type=vehicle_type,
            vehicle_category=vehicle.get("body_type"),
            category_id=None,
        )

        fuel_price = self._float(
            getattr(request, "fuel_price", None),
            cost_inputs["fuel_price"],
        )

        maintenance_per_km = self._float(
            getattr(request, "maintenance_cost_per_km", None),
            cost_inputs["maintenance_per_km"],
        )

        tyre_per_km = self._float(
            getattr(request, "tyre_cost_per_km", None),
            cost_inputs["tyre_per_km"],
        )

        insurance_rate = self._float(
            getattr(request, "insurance_rate", None),
            cost_inputs["insurance_rate"],
        )

        # Fuel.
        if fuel_type in {"electric", "ev"}:
            annual_fuel = 0.0
        else:
            litres_per_year = annual_mileage / max(fuel_efficiency, 0.1)
            annual_fuel = litres_per_year * fuel_price

        # Service.
        annual_service = annual_mileage * maintenance_per_km

        # Tyres.
        annual_tyres = annual_mileage * tyre_per_km

        # Insurance.
        annual_insurance = (
            adjusted_purchase_price * insurance_rate / 100.0
        )

        # Depreciation.
        annual_depreciation = 0.0

        if request.include_depreciation:
            age = max(datetime.now().year - vehicle_year, 0)
            dep_factor = await self.repository.get_depreciation_factor(
                category_id=None,
                age=age,
            )
            annual_depreciation = adjusted_purchase_price * dep_factor

        # Finance.
        term_months = loan_years * 12

        if purchase_type == "finance":
            down_payment = min(
                max(down_payment, 0.0),
                adjusted_purchase_price,
            )

            loan_principal = max(
                adjusted_purchase_price - down_payment,
                0.0,
            )

            monthly_rate = interest_rate / 100.0 / 12.0

            if loan_principal > 0 and monthly_rate > 0:
                factor = (1.0 + monthly_rate) ** term_months
                monthly_payment = (
                    loan_principal
                    * monthly_rate
                    * factor
                    / (factor - 1.0)
                )
                total_payment = monthly_payment * term_months
                total_interest = total_payment - loan_principal
            else:
                monthly_payment = loan_principal / term_months
                total_payment = loan_principal
                total_interest = 0.0
        else:
            down_payment = adjusted_purchase_price
            loan_principal = 0.0
            monthly_payment = 0.0
            total_payment = 0.0
            total_interest = 0.0

        annual_running_cost = (
            annual_fuel
            + annual_service
            + annual_tyres
            + annual_insurance
        )

        # Do NOT double-count the purchase price for financed vehicles.
        acquisition_cost = (
            adjusted_purchase_price
            if purchase_type == "cash"
            else down_payment + total_payment
        )

        total_running_cost = annual_running_cost * loan_years

        total_depreciation = (
            annual_depreciation * loan_years
            if request.include_depreciation
            else 0.0
        )

        total_ownership_cost = (
            acquisition_cost
            + total_running_cost
            + total_depreciation
        )

        total_km = annual_mileage * loan_years

        cost_per_km = (
            total_ownership_cost / total_km
            if total_km > 0
            else 0.0
        )

        monthly_total = total_ownership_cost / term_months

        if request.include_depreciation:
            resale_value = max(
                adjusted_purchase_price - total_depreciation,
                adjusted_purchase_price * 0.15,
            )
        else:
            resale_value = adjusted_purchase_price

        monthly_fuel = annual_fuel / 12.0
        monthly_service = annual_service / 12.0
        monthly_tyres = annual_tyres / 12.0
        monthly_insurance = annual_insurance / 12.0
        monthly_depreciation = annual_depreciation / 12.0

        monthly_running_total = (
            monthly_fuel
            + monthly_service
            + monthly_tyres
            + monthly_insurance
        )

        # Components.
        components: List[Dict[str, Any]] = []

        def add_component(name: str, amount: float) -> None:
            percentage = (
                amount / total_ownership_cost * 100.0
                if total_ownership_cost > 0
                else 0.0
            )
            components.append({
                "name": name,
                "amount": round(amount, 2),
                "percentage": round(percentage, 1),
            })

        add_component("Vehicle Purchase", adjusted_purchase_price)

        if total_interest > 0:
            add_component("Loan Interest", total_interest)

        add_component("Fuel", annual_fuel * loan_years)
        add_component("Service", annual_service * loan_years)
        add_component("Tyres", annual_tyres * loan_years)
        add_component("Insurance", annual_insurance * loan_years)

        if request.include_depreciation:
            add_component("Depreciation", total_depreciation)

        components.sort(
            key=lambda item: item["amount"],
            reverse=True,
        )

        yearly_breakdown = self._yearly_breakdown(
            loan_years=loan_years,
            annual_fuel=annual_fuel,
            annual_service=annual_service,
            annual_tyres=annual_tyres,
            annual_insurance=annual_insurance,
            annual_depreciation=annual_depreciation,
            include_depreciation=request.include_depreciation,
            monthly_payment=monthly_payment,
            purchase_type=purchase_type,
            interest_rate=interest_rate,
            loan_principal=loan_principal,
            purchase_price=adjusted_purchase_price,
        )

        rci = self._calculate_rci(cost_per_km)

        return {
            "total_cost": round(total_ownership_cost, 2),
            "monthly_cost": round(monthly_total, 2),
            "monthly_payment": round(monthly_payment, 2),
            "total_interest": round(total_interest, 2),
            "cost_per_km": round(cost_per_km, 2),
            "total_depreciation": round(total_depreciation, 2),
            "resale_value": round(resale_value, 2),

            "monthly_breakdown": {
                "loan_payment": round(monthly_payment, 2),
                "fuel": round(monthly_fuel, 2),
                "service": round(monthly_service, 2),
                "maintenance": round(monthly_service, 2),
                "tyres": round(monthly_tyres, 2),
                "insurance": round(monthly_insurance, 2),
                "depreciation": round(monthly_depreciation, 2),
                "total": round(monthly_running_total, 2),
            },

            "annual_breakdown": {
                "fuel": round(annual_fuel, 2),
                "service": round(annual_service, 2),
                "tyres": round(annual_tyres, 2),
                "insurance": round(annual_insurance, 2),
                "depreciation": round(annual_depreciation, 2),
                "running_cost": round(annual_running_cost, 2),
            },

            "components": components,
            "yearly_breakdown": yearly_breakdown,

            "rci": {
                "value": round(rci, 2),
                "label": self._rci_label(rci),
                "stars": self._rci_stars(rci),
                "class": self._rci_class(rci),
            },

            "loan_details": {
                "principal": round(loan_principal, 2),
                "interest_rate": interest_rate,
                "term_years": loan_years,
                "term_months": term_months,
                "total_payment": round(total_payment, 2),
                "purchase_type": purchase_type,
            },

            "vehicle_details": {
                "vehicle_crsp_id": crsp_id,
                "make": vehicle.get("make", ""),
                "model": vehicle.get("model", ""),
                "variant": vehicle.get("trim_level", ""),
                "fuel_type": fuel_type.capitalize(),
                "vehicle_condition": condition,
                "purchase_type": purchase_type,
                "vehicle_year": vehicle_year,
                "vehicle_type": vehicle_type,
                "engine_capacity": vehicle.get(
                    "engine_capacity_cc",
                    engine_cc,
                ),
                "transmission": vehicle.get("transmission", ""),
                "body_type": vehicle.get("body_type", ""),
            },

            "crsp_reference": {
                "crsp_kes": vehicle.get("crsp_kes"),
                "manufacture_year": vehicle.get("manufacture_year"),
                "is_matched": True,
            },

            "currency": "KES",
            "calculated_at": datetime.utcnow().isoformat(),
        }

    # ------------------------------------------------------------------
    # Fuel efficiency
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_fuel_efficiency(
        engine_litres: float,
        vehicle_year: int,
        fuel_type: str,
    ) -> float:

        base = {
            "petrol": 12.0,
            "diesel": 14.0,
            "hybrid": 18.0,
            "lpg": 11.0,
            "cng": 10.0,
            "electric": 0.0,
        }

        if fuel_type in {"electric", "ev"}:
            return 0.0

        efficiency = base.get(fuel_type, 12.0)

        if engine_litres > 1.5:
            efficiency -= (engine_litres - 1.5) * 1.5

        age = max(datetime.now().year - vehicle_year, 0)
        age_factor = max(0.75, 1.0 - age * 0.01)

        return max(efficiency * age_factor, 4.0)

    # ------------------------------------------------------------------
    # Yearly breakdown
    # ------------------------------------------------------------------

    def _yearly_breakdown(
        self,
        loan_years: int,
        annual_fuel: float,
        annual_service: float,
        annual_tyres: float,
        annual_insurance: float,
        annual_depreciation: float,
        include_depreciation: bool,
        monthly_payment: float,
        purchase_type: str,
        interest_rate: float,
        loan_principal: float,
        purchase_price: float,
    ) -> List[Dict[str, Any]]:

        result = []
        remaining_loan = loan_principal
        current_value = purchase_price

        for year in range(1, loan_years + 1):

            yearly_payment = (
                monthly_payment * 12.0
                if purchase_type == "finance"
                else 0.0
            )

            if purchase_type == "finance":
                annual_interest = (
                    remaining_loan * interest_rate / 100.0
                )

                annual_principal = max(
                    yearly_payment - annual_interest,
                    0.0,
                )

                remaining_loan = max(
                    remaining_loan - annual_principal,
                    0.0,
                )
            else:
                annual_interest = 0.0

            yearly_depreciation = (
                annual_depreciation
                if include_depreciation
                else 0.0
            )

            if include_depreciation:
                current_value = max(
                    current_value - yearly_depreciation,
                    0.0,
                )

            running = (
                annual_fuel
                + annual_service
                + annual_tyres
                + annual_insurance
            )

            total = (
                yearly_payment
                + running
                + yearly_depreciation
            )

            result.append({
                "year": year,
                "total_cost": round(total, 2),
                "running_cost": round(running, 2),
                "fuel": round(annual_fuel, 2),
                "service": round(annual_service, 2),
                "maintenance": round(annual_service, 2),
                "tyres": round(annual_tyres, 2),
                "insurance": round(annual_insurance, 2),
                "depreciation": round(yearly_depreciation, 2),
                "loan_payment": round(yearly_payment, 2),
                "interest": round(annual_interest, 2),
                "vehicle_value": round(current_value, 2),
            })

        return result

    # ------------------------------------------------------------------
    # Running Cost Index
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_rci(cost_per_km: float) -> float:
        if cost_per_km <= 0:
            return 0.0
        return min((cost_per_km / 50.0) * 100.0, 200.0)

    @staticmethod
    def _rci_label(rci: float) -> str:
        if rci <= 40:
            return "Excellent"
        if rci <= 70:
            return "Good"
        if rci <= 100:
            return "Average"
        if rci <= 140:
            return "Expensive"
        return "Very Expensive"

    @staticmethod
    def _rci_stars(rci: float) -> str:
        if rci <= 40:
            return "★★★★★"
        if rci <= 70:
            return "★★★★"
        if rci <= 100:
            return "★★★"
        if rci <= 140:
            return "★★"
        return "★"

    @staticmethod
    def _rci_class(rci: float) -> str:
        if rci <= 40:
            return "excellent"
        if rci <= 70:
            return "good"
        if rci <= 100:
            return "average"
        if rci <= 140:
            return "expensive"
        return "very-expensive"
