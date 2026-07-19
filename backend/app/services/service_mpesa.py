"""
M-Pesa Payment Service for Auto-D Kenya
Handles STK Push, payment status checks, and service unlocking
"""

import os
import json
import logging
import hashlib
import base64
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from uuid import uuid4

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from supabase import create_client, Client

# ─── Configuration ──────────────────────────────────────────────────────

# Supabase Configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://xgkdbithhlvoqjnqvfmj.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhna2RiaXRoaGx2b3FqbnF2Zm1qIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjY1MTg3NCwiZXhwIjoyMDk4MjI3ODc0fQ.5H4QRX8dRwPjVpK4QGJq5HrdM3w5cK8L3bR7hPq0dYk')

# M-Pesa Configuration - Using your shortcode
MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY', '')
MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET', '')
MPESA_PASSKEY = os.environ.get('MPESA_PASSKEY', '')
MPESA_SHORTCODE = os.environ.get('MPESA_SHORTCODE', '4095377')  # Your shortcode
MPESA_ENV = os.environ.get('MPESA_ENV', 'sandbox')  # 'sandbox' or 'production'

# API Base URLs
MPESA_BASE_URL = 'https://sandbox.safaricom.co.ke' if MPESA_ENV == 'sandbox' else 'https://api.safaricom.co.ke'
CALLBACK_BASE_URL = os.environ.get('CALLBACK_BASE_URL', 'https://auto-digital.onrender.com')

# ─── Logging ──────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Supabase Client ──────────────────────────────────────────────────

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── Flask App ───────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app, origins=['https://auto-d.meipressgroup.com', 'http://localhost:5500', 'https://auto-digital.onrender.com'])

# ─── Helper Functions ─────────────────────────────────────────────────

def get_access_token() -> Optional[str]:
    """
    Get M-Pesa API access token using OAuth 2.0 client credentials.
    """
    try:
        auth_url = f"{MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
        
        # Encode credentials
        credentials = f"{MPESA_CONSUMER_KEY}:{MPESA_CONSUMER_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(auth_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access_token')
            logger.info("✅ M-Pesa access token obtained successfully")
            return access_token
        else:
            logger.error(f"❌ Failed to get M-Pesa access token: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error getting M-Pesa access token: {str(e)}")
        return None


def get_timestamp() -> str:
    """Get current timestamp in M-Pesa format (YYYYMMDDHHmmSS)"""
    return datetime.now().strftime('%Y%m%d%H%M%S')


def generate_password(shortcode: str, passkey: str, timestamp: str) -> str:
    """
    Generate the base64 encoded password for M-Pesa STK Push.
    """
    data_to_encode = f"{shortcode}{passkey}{timestamp}"
    encoded = base64.b64encode(data_to_encode.encode()).decode()
    return encoded


def generate_transaction_id() -> str:
    """Generate a unique transaction ID."""
    return f"TX{uuid4().hex[:12].upper()}"


def get_service_price(service_id: str) -> Optional[float]:
    """
    Get the price for a service from the database.
    """
    try:
        response = supabase.table('service_prices') \
            .select('price') \
            .eq('service_type', service_id) \
            .order('created_at', desc=True) \
            .limit(1) \
            .execute()
        
        if response.data and len(response.data) > 0:
            return float(response.data[0]['price'])
        
        # Fallback prices
        fallback_prices = {
            'mileage': 100,
            'valuation': 150,
            'ownership': 200,
            'full_report': 350
        }
        return fallback_prices.get(service_id, 100)
        
    except Exception as e:
        logger.error(f"❌ Error fetching service price: {str(e)}")
        return None


def save_payment_record(user_id: str, service_id: str, amount: float, 
                        phone: str, checkout_request_id: str, 
                        status: str = 'pending') -> bool:
    """
    Save payment record to Supabase.
    """
    try:
        data = {
            'user_id': user_id,
            'service_id': service_id,
            'service_name': get_service_name(service_id),
            'amount': amount,
            'phone': phone,
            'checkout_request_id': checkout_request_id,
            'status': status,
            'created_at': datetime.now().isoformat()
        }
        
        response = supabase.table('payments').insert(data).execute()
        
        if response.data:
            logger.info(f"✅ Payment record saved: {checkout_request_id}")
            return True
        else:
            logger.error("❌ Failed to save payment record")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error saving payment record: {str(e)}")
        return False


def update_payment_status(checkout_request_id: str, status: str, 
                          result_code: str = None, 
                          result_desc: str = None) -> bool:
    """
    Update payment status in Supabase.
    """
    try:
        data = {
            'status': status,
            'updated_at': datetime.now().isoformat()
        }
        
        if result_code:
            data['result_code'] = result_code
        if result_desc:
            data['result_desc'] = result_desc
        
        response = supabase.table('payments') \
            .update(data) \
            .eq('checkout_request_id', checkout_request_id) \
            .execute()
        
        if response.data:
            logger.info(f"✅ Payment status updated: {checkout_request_id} -> {status}")
            return True
        else:
            logger.error(f"❌ Failed to update payment status: {checkout_request_id}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error updating payment status: {str(e)}")
        return False


def unlock_service(user_id: str, service_id: str, payment_ref: str) -> bool:
    """
    Unlock a service for a user after successful payment.
    """
    try:
        # Check if service is already unlocked
        existing = supabase.table('service_access') \
            .select('id') \
            .eq('user_id', user_id) \
            .eq('service_id', service_id) \
            .eq('status', 'active') \
            .execute()
        
        if existing.data and len(existing.data) > 0:
            logger.info(f"ℹ️ Service {service_id} already unlocked for user {user_id}")
            return True
        
        # Create new service access record
        expires_at = datetime.now() + timedelta(days=365)  # 1 year access
        
        data = {
            'user_id': user_id,
            'service_id': service_id,
            'status': 'active',
            'expires_at': expires_at.isoformat(),
            'payment_ref': payment_ref,
            'created_at': datetime.now().isoformat()
        }
        
        response = supabase.table('service_access').insert(data).execute()
        
        if response.data:
            logger.info(f"✅ Service {service_id} unlocked for user {user_id}")
            
            # Create notification
            create_notification(
                user_id,
                f"🎉 {get_service_name(service_id)} has been unlocked!",
                'service'
            )
            
            return True
        else:
            logger.error(f"❌ Failed to unlock service: {service_id}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error unlocking service: {str(e)}")
        return False


def get_service_name(service_id: str) -> str:
    """Get human-readable service name."""
    names = {
        'mileage': 'Mileage Calculator',
        'valuation': 'Instant Vehicle Value',
        'ownership': 'Ownership Cost Report',
        'full_report': 'Full Vehicle Report'
    }
    return names.get(service_id, service_id)


def create_notification(user_id: str, message: str, notif_type: str = 'service') -> bool:
    """
    Create a notification for the user.
    """
    try:
        data = {
            'user_id': user_id,
            'message': message,
            'type': notif_type,
            'read': False,
            'created_at': datetime.now().isoformat()
        }
        
        response = supabase.table('notifications').insert(data).execute()
        
        if response.data:
            logger.info(f"✅ Notification created for user {user_id}")
            return True
        return False
        
    except Exception as e:
        logger.error(f"❌ Error creating notification: {str(e)}")
        return False


def format_phone_number(phone: str) -> str:
    """
    Format phone number for M-Pesa API.
    Removes leading 0 or +254 and adds 254 prefix.
    """
    # Remove any non-numeric characters
    phone = ''.join(filter(str.isdigit, phone))
    
    # Remove leading 0 if present
    if phone.startswith('0'):
        phone = phone[1:]
    
    # Remove leading 254 if present
    if phone.startswith('254'):
        phone = phone
    
    # Add 254 prefix if not present
    if not phone.startswith('254'):
        phone = f"254{phone}"
    
    return phone


# ─── API Routes ──────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat(),
        'mpesa_env': MPESA_ENV,
        'shortcode': MPESA_SHORTCODE
    })


@app.route('/api/mpesa/stkpush', methods=['POST'])
def stk_push():
    """
    Initiate M-Pesa STK Push payment.
    
    Expected JSON payload:
    {
        "phone": "0712345678",
        "amount": 100,
        "account_reference": "mileage",
        "description": "Auto-D: Mileage Calculator",
        "user_id": "user-uuid"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        phone = data.get('phone', '').strip()
        amount = data.get('amount')
        account_ref = data.get('account_reference', 'AUTO-D')
        description = data.get('description', 'Auto-D Payment')
        user_id = data.get('user_id') or session.get('user_id')
        
        # Validate inputs
        if not phone:
            return jsonify({'error': 'Phone number is required'}), 400
        
        if not amount or amount <= 0:
            return jsonify({'error': 'Valid amount is required'}), 400
        
        # Format phone number
        formatted_phone = format_phone_number(phone)
        
        # Get access token
        access_token = get_access_token()
        if not access_token:
            return jsonify({'error': 'Failed to authenticate with M-Pesa'}), 500
        
        # Generate timestamp and password
        timestamp = get_timestamp()
        password = generate_password(MPESA_SHORTCODE, MPESA_PASSKEY, timestamp)
        
        # Build STK Push request
        stk_url = f"{MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest"
        
        payload = {
            'BusinessShortCode': MPESA_SHORTCODE,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': str(int(amount)),
            'PartyA': formatted_phone,
            'PartyB': MPESA_SHORTCODE,
            'PhoneNumber': formatted_phone,
            'CallBackURL': f"{CALLBACK_BASE_URL}/api/mpesa/callback",
            'AccountReference': account_ref[:12],
            'TransactionDesc': description[:36]
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        logger.info(f"📱 Initiating STK Push for {formatted_phone}, amount: {amount}, shortcode: {MPESA_SHORTCODE}")
        
        response = requests.post(stk_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            checkout_request_id = result.get('CheckoutRequestID')
            response_code = result.get('ResponseCode')
            response_desc = result.get('ResponseDescription')
            
            if response_code == '0':
                logger.info(f"✅ STK Push initiated: {checkout_request_id}")
                
                # Save payment record
                if user_id:
                    save_payment_record(
                        user_id=user_id,
                        service_id=account_ref,
                        amount=amount,
                        phone=phone,
                        checkout_request_id=checkout_request_id,
                        status='pending'
                    )
                
                return jsonify({
                    'success': True,
                    'checkout_request_id': checkout_request_id,
                    'message': 'STK Push sent successfully',
                    'response_description': response_desc
                })
            else:
                logger.error(f"❌ STK Push failed: {response_code} - {response_desc}")
                return jsonify({
                    'success': False,
                    'error': response_desc or 'STK Push failed',
                    'code': response_code
                }), 400
        else:
            logger.error(f"❌ STK Push error: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': 'Failed to initiate STK Push',
                'status_code': response.status_code
            }), response.status_code
            
    except Exception as e:
        logger.error(f"❌ STK Push error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/mpesa/callback', methods=['POST'])
def mpesa_callback():
    """
    M-Pesa callback endpoint for STK Push results.
    """
    try:
        data = request.get_json()
        logger.info(f"📩 M-Pesa callback received: {json.dumps(data)[:200]}...")
        
        # Extract the result from the callback
        body = data.get('Body', {})
        stk_callback = body.get('stkCallback', {})
        
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        
        if not checkout_request_id:
            logger.error("❌ Callback missing CheckoutRequestID")
            return jsonify({'success': False, 'error': 'Missing checkout request ID'}), 400
        
        # Update payment status
        if result_code == '0':
            # Payment successful
            update_payment_status(checkout_request_id, 'completed', result_code, result_desc)
            
            # Get payment record
            payment = supabase.table('payments') \
                .select('*') \
                .eq('checkout_request_id', checkout_request_id) \
                .execute()
            
            if payment.data and len(payment.data) > 0:
                payment_data = payment.data[0]
                user_id = payment_data.get('user_id')
                service_id = payment_data.get('service_id')
                
                if user_id and service_id:
                    # Unlock the service
                    unlock_service(user_id, service_id, checkout_request_id)
            
            logger.info(f"✅ Payment successful: {checkout_request_id}")
            
        else:
            # Payment failed
            update_payment_status(checkout_request_id, 'failed', result_code, result_desc)
            logger.warning(f"⚠️ Payment failed: {checkout_request_id} - {result_desc}")
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        logger.error(f"❌ Callback error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/mpesa/status/<checkout_request_id>', methods=['GET'])
def payment_status(checkout_request_id):
    """
    Check the status of a payment.
    """
    try:
        # Query the payment record
        response = supabase.table('payments') \
            .select('*') \
            .eq('checkout_request_id', checkout_request_id) \
            .execute()
        
        if response.data and len(response.data) > 0:
            payment = response.data[0]
            return jsonify({
                'success': True,
                'checkout_request_id': checkout_request_id,
                'status': payment.get('status', 'pending'),
                'amount': payment.get('amount'),
                'service_id': payment.get('service_id'),
                'created_at': payment.get('created_at'),
                'updated_at': payment.get('updated_at'),
                'result_code': payment.get('result_code'),
                'result_desc': payment.get('result_desc')
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Payment not found'
            }), 404
            
    except Exception as e:
        logger.error(f"❌ Status check error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/mpesa/confirm/<checkout_request_id>', methods=['POST'])
def confirm_payment(checkout_request_id):
    """
    Manually confirm a payment (for cases where callback fails).
    """
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id') or session.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        # Get payment record
        response = supabase.table('payments') \
            .select('*') \
            .eq('checkout_request_id', checkout_request_id) \
            .execute()
        
        if not response.data or len(response.data) == 0:
            return jsonify({'error': 'Payment not found'}), 404
        
        payment = response.data[0]
        service_id = payment.get('service_id')
        
        if not service_id:
            return jsonify({'error': 'Service ID not found'}), 400
        
        # Unlock the service
        success = unlock_service(user_id, service_id, checkout_request_id)
        
        if success:
            # Update payment status
            update_payment_status(checkout_request_id, 'completed', '0', 'Confirmed manually')
            
            return jsonify({
                'success': True,
                'message': 'Payment confirmed and service unlocked'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to unlock service'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Confirm payment error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/mpesa/services', methods=['GET'])
def get_services():
    """
    Get list of available services with prices.
    """
    try:
        # Get all service prices
        response = supabase.table('service_prices') \
            .select('*') \
            .order('created_at', desc=True) \
            .execute()
        
        services = {}
        
        # Group by service_type to get latest price
        if response.data:
            for item in response.data:
                service_type = item.get('service_type')
                if service_type and service_type not in services:
                    services[service_type] = {
                        'id': service_type,
                        'name': get_service_name(service_type),
                        'price': float(item.get('price', 0)),
                        'currency': 'KES'
                    }
        
        # Add default services if missing
        default_services = {
            'mileage': {'name': 'Mileage Calculator', 'price': 100},
            'valuation': {'name': 'Instant Vehicle Value', 'price': 150},
            'ownership': {'name': 'Ownership Cost Report', 'price': 200},
            'full_report': {'name': 'Full Vehicle Report', 'price': 350}
        }
        
        for service_id, default in default_services.items():
            if service_id not in services:
                services[service_id] = {
                    'id': service_id,
                    'name': default['name'],
                    'price': default['price'],
                    'currency': 'KES'
                }
        
        return jsonify({
            'success': True,
            'services': list(services.values())
        })
        
    except Exception as e:
        logger.error(f"❌ Get services error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/mpesa/user/services/<user_id>', methods=['GET'])
def get_user_services(user_id):
    """
    Get unlocked services for a user.
    """
    try:
        response = supabase.table('service_access') \
            .select('*') \
            .eq('user_id', user_id) \
            .eq('status', 'active') \
            .execute()
        
        unlocked = []
        if response.data:
            for item in response.data:
                service_id = item.get('service_id')
                expires_at = item.get('expires_at')
                
                # Check if expired
                if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
                    continue
                
                unlocked.append({
                    'service_id': service_id,
                    'name': get_service_name(service_id),
                    'status': 'active',
                    'expires_at': expires_at,
                    'unlocked_at': item.get('created_at')
                })
        
        return jsonify({
            'success': True,
            'services': unlocked
        })
        
    except Exception as e:
        logger.error(f"❌ Get user services error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/mpesa/webhook', methods=['POST'])
def webhook():
    """
    Generic webhook endpoint for testing.
    """
    data = request.get_json()
    logger.info(f"📩 Webhook received: {json.dumps(data)[:500]}")
    return jsonify({'success': True, 'message': 'Webhook received'}), 200


@app.route('/api/mpesa/shortcode', methods=['GET'])
def get_shortcode():
    """
    Get the configured shortcode.
    """
    return jsonify({
        'success': True,
        'shortcode': MPESA_SHORTCODE,
        'environment': MPESA_ENV
    })


# ─── Error Handlers ──────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# ─── Main ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    # Check required configuration
    missing_config = []
    
    if not MPESA_CONSUMER_KEY:
        missing_config.append('MPESA_CONSUMER_KEY')
    if not MPESA_CONSUMER_SECRET:
        missing_config.append('MPESA_CONSUMER_SECRET')
    if not MPESA_PASSKEY:
        missing_config.append('MPESA_PASSKEY')
    
    if missing_config:
        logger.warning(f"⚠️ Missing M-Pesa configuration: {', '.join(missing_config)}")
        logger.warning("⚠️ STK Push functionality will not work without these credentials")
    
    logger.info(f"🚀 M-Pesa Service starting on http://localhost:5000")
    logger.info(f"📡 Environment: {MPESA_ENV}")
    logger.info(f"📱 Shortcode: {MPESA_SHORTCODE}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
