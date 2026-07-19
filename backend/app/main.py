# backend/app/main.py - Add this section where routers are registered

# ─── Include Routers ───────────────────────────────────────────────
api_prefix = getattr(settings, "API_V1_PREFIX", "/api/v1")

app.include_router(auth_router, prefix=api_prefix + "/auth", tags=["Authentication"])
app.include_router(vehicles_router, prefix=api_prefix + "/vehicles", tags=["Vehicles"])
app.include_router(valuation_router, prefix=api_prefix + "/valuation", tags=["Valuation"])
app.include_router(mileage_router, prefix=api_prefix + "/mileage", tags=["Mileage"])
app.include_router(running_cost_router, prefix=api_prefix + "/running-cost", tags=["Running Cost"])
app.include_router(ownership_router, prefix=api_prefix + "/ownership", tags=["Ownership"])
app.include_router(fuel_router, prefix=api_prefix + "/fuel", tags=["Fuel"])
app.include_router(admin_router, prefix=api_prefix + "/admin", tags=["Admin"])
app.include_router(reports_router, prefix=api_prefix + "/reports", tags=["Reports"])

# Include M-Pesa router only if available
if mpesa_router is not None:
    app.include_router(mpesa_router, prefix=api_prefix, tags=["M-Pesa"])
    logger.info("✅ M-Pesa router registered")
else:
    logger.warning("⚠️ M-Pesa router not available - payment endpoints disabled")

logger.info("✅ All routers registered")
