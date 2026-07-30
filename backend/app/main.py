"""
Auto-D Kenya API — entry point.

Wires together the four independent service routers so each stays a
clean, self-contained file while sharing one FastAPI app, CORS policy
and Supabase connection.

Run locally with:
    uvicorn main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routers import mpesa, ownership, running_cost, valuation

settings = get_settings()

app = FastAPI(
    title="Auto-D Kenya API",
    version="1.0.0",
    description=(
        "Backend services for Auto-D Kenya: vehicle valuation, mileage/"
        "running-cost, cost-of-ownership (TCO) and M-Pesa payments."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path prefixes match exactly what each existing frontend already calls,
# so none of the three HTML files need to change.
app.include_router(mpesa.router, prefix="/api/v1/mpesa/mpesa", tags=["M-Pesa"])
app.include_router(valuation.router, prefix="/api/v1/valuation", tags=["Valuation"])
app.include_router(running_cost.router, prefix="/api/v1/running-cost", tags=["Running Cost"])
app.include_router(ownership.router, prefix="/api/v1/ownership", tags=["Ownership / TCO"])


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "auto-d-kenya-api"}
