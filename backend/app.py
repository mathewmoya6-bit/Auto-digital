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

# ─── Admin Endpoints ─────────────────────────────────────────────
POST /api/admin/login             - Admin login
GET  /api/admin/stats             - Dashboard statistics
GET  /api/admin/fuel              - Get fuel prices
PUT  /api/admin/fuel              - Update fuel price
GET  /api/admin/services          - Get service pricing
PUT  /api/admin/services          - Update service price
GET  /api/admin/settings          - Get engine settings
PUT  /api/admin/settings          - Update engine setting
POST /api/admin/settings/reset    - Reset all settings
GET  /api/admin/logs              - Get activity logs
POST /api/admin/logs              - Add activity log
GET  /api/admin/validate          - Validate admin session
"""

from flask import Flask, jsonify, request, session
from flask_cors import CORS
import os
import logging
import secrets
from datetime import datetime, timedelta
from dotenv import load_dotenv
import threading
import sys

# ─── Load Environment ──────────────────────────────────────────────
load_dotenv()

# ─── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("auto-d-backend")

# ─── Import Services (with fallback for missing modules) ──────────
try:
    from services.mileage_service import MileageService
    logger.info("✅ MileageService imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ MileageService import failed: {e}")
    MileageService = None

try:
    from services.valuation_service import ValuationService
    logger.info("✅ ValuationService imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ ValuationService import failed: {e}")
    ValuationService = None

# ─── Import OwnershipService with fallback ──────────────────────
try:
    from services.ownership_service import OwnershipService
    logger.info("✅ OwnershipService imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ OwnershipService (class) import failed: {e}")
    try:
        from services.ownership_service import ownership_service as OwnershipService
        logger.info("✅ ownership_service (function) imported as fallback")
    except ImportError as e2:
        logger.warning(f"⚠️ ownership_service fallback import failed: {e2}")
        OwnershipService = None

# ─── Import Vehicle Data ──────────────────────────────────────────
try:
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
    logger.info("✅ Vehicle data imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ Vehicle data import failed: {e}")
    VEHICLE_DATABASE = {}
    get_all_makes = lambda: []
    get_models_for_make = lambda x: []
    get_vehicle_data = lambda x, y: None
    get_categories = lambda: []
    get_makes_by_category = lambda x: []
    search_vehicles = lambda x: []
    get_vehicle_price = lambda x, y: None

# ─── Import M-Pesa (if available) ──────────────────────────────────
try:
    from mpesa import (
        MpesaAPIError,
        MpesaClient,
        MpesaConfigError
    )
    MPESA_AVAILABLE = True
    logger.info("✅ M-Pesa module imported successfully")
except ImportError:
    MPESA_AVAILABLE = False
    logger.warning("⚠️ M-Pesa module not available - M-Pesa endpoints disabled")

# ─── Flask App ────────────────────────────────────────────────────
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "development-secret")
app.config["SESSION_TYPE"] = "filesystem"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)

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

# ─── Initialize Services (with fallback) ──────────────────────────
if MileageService:
    mileage_service = MileageService()
else:
    mileage_service = None
    logger.warning("⚠️ MileageService not available")

if ValuationService:
    valuation_service = ValuationService()
else:
    valuation_service = None
    logger.warning("⚠️ ValuationService not available")

if OwnershipService:
    # Check if it's a class or function
    if callable(OwnershipService) and not isinstance(OwnershipService, type):
        # It's a function, not a class
        ownership_service = OwnershipService
    else:
        try:
            ownership_service = OwnershipService()
        except TypeError:
            # It's a function
            ownership_service = OwnershipService
else:
    ownership_service = None
    logger.warning("⚠️ OwnershipService not available")

logger.info("✅ Services initialized")

# ─── Temporary Storage ──────────────────────────────────────────
transactions = {}
transactions_lock = threading.Lock()

# ─── Admin Storage ──────────────────────────────────────────────
ADMIN_CREDENTIALS = {
    "username": os.getenv("ADMIN_USERNAME", "admin"),
    "password": os.getenv("ADMIN_PASSWORD", "admin123")
}

# Fuel prices (in-memory, can be moved to database)
FUEL_PRICES = {
    "petrol": {"price": 182.00, "date": datetime.now().strftime("%Y-%m-%d")},
    "diesel": {"price": 170.00, "date": datetime.now().strftime("%Y-%m-%d")},
    "electric": {"price": 30.00, "date": datetime.now().strftime("%Y-%m-%d")},
    "lpg": {"price": 120.00, "date": datetime.now().strftime("%Y-%m-%d")}
}

# Service pricing
SERVICE_PRICES = {
    "valuation": 150,
    "ownership": 200,
    "mileage": 100,
    "full_report": 350
}

# Engine settings
ENGINE_SETTINGS = {
    "depreciation_rate": 0.15,
    "insurance_rate": 0.045,
    "annual_mileage": 20000,
    "tyre_lifespan": 45000
}

# Activity logs
activity_logs = []
logs_lock = threading.Lock()

# Admin sessions
admin_sessions = {}


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
    """Calculate mileage and running cost"""
    if not mileage_service:
        return jsonify({"error": "Mileage service unavailable"}), 503
    
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
    """Calculate vehicle instant valuation"""
    if not valuation_service:
        return jsonify({"error": "Valuation service unavailable"}), 503
    
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
    """Calculate total cost of vehicle ownership"""
    if not ownership_service:
        return jsonify({"error": "Ownership service unavailable"}), 503
    
    data = request.get_json() or {}
    
    # Handle both class and function cases
    if callable(ownership_service):
        if isinstance(ownership_service, type):
            # It's a class
            result = ownership_service().calculate(data)
        else:
            # It's a function
            result = ownership_service(data)
    else:
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
# ADMIN AUTHENTICATION ENDPOINTS
# ──────────────────────────────────────────────────────────────────

def generate_admin_token():
    """Generate a secure admin session token"""
    return secrets.token_urlsafe(32)

def validate_admin_token(token):
    """Validate admin session token"""
    if not token:
        return False
    session_data = admin_sessions.get(token)
    if not session_data:
        return False
    # Check if session expired (24 hours)
    if datetime.now() > session_data.get("expires_at", datetime.now()):
        del admin_sessions[token]
        return False
    return True

def admin_required(f):
    """Decorator for admin-only endpoints"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not validate_admin_token(token):
            return jsonify({"error": "Unauthorized", "success": False}), 401
        return f(*args, **kwargs)
    return decorated_function


@app.post("/api/admin/login")
def admin_login():
    """Admin login endpoint"""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    
    if username == ADMIN_CREDENTIALS["username"] and password == ADMIN_CREDENTIALS["password"]:
        token = generate_admin_token()
        admin_sessions[token] = {
            "username": username,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24)
        }
        add_admin_log(f"🔑 Admin logged in: {username}", username)
        return jsonify({
            "success": True,
            "token": token,
            "username": username,
            "expires_in": 86400  # 24 hours in seconds
        })
    
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.get("/api/admin/validate")
def admin_validate():
    """Validate admin session"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if validate_admin_token(token):
        session_data = admin_sessions.get(token, {})
        return jsonify({
            "success": True,
            "valid": True,
            "username": session_data.get("username", "admin")
        })
    return jsonify({"success": False, "valid": False}), 401


# ──────────────────────────────────────────────────────────────────
# ADMIN DASHBOARD ENDPOINTS
# ──────────────────────────────────────────────────────────────────

@app.get("/api/admin/stats")
@admin_required
def admin_stats():
    """Get dashboard statistics"""
    return jsonify({
        "success": True,
        "data": {
            "valuations": 1247,
            "revenue": 187450,
            "users": 856,
            "apiCalls": 342
        }
    })

@app.get("/api/admin/fuel")
@admin_required
def admin_get_fuel():
    """Get current fuel prices"""
    return jsonify({
        "success": True,
        "data": FUEL_PRICES
    })

@app.put("/api/admin/fuel")
@admin_required
def admin_update_fuel():
    """Update fuel price"""
    data = request.get_json() or {}
    fuel_type = data.get("fuel_type")
    price = data.get("price")
    
    if not fuel_type or price is None:
        return jsonify({"success": False, "error": "fuel_type and price are required"}), 400
    
    if fuel_type not in FUEL_PRICES:
        return jsonify({"success": False, "error": f"Invalid fuel type: {fuel_type}"}), 400
    
    try:
        price = float(price)
        if price < 0:
            raise ValueError
    except ValueError:
        return jsonify({"success": False, "error": "Price must be a positive number"}), 400
    
    FUEL_PRICES[fuel_type]["price"] = price
    FUEL_PRICES[fuel_type]["date"] = datetime.now().strftime("%Y-%m-%d")
    
    add_admin_log(f"⛽ {fuel_type.capitalize()} price updated to KES {price:.2f}", 
                  request.headers.get('X-Admin-User', 'admin'))
    
    return jsonify({
        "success": True,
        "data": FUEL_PRICES[fuel_type],
        "message": f"{fuel_type.capitalize()} price updated successfully"
    })

@app.get("/api/admin/services")
@admin_required
def admin_get_services():
    """Get service pricing"""
    return jsonify({
        "success": True,
        "data": SERVICE_PRICES
    })

@app.put("/api/admin/services")
@admin_required
def admin_update_service():
    """Update service price"""
    data = request.get_json() or {}
    service_type = data.get("service_type")
    price = data.get("price")
    
    if not service_type or price is None:
        return jsonify({"success": False, "error": "service_type and price are required"}), 400
    
    if service_type not in SERVICE_PRICES:
        return jsonify({"success": False, "error": f"Invalid service type: {service_type}"}), 400
    
    try:
        price = int(price)
        if price < 0:
            raise ValueError
    except ValueError:
        return jsonify({"success": False, "error": "Price must be a positive integer"}), 400
    
    SERVICE_PRICES[service_type] = price
    
    service_names = {
        "valuation": "Instant Valuation",
        "ownership": "Ownership Cost Report",
        "mileage": "Mileage Report",
        "full_report": "Full Vehicle Report"
    }
    
    add_admin_log(f"💳 {service_names.get(service_type, service_type)} price updated to KES {price}", 
                  request.headers.get('X-Admin-User', 'admin'))
    
    return jsonify({
        "success": True,
        "data": SERVICE_PRICES,
        "message": f"Service price updated successfully"
    })

@app.get("/api/admin/settings")
@admin_required
def admin_get_settings():
    """Get engine settings"""
    return jsonify({
        "success": True,
        "data": ENGINE_SETTINGS
    })

@app.put("/api/admin/settings")
@admin_required
def admin_update_setting():
    """Update engine setting"""
    data = request.get_json() or {}
    key = data.get("key")
    value = data.get("value")
    
    if not key or value is None:
        return jsonify({"success": False, "error": "key and value are required"}), 400
    
    if key not in ENGINE_SETTINGS:
        return jsonify({"success": False, "error": f"Invalid setting key: {key}"}), 400
    
    try:
        value = float(value)
        if value < 0:
            raise ValueError
    except ValueError:
        return jsonify({"success": False, "error": "Value must be a positive number"}), 400
    
    ENGINE_SETTINGS[key] = value
    
    setting_names = {
        "depreciation_rate": "Depreciation Rate",
        "insurance_rate": "Insurance Rate",
        "annual_mileage": "Annual Mileage",
        "tyre_lifespan": "Tyre Lifespan"
    }
    
    add_admin_log(f"⚙️ {setting_names.get(key, key)} updated to {value}", 
                  request.headers.get('X-Admin-User', 'admin'))
    
    return jsonify({
        "success": True,
        "data": ENGINE_SETTINGS,
        "message": f"Setting updated successfully"
    })

@app.post("/api/admin/settings/reset")
@admin_required
def admin_reset_settings():
    """Reset all settings to defaults"""
    default_settings = {
        "depreciation_rate": 0.15,
        "insurance_rate": 0.045,
        "annual_mileage": 20000,
        "tyre_lifespan": 45000
    }
    ENGINE_SETTINGS.update(default_settings)
    
    add_admin_log("⚠️ All settings reset to default", 
                  request.headers.get('X-Admin-User', 'admin'))
    
    return jsonify({
        "success": True,
        "data": ENGINE_SETTINGS,
        "message": "All settings reset to default"
    })

@app.get("/api/admin/logs")
@admin_required
def admin_get_logs():
    """Get activity logs"""
    limit = request.args.get('limit', 50, type=int)
    with logs_lock:
        logs = activity_logs[:limit]
    return jsonify({
        "success": True,
        "data": logs,
        "count": len(logs)
    })

@app.post("/api/admin/logs")
@admin_required
def admin_add_log_endpoint():
    """Add activity log (internal)"""
    data = request.get_json() or {}
    action = data.get("action", "Unknown action")
    user = data.get("user", "system")
    add_admin_log(action, user)
    return jsonify({"success": True})

def add_admin_log(action, user="system"):
    """Helper to add admin log"""
    with logs_lock:
        log_entry = {
            "action": action,
            "user": user,
            "time": datetime.now().strftime("%I:%M %p"),
            "timestamp": datetime.now().isoformat()
        }
        activity_logs.insert(0, log_entry)
        # Keep only last 100 logs
        if len(activity_logs) > 100:
            activity_logs.pop()


# ──────────────────────────────────────────────────────────────────
# HEALTH CHECK ENDPOINT
# ──────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "service": "auto-d-backend",
        "version": "3.1.0",
        "services": {
            "mileage": "active" if mileage_service else "unavailable",
            "valuation": "active" if valuation_service else "unavailable",
            "ownership": "active" if ownership_service else "unavailable"
        },
        "vehicle_categories": get_categories(),
        "mpesa_available": MPESA_AVAILABLE,
        "admin_enabled": True,
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
    logger.info(f"🔑 Admin: Enabled at /api/admin/login")
    app.run(host="0.0.0.0", port=port, debug=False)
