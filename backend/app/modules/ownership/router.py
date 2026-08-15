"""
Auto-D Kenya
Ownership API Router

Production endpoint:

POST /api/v1/ownership/calculate
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.modules.ownership.engine import OwnershipEngine
from app.modules.ownership.schemas import (
    OwnershipCostRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ownership",
    tags=["Ownership"],
)

engine = OwnershipEngine()


@router.post(
    "/calculate",
    status_code=status.HTTP_200_OK,
)
async def calculate_ownership(
    request: OwnershipCostRequest,
):
    """
    Calculate production vehicle ownership / running costs.

    Authoritative vehicle identifier:
        vehicle_crsp_id

    Calculation source:
        calculate_vehicle_running_cost_v2()
    """

    try:
        result = await engine.calculate(request)

        if result.get("success") is False:
            error = result.get(
                "error",
                "Vehicle ownership calculation failed",
            )

            # Vehicle not found is a client-side request problem.
            if "not found" in error.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=error,
                )

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=error,
            )

        return result

    except HTTPException:
        raise

    except ValueError as exc:
        logger.warning(
            "Ownership validation/calculation error: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    except Exception:
        logger.exception(
            "Unexpected production ownership calculation error"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Vehicle ownership calculation failed. "
                "Please try again."
            ),
        )


@router.get(
    "/health",
)
async def ownership_health():
    """
    Ownership module health endpoint.
    """

    return {
        "status": "ok",
        "module": "ownership",
        "calculation_source": (
            "calculate_vehicle_running_cost_v2"
        ),
        "vehicle_source": "vehicle_crsp",
    }
