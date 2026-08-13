# app/modules/valuation/router.py - Update the calculate_valuation endpoint

@router.post("/calculate", response_model=ValuationReportResponse)
async def calculate_valuation(
    request: ValuationRequest,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Calculate vehicle valuation.
    
    Returns a comprehensive valuation report with:
    - Estimated market value
    - Retail, trade, and dealer values
    - Confidence score
    - Value range
    - Analysis and methodology
    """
    try:
        user_id = current_user.get("id") if current_user else None
        
        # ✅ FIXED: Get make and model from the request
        # The request has vehicle_crsp_id, but we need to look up make/model
        # from the vehicle_master_specs or use the ones from the request
        
        # First, try to get make and model from the vehicle_crsp_id
        make = None
        model = None
        variant_name = None
        
        try:
            # Try to get vehicle details from vehicle_master_specs
            variant_response = (
                valuation_service.supabase
                .table("vehicle_master_specs")
                .select("make_name, model_name, variant_name")
                .eq("variant_id", request.vehicle_crsp_id)
                .limit(1)
                .execute()
            )
            
            if variant_response.data:
                vehicle_data = variant_response.data[0]
                make = vehicle_data.get("make_name")
                model = vehicle_data.get("model_name")
                variant_name = vehicle_data.get("variant_name")
                logger.info(f"Found vehicle from master_specs: {make} {model} ({variant_name})")
        except Exception as e:
            logger.warning(f"Could not fetch vehicle details for CRSP {request.vehicle_crsp_id}: {e}")
        
        # If we still don't have make/model, try to get from vehicle_crsp_prices
        if not make or not model:
            try:
                crsp_response = (
                    valuation_service.supabase
                    .table("vehicle_crsp_prices")
                    .select("make, model")
                    .eq("id", request.vehicle_crsp_id)
                    .limit(1)
                    .execute()
                )
                
                if crsp_response.data:
                    crsp_data = crsp_response.data[0]
                    make = crsp_data.get("make") or make
                    model = crsp_data.get("model") or model
                    logger.info(f"Found vehicle from CRSP: {make} {model}")
            except Exception as e:
                logger.warning(f"Could not fetch CRSP details: {e}")
        
        # Call the service with all available data
        result = await valuation_service.calculate_valuation(
            vehicle_crsp_id=request.vehicle_crsp_id,
            year=request.manufacture_year,
            mileage=request.mileage_km,
            condition=request.condition_name,
            accident_history=request.accident_status,
            location=request.location_name,
            user_id=user_id,
            profit_margin_percent=request.profit_margin_percent,
            # ✅ Pass make and model if available
            make=make,
            model=model,
            fuel_type=request.vehicle_type,  # Use vehicle_type as fuel_type hint
            transmission=None,  # Not in request
            body_type=None,  # Not in request
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Valuation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Valuation failed: {str(e)}"
        )
