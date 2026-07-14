"""
Auto-D Kenya Flask Backend - Production Ready
Complete vehicle intelligence platform

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

POST /api/service/mileage         - Calculate mileage cost (mileage.html)
POST /api/service/valuation       - Calculate vehicle valuation (instant-value.html)
POST /api/service/ownership       - Calculate ownership cost (ownership-cost.html)
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# ─── Import Services ──────────────────────────────────────────────
from services.mileage_service import MileageService
from services.valuation_service import ValuationService
from services.ownership_service import OwnershipService

# ─── Import Vehicle Data ──────────────────────────────────────────
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

# ─── Import M-Pesa (if available) ──────────────────────────────────
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

# ─── Load Environment ──────────────────────────────────────────────
load_dotenv()

# ─── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("auto-d-backend")

# ─── Flask App ────────────────────────────────────────────────────
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "development-secret")

# ─── CORS Configuration ────────────────────────────────────────────
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

# ─── Initialize Services ──────────────────────────────────────────
# Each service handles its specific calculation logic
mileage_service = MileageService()
valuation_service = ValuationService()
ownership_service = OwnershipService()

logger.info("✅ Services initialized: Mileage, Valuation, Ownership")

# ─── Temporary Storage for M-Pesa ──────────────────────────────────
transactions = {}
import threading
transactions_lock = threading.Lock()


# ──────────────────────────────────────────────────────────────────
# VEHICLE DATA ENDPOINTS
# ──────────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────────
# SERVICE ENDPOINTS - Core Calculation Services
# ──────────────────────────────────────────────────────────────────

@app.post("/api/service/mileage")
def mileage():
    """
    Calculate mileage and running cost
    Used by: mileage.html
    Expected payload:
    {
        "distance_km": 100,
        "fuel_type": "petrol",
        "fuel_consumption": 8,
        "maintenance_per_km": 2,
        "insurance": 5000,
        "tax": 2000
    }
    """
    data = request.get_json() or {}
    result = mileage_service.calculate(data)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify({
        "success": True,
        "data": result,
        "service": "mileage",
        "timestamp": datetime.utcnow().isoformat()
    })


@app.post("/api/service/valuation")
def valuation():
    """
    Calculate vehicle instant valuation
    Used by: instant-value.html
    Expected payload:
    {
        "purchase_price": 5000000,
        "age_years": 3,
        "depreciation_rate": 0.15,
        "condition": "Good",
        "mileage": 45000,
        "location": "Nairobi"
    }
    """
    data = request.get_json() or {}
    result = valuation_service.calculate(data)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify({
        "success": True,
        "data": result,
        "service": "valuation",
        "timestamp": datetime.utcnow().isoformat()
    })


@app.post("/api/service/ownership")
def ownership():
    """
    Calculate total cost of vehicle ownership
    Used by: ownership-cost.html
    Expected payload (manual input):
    {
        "purchase_price": 5000000,
        "years_owned": 5,
        "fuel_cost": 360000,
        "maintenance_cost": 120000,
        "insurance_cost": 150000,
        "taxes": 50000,
        "resale_value": 2000000
    }
    OR (vehicle database):
    {
        "make": "toyota",
        "model": "prado",
        "years_owned": 5,
        "annual_mileage": 20000,
        "financed": true,
        "down_pct": 30,
        "interest_rate": 16,
        "loan_term": 4,
        "driving_locations": ["nairobi"]
    }
    """
    data = request.get_json() or {}
    result = ownership_service.calculate(data)
    
    if "error" in result:
        return jsonify(result), 400
    
    return jsonify({
        "success": True,
        "data": result,
        "service": "ownership",
        "timestamp": datetime.utcnow().isoformat()
    })


# ──────────────────────────────────────────────────────────────────
# HEALTH CHECK ENDPOINT
# ──────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "service": "auto-d-backend",
        "version": "3.0",
        "services": {
            "mileage": "active",
            "valuation": "active",
            "ownership": "active"
        },
        "vehicle_categories": get_categories(),
        "mpesa_available": MPESA_AVAILABLE,
        "timestamp": datetime.utcnow().isoformat()
    })


# ──────────────────────────────────────────────────────────────────
# M-PESA PAYMENT ENDPOINTS (Conditional)
# ──────────────────────────────────────────────────────────────────

def get_mpesa_client():
    if not MPESA_AVAILABLE:
        raise MpesaConfigError("M-Pesa module not available")
    try:
        return MpesaClient()
    except MpesaConfigError as e:
        logger.error(e)
        raise


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
        client = get_mpesa_client()
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


# ──────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    logger.info(f"🚀 Starting Auto-D Backend on port {port}")
    logger.info(f"📡 Services: Mileage, Valuation, Ownership")
    logger.info(f"🔌 M-Pesa: {'Available' if MPESA_AVAILABLE else 'Unavailable'}")
    app.run(host="0.0.0.0", port=port, debug=False)
