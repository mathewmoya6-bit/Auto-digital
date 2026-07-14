"""
Auto-D Kenya Flask Backend - Production Ready

Endpoints:
POST /api/mpesa/stkpush           - Start M-Pesa STK Push payment
POST /api/mpesa/callback          - Receive Safaricom payment callback
GET  /api/mpesa/status/<checkout_id> - Check payment status

GET  /api/health                  - Health check
GET  /api/vehicles/makes          - Get all vehicle makes/brands
GET  /api/vehicles/models/<make>  - Get models for a make
GET  /api/vehicles/<make>/<model> - Get vehicle details
GET  /api/vehicles/categories     - Get all vehicle categories
GET  /api/vehicles/search         - Search for vehicles
GET  /api/vehicles/database       - Get full vehicle database

POST /api/service/mileage         - Calculate mileage cost
POST /api/service/valuation       - Calculate vehicle valuation
POST /api/service/ownership       - Calculate ownership cost
"""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

# Import vehicle database
from vehicle_data import (
    VEHICLE_DATABASE,
    get_all_makes,
    get_models_for_make,
    get_vehicle_data,
    get_categories,
    get_makes_by_category,
    search_vehicles,
    get_vehicle_price
)

# Import M-Pesa (if available)
try:
    from mpesa import (
        MpesaAPIError,
        MpesaClient,
        MpesaConfigError
    )
    MPESA_AVAILABLE = True
except ImportError:
    MPESA_AVAILABLE = False
    logging.warning("M-Pesa module not available - M-Pesa endpoints disabled")

# Load local .env during development
load_dotenv()

# ─── LOGGING ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("auto-d-backend")

# ─── FLASK APP ──────────────────────────────────────────────────
app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "FLASK_SECRET_KEY",
    "development-secret-change-in-production"
)

# ─── CORS CONFIGURATION ────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "https://auto-d.meipressgroup.com,http://localhost:3000,http://localhost:5000,https://auto-d-kenya-backend.onrender.com"
).split(",")

CORS(
    app,
    origins=ALLOWED_ORIGINS,
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

# ─── TEMPORARY STORAGE ──────────────────────────────────────────
transactions = {}
transactions_lock = threading.Lock()


# ──────────────────────────────────────────────────────────────
# VEHICLE DATA ENDPOINTS
# ──────────────────────────────────────────────────────────────

@app.get("/api/vehicles/makes")
def get_makes_endpoint():
    """Get all vehicle makes/brands"""
    category = request.args.get('category')
    if category:
        makes = get_makes_by_category(category)
    else:
        makes = get_all_makes()
    return jsonify({
        "success": True,
        "makes": makes,
        "count": len(makes),
        "timestamp": datetime.utcnow().isoformat()
    })

@app.get("/api/vehicles/models/<make>")
def get_models_endpoint(make):
    """Get all models for a specific make"""
    models = get_models_for_make(make)
    if not models:
        return jsonify({
            "success": False,
            "error": f"Make '{make}' not found"
        }), 404
    return jsonify({
        "success": True,
        "make": make,
        "models": models,
        "count": len(models)
    })

@app.get("/api/vehicles/<make>/<model>")
def get_vehicle_endpoint(make, model):
    """Get detailed data for a specific vehicle"""
    data = get_vehicle_data(make, model)
    if not data:
        return jsonify({
            "success": False,
            "error": f"Vehicle '{make} {model}' not found"
        }), 404
    return jsonify({
        "success": True,
        "make": make,
        "model": model,
        "data": data
    })

@app.get("/api/vehicles/categories")
def get_categories_endpoint():
    """Get all vehicle categories"""
    categories = get_categories()
    return jsonify({
        "success": True,
        "categories": categories,
        "count": len(categories)
    })

@app.get("/api/vehicles/search")
def search_vehicles_endpoint():
    """Search for vehicles by make or model name"""
    query = request.args.get('q', '')
    if not query:
        return jsonify({
            "success": False,
            "error": "Search query required (use ?q=search_term)"
        }), 400
    results = search_vehicles(query)
    return jsonify({
        "success": True,
        "query": query,
        "results": results,
        "count": len(results)
    })

@app.get("/api/vehicles/database")
def get_full_database_endpoint():
    """Get full vehicle database"""
    return jsonify({
        "success": True,
        "database": VEHICLE_DATABASE,
        "timestamp": datetime.utcnow().isoformat()
    })

@app.get("/api/vehicles/price/<make>/<model>")
def get_vehicle_price_endpoint(make, model):
    """Get price for a specific vehicle"""
    price = get_vehicle_price(make, model)
    if price is None:
        return jsonify({
            "success": False,
            "error": f"Vehicle '{make} {model}' not found"
        }), 404
    return jsonify({
        "success": True,
        "make": make,
        "model": model,
        "price": price
    })


# ──────────────────────────────────────────────────────────────
# SERVICE CALCULATION ENDPOINTS
# ──────────────────────────────────────────────────────────────

def calculate_mileage_cost(distance_km, fuel_type="petrol", fuel_consumption=None,
                           maintenance_per_km=0, insurance=0, tax=0):
    """Calculate the cost of traveling a given distance."""
    fuel_prices = {
        "petrol": 180,
        "diesel": 170,
        "electric": 30,
        "hybrid": 150,
        "lpg": 120
    }

    default_consumption = {
        "petrol": 8,
        "diesel": 7,
        "electric": 15,
        "hybrid": 20,
        "lpg": 10
    }

    if fuel_consumption is None:
        fuel_consumption = default_consumption.get(fuel_type, 8)

    price_per_unit = fuel_prices.get(fuel_type, 180)

    fuel_cost = (distance_km / 100) * fuel_consumption * price_per_unit
    maintenance_cost = distance_km * maintenance_per_km
    insurance_cost = insurance
    tax_cost = tax

    total_cost = fuel_cost + maintenance_cost + insurance_cost + tax_cost

    return {
        "distance_km": distance_km,
        "fuel_type": fuel_type,
        "fuel_consumption": fuel_consumption,
        "fuel_cost": round(fuel_cost, 2),
        "maintenance_cost": round(maintenance_cost, 2),
        "insurance_cost": round(insurance_cost, 2),
        "tax_cost": round(tax_cost, 2),
        "total_cost": round(total_cost, 2),
        "cost_per_km": round(total_cost / distance_km if distance_km > 0 else 0, 2)
    }


def calculate_vehicle_value(purchase_price, age_years, depreciation_rate=0.15):
    """Calculate current vehicle value using declining balance depreciation."""
    try:
        purchase_price = float(purchase_price)
        age_years = float(age_years)
        depreciation_rate = float(depreciation_rate)
    except (ValueError, TypeError):
        return {"error": "Invalid input values"}

    if purchase_price <= 0 or age_years < 0:
        return {"error": "Invalid input values"}

    current_value = purchase_price * ((1 - depreciation_rate) ** age_years)
    total_depreciation = purchase_price - current_value

    return {
        "purchase_price": purchase_price,
        "age_years": age_years,
        "depreciation_rate": depreciation_rate,
        "current_value": round(current_value, 2),
        "total_depreciation": round(total_depreciation, 2),
        "value_retained": round((current_value / purchase_price) * 100, 2)
    }


def calculate_ownership_cost(purchase_price, years_owned, fuel_cost,
                             maintenance_cost, insurance_cost, taxes,
                             resale_value=0):
    """Calculate total cost of vehicle ownership."""
    try:
        purchase_price = float(purchase_price)
        years_owned = float(years_owned)
        fuel_cost = float(fuel_cost)
        maintenance_cost = float(maintenance_cost)
        insurance_cost = float(insurance_cost)
        taxes = float(taxes)
        resale_value = float(resale_value)
    except (ValueError, TypeError):
        return {"error": "Invalid input values"}

    if purchase_price < 0 or years_owned < 0:
        return {"error": "Invalid input values"}

    total_operating_cost = fuel_cost + maintenance_cost + insurance_cost + taxes
    total_cost = purchase_price + total_operating_cost - resale_value
    annual_cost = total_cost / years_owned if years_owned > 0 else 0

    return {
        "purchase_price": purchase_price,
        "years_owned": years_owned,
        "fuel_cost": round(fuel_cost, 2),
        "maintenance_cost": round(maintenance_cost, 2),
        "insurance_cost": round(insurance_cost, 2),
        "taxes": round(taxes, 2),
        "resale_value": round(resale_value, 2),
        "total_operating_cost": round(total_operating_cost, 2),
        "total_cost": round(total_cost, 2),
        "annual_cost": round(annual_cost, 2),
        "cost_per_day": round(annual_cost / 365, 2) if years_owned > 0 else 0
    }


@app.post("/api/service/mileage")
def mileage():
    """Calculate mileage cost"""
    data = request.get_json() or {}

    distance_km = data.get("distance_km")
    if distance_km is None:
        return jsonify({"error": "distance_km is required"}), 400

    try:
        distance_km = float(distance_km)
        if distance_km <= 0:
            raise ValueError
    except ValueError:
        return jsonify({"error": "distance_km must be a positive number"}), 400

    result = calculate_mileage_cost(
        distance_km=distance_km,
        fuel_type=data.get("fuel_type", "petrol"),
        fuel_consumption=data.get("fuel_consumption"),
        maintenance_per_km=data.get("maintenance_per_km", 0),
        insurance=data.get("insurance", 0),
        tax=data.get("tax", 0)
    )

    return jsonify({"success": True, "data": result})


@app.post("/api/service/valuation")
def valuation():
    """Calculate vehicle valuation"""
    data = request.get_json() or {}

    purchase_price = data.get("purchase_price")
    age_years = data.get("age_years")

    if purchase_price is None:
        return jsonify({"error": "purchase_price is required"}), 400
    if age_years is None:
        return jsonify({"error": "age_years is required"}), 400

    try:
        purchase_price = float(purchase_price)
        age_years = float(age_years)
        if purchase_price <= 0 or age_years < 0:
            raise ValueError
    except ValueError:
        return jsonify({"error": "purchase_price must be positive and age_years must be non-negative"}), 400

    result = calculate_vehicle_value(
        purchase_price=purchase_price,
        age_years=age_years,
        depreciation_rate=data.get("depreciation_rate", 0.15)
    )

    if "error" in result:
        return jsonify(result), 400

    return jsonify({"success": True, "data": result})


@app.post("/api/service/ownership")
def ownership():
    """Calculate ownership cost"""
    data = request.get_json() or {}

    # Check if using vehicle database or manual input
    make = data.get("make")
    model = data.get("model")

    if make and model:
        # Use vehicle database
        vehicle = get_vehicle_data(make, model)
        if not vehicle:
            return jsonify({"error": f"Vehicle '{make} {model}' not found"}), 404

        base_price = vehicle.get("price", 0)
        years_owned = data.get("years_owned", 5)
        annual_mileage = data.get("annual_mileage", 20000)

        # Calculate using vehicle data
        result = calculate_ownership_cost(
            purchase_price=base_price,
            years_owned=years_owned,
            fuel_cost=annual_mileage * 182 / vehicle.get("fuel_efficiency", 10),
            maintenance_cost=annual_mileage * vehicle.get("maintenance_per_km", 10) * years_owned,
            insurance_cost=base_price * 0.045 * years_owned,
            taxes=5000 * years_owned,
            resale_value=base_price * 0.3
        )

        if "error" in result:
            return jsonify(result), 400

        return jsonify({"success": True, "data": result})

    else:
        # Manual input
        required_fields = ["purchase_price", "years_owned", "fuel_cost",
                          "maintenance_cost", "insurance_cost", "taxes"]

        missing_fields = [field for field in required_fields if data.get(field) is None]
        if missing_fields:
            return jsonify({
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400

        try:
            purchase_price = float(data.get("purchase_price"))
            years_owned = float(data.get("years_owned"))
            fuel_cost = float(data.get("fuel_cost"))
            maintenance_cost = float(data.get("maintenance_cost"))
            insurance_cost = float(data.get("insurance_cost"))
            taxes = float(data.get("taxes"))
            resale_value = float(data.get("resale_value", 0))

            if purchase_price < 0 or years_owned < 0:
                raise ValueError
        except ValueError:
            return jsonify({"error": "All numeric fields must be valid positive numbers"}), 400

        result = calculate_ownership_cost(
            purchase_price=purchase_price,
            years_owned=years_owned,
            fuel_cost=fuel_cost,
            maintenance_cost=maintenance_cost,
            insurance_cost=insurance_cost,
            taxes=taxes,
            resale_value=resale_value
        )

        if "error" in result:
            return jsonify(result), 400

        return jsonify({"success": True, "data": result})


# ──────────────────────────────────────────────────────────────
# M-PESA PAYMENT ENDPOINTS (Conditional)
# ──────────────────────────────────────────────────────────────

def get_client():
    if not MPESA_AVAILABLE:
        raise MpesaConfigError("M-Pesa module not available")
    try:
        return MpesaClient()
    except MpesaConfigError as e:
        logger.error(e)
        raise


@app.get("/api/health")
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "service": "auto-d-backend",
        "version": "2.0",
        "vehicle_categories": get_categories(),
        "mpesa_available": MPESA_AVAILABLE,
        "timestamp": datetime.utcnow().isoformat()
    })


@app.post("/api/mpesa/stkpush")
def stkpush():
    """Initiate M-Pesa STK Push payment"""
    if not MPESA_AVAILABLE:
        return jsonify({"error": "M-Pesa service unavailable"}), 503

    data = request.get_json() or {}

    phone = data.get("phone")
    amount = data.get("amount")
    account_reference = data.get("account_reference", "AUTO-D")
    description = data.get("description", "Vehicle valuation")

    if not phone or not amount:
        return jsonify({"error": "phone and amount are required"}), 400

    try:
        amount = int(float(amount))
        if amount <= 0:
            raise ValueError
    except ValueError:
        return jsonify({"error": "Invalid amount"}), 400

    try:
        client = get_client()
        result = client.stk_push(
            phone_number=phone,
            amount=amount,
            account_reference=account_reference,
            transaction_desc=description
        )
    except MpesaConfigError as e:
        return jsonify({"error": str(e)}), 500
    except MpesaAPIError as e:
        return jsonify({"error": str(e)}), 502

    checkout_id = result.get("CheckoutRequestID")

    with transactions_lock:
        transactions[checkout_id] = {
            "status": "pending",
            "phone": client.normalize_phone(phone),
            "amount": amount,
            "timestamp": datetime.utcnow().isoformat()
        }

    return jsonify({
        "message": "STK Push sent",
        "checkout_request_id": checkout_id
    })


@app.post("/api/mpesa/callback")
def mpesa_callback():
    """Handle M-Pesa payment callback"""
    if not MPESA_AVAILABLE:
        return jsonify({"error": "M-Pesa service unavailable"}), 503

    payload = request.get_json() or {}

    logger.info("M-Pesa callback: %s", payload)

    callback = payload.get("Body", {}).get("stkCallback", {})
    checkout_id = callback.get("CheckoutRequestID")
    result_code = callback.get("ResultCode")
    result_desc = callback.get("ResultDesc")

    receipt = None
    amount = None

    if result_code == 0:
        items = callback.get("CallbackMetadata", {}).get("Item", [])
        metadata = {
            item.get("Name"): item.get("Value")
            for item in items
        }
        receipt = metadata.get("MpesaReceiptNumber")
        amount = metadata.get("Amount")

    with transactions_lock:
        transactions[checkout_id] = {
            "status": "success" if result_code == 0 else "failed",
            "result_code": result_code,
            "description": result_desc,
            "receipt": receipt,
            "amount": amount,
            "timestamp": datetime.utcnow().isoformat()
        }

    return jsonify({
        "ResultCode": 0,
        "ResultDesc": "Accepted"
    })


@app.get("/api/mpesa/status/<checkout_id>")
def payment_status(checkout_id):
    """Check payment status"""
    with transactions_lock:
        payment = transactions.get(checkout_id)

    if not payment:
        return jsonify({"status": "unknown"}), 404

    return jsonify(payment)


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )


# For Gunicorn
if __name__ != "__main__":
    app.config["ENV"] = "production"
