"""
app/api/v1/scraper.py
======================
Admin-only endpoints for triggering scraper jobs (autochek/jiji/carapi via
scrapers/worker.py) and checking which scrapers are available.

NOTE: This is a *separate* namespace from whatever app/api/v1/market.py's
existing /market/scrape endpoint does (that one lists Jiji/Cheki/Autochek/
BeepBeep/PigiaMe as sources - a different registry than worker.py's three).
The two haven't been reconciled - if they're duplicating effort, that's a
decision for you to make once you can compare both side by side.

Registration in app/main.py (matching your existing router pattern, e.g.
the mpesa/price_alignment/market try/except blocks):

    try:
        from app.api.v1.scraper import router as scraper_router
        SCRAPER_ROUTER_LOADED = True
    except ImportError as e:
        SCRAPER_ROUTER_LOADED = False
        scraper_router = None

    if SCRAPER_ROUTER_LOADED and scraper_router is not None:
        app.include_router(scraper_router, prefix=f"{api_prefix}/scraper", tags=["Scraper Jobs"])

ASSUMPTION (flag if wrong): admin auth delegates to
`supabase.auth.get_user(token)` then checks `app_metadata.role == "admin"`
/ `app_metadata.is_admin`. Swap `require_admin()` below if admin access is
actually gated differently elsewhere in the app (e.g. a DB table, or
whatever app/api/v1/auth.py already does - I don't have that file's
content, so I couldn't match it directly).

Jobs run via FastAPI BackgroundTasks (fire-and-forget) rather than a real
queue. There's no `scraper_jobs` table in your schema yet, so this can't
report status after acceptance - only server logs show the outcome. Say
the word if you want a status-polling table added.

Endpoints:
    GET  /available   -> list known scraper names (from worker.py's registry)
    POST /run          -> trigger a scraper job (background)
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.core.database import supabase
from scrapers.worker import SCRAPER_REGISTRY, run_job
from services.scraper_logger import get_logger

logger = get_logger(__name__)

# No prefix/tags baked in here - main.py applies
# prefix=f"{api_prefix}/scraper" and tags=["Scraper Jobs"] at include_router,
# matching how auth/vehicles/valuation/etc. routers are wired.
router = APIRouter()

security = HTTPBearer()


# ---------------------------------------------------------------------------
# Auth - swap this out for however admin access is actually checked elsewhere
# in the app. This mirrors the "delegate to supabase.auth.get_user()" pattern
# rather than doing local JWT decoding, per your existing auth fix.
# ---------------------------------------------------------------------------
async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    try:
        user_response = supabase.auth.get_user(token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    user = getattr(user_response, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    app_metadata = getattr(user, "app_metadata", None) or {}
    is_admin = app_metadata.get("role") == "admin" or app_metadata.get("is_admin") is True
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return {"id": user.id, "email": getattr(user, "email", None)}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ScraperRunRequest(BaseModel):
    scraper: str = Field(..., description="One of: " + ", ".join(SCRAPER_REGISTRY))
    max_listings: int = Field(100, ge=1, le=1000, description="Ignored by carapi")
    kwargs: dict[str, Any] = Field(default_factory=dict, description="Scraper constructor args")


class ScraperRunResponse(BaseModel):
    accepted: bool
    scraper: str
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/available")
async def list_available_scrapers(admin: dict = Depends(require_admin)) -> dict:
    return {"scrapers": list(SCRAPER_REGISTRY)}


def _run_job_and_log(payload: dict) -> None:
    """Runs in the background; run_job() itself never raises, so this is
    just here to keep the background-task call site simple."""
    result = run_job(payload)
    if result.get("ok"):
        logger.info("Background scraper job succeeded: %s", result)
    else:
        logger.error("Background scraper job failed: %s", result)


@router.post("/run", response_model=ScraperRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_scraper_run(
    body: ScraperRunRequest,
    background_tasks: BackgroundTasks,
    admin: dict = Depends(require_admin),
) -> ScraperRunResponse:
    if body.scraper not in SCRAPER_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown scraper '{body.scraper}'. Known: {list(SCRAPER_REGISTRY)}",
        )

    payload = {
        "scraper": body.scraper,
        "max_listings": body.max_listings,
        "kwargs": body.kwargs,
    }

    background_tasks.add_task(_run_job_and_log, payload)
    logger.info("Scraper job accepted by admin %s: %s", admin.get("email"), payload)

    return ScraperRunResponse(
        accepted=True,
        scraper=body.scraper,
        message="Job accepted and running in the background. Check server logs for the result.",
    )
