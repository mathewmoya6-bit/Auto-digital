# backend/app/services/mpesa_service.py
"""
M-Pesa Service - Handles M-Pesa payment processing
STK Push, payment status, service unlocking, and payment records
"""

import os
import base64
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import uuid4

from app.core.database import supabase  # <-- Changed from db to supabase
from app.core.config import settings

logger = logging.getLogger(__name__)


class MpesaService:
    """Service for handling M-Pesa payments and service access management."""
    
    def __init__(self):
        self.shortcode = getattr(settings, "MPESA_SHORTCODE", "4095377")
        self.consumer_key = getattr(settings, "MPESA_CONSUMER_KEY", "")
        self.consumer_secret = getattr(settings, "MPESA_CONSUMER_SECRET", "")
        self.passkey = getattr(settings, "MPESA_PASSKEY", "")
        self.environment = getattr(settings, "MPESA_ENV", "sandbox")
        
        # API Base URLs
        self.base_url = (
            "https://sandbox.safaricom.co.ke" 
            if self.environment == "sandbox" 
            else "https://api.safaricom.co.ke"
        )
        
        self.callback_url = getattr(settings, "CALLBACK_BASE_URL", "https://auto-digital.onrender.com")
        
        # Service price mapping
        self.service_prices = {
            'mileage': 100,
            'valuation': 150,
            'ownership': 200,
            'full_report': 350
        }
        
        # Service name mapping
        self.service_names = {
            'mileage': 'Mileage Calculator',
            'valuation': 'Instant Vehicle Value',
            'ownership': 'Ownership Cost Report',
            'full_report': 'Full Vehicle Report'
        }
        
        logger.info(f"📱 M-Pesa Service initialized - Shortcode: {self.shortcode}, Env: {self.environment}")
    
    def is_configured(self) -> bool:
        """Check if M-Pesa is properly configured."""
        return all([
            self.consumer_key,
            self.consumer_secret,
            self.passkey,
            self.shortcode
        ])
    
    def get_access_token(self) -> Optional[str]:
        """
        Get M-Pesa API access token using OAuth 2.0 client credentials.
        """
        try:
            if not self.consumer_key or not self.consumer_secret:
                logger.error("❌ M-Pesa consumer key or secret not configured")
                return None
            
            auth_url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
            
            credentials = f"{self.consumer_key}:{self.consumer_secret}"
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
    
    def get_timestamp(self) -> str:
        """Get current timestamp in M-Pesa format (YYYYMMDDHHmmSS)"""
        return datetime.now().strftime('%Y%m%d%H%M%S')
    
    def generate_password(self, timestamp: str) -> str:
        """
        Generate the base64 encoded password for M-Pesa STK Push.
        """
        if not self.passkey:
            logger.error("❌ M-Pesa passkey not configured")
            return ""
        
        data_to_encode = f"{self.shortcode}{self.passkey}{timestamp}"
        encoded = base64.b64encode(data_to_encode.encode()).decode()
        return encoded
    
    def format_phone_number(self, phone: str) -> str:
        """
        Format phone number for M-Pesa API.
        Removes leading 0 or +254 and adds 254 prefix.
        """
        phone = ''.join(filter(str.isdigit, phone))
        
        if phone.startswith('0'):
            phone = phone[1:]
        
        if not phone.startswith('254'):
            phone = f"254{phone}"
        
        return phone
    
    def get_service_price(self, service_id: str) -> float:
        """
        Get the price for a service.
        First tries database, then falls back to defaults.
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
            
        except Exception as e:
            logger.warning(f"Could not fetch price from DB: {str(e)}")
        
        return self.service_prices.get(service_id, 100)
    
    def get_service_name(self, service_id: str) -> str:
        """Get human-readable service name."""
        return self.service_names.get(service_id, service_id)
    
    def save_payment_record(self, user_id: str, service_id: str, amount: float, 
                            phone: str, checkout_request_id: str, 
                            status: str = 'pending') -> bool:
        """Save payment record to Supabase."""
        try:
            data = {
                'user_id': user_id,
                'service_id': service_id,
                'service_name': self.get_service_name(service_id),
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
    
    def update_payment_status(self, checkout_request_id: str, status: str, 
                              result_code: str = None, 
                              result_desc: str = None) -> bool:
        """Update payment status in Supabase."""
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
    
    def unlock_service(self, user_id: str, service_id: str, payment_ref: str) -> bool:
        """Unlock a service for a user after successful payment."""
        try:
            existing = supabase.table('service_access') \
                .select('id') \
                .eq('user_id', user_id) \
                .eq('service_id', service_id) \
                .eq('status', 'active') \
                .execute()
            
            if existing.data and len(existing.data) > 0:
                logger.info(f"ℹ️ Service {service_id} already unlocked for user {user_id}")
                return True
            
            expires_at = datetime.now() + timedelta(days=365)
            
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
                
                self.create_notification(
                    user_id,
                    f"🎉 {self.get_service_name(service_id)} has been unlocked!",
                    'service'
                )
                
                return True
            else:
                logger.error(f"❌ Failed to unlock service: {service_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error unlocking service: {str(e)}")
            return False
    
    def create_notification(self, user_id: str, message: str, notif_type: str = 'service') -> bool:
        """Create a notification for the user."""
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
    
    def initiate_stk_push(self, phone: str, amount: float, 
                          account_reference: str, description: str,
                          user_id: str = None) -> Dict[str, Any]:
        """Initiate an M-Pesa STK Push payment."""
        if not phone:
            return {'success': False, 'error': 'Phone number is required'}
        
        if not amount or amount <= 0:
            return {'success': False, 'error': 'Valid amount is required'}
        
        formatted_phone = self.format_phone_number(phone)
        
        access_token = self.get_access_token()
        if not access_token:
            return {'success': False, 'error': 'Failed to authenticate with M-Pesa'}
        
        timestamp = self.get_timestamp()
        password = self.generate_password(timestamp)
        
        if not password:
            return {'success': False, 'error': 'Failed to generate M-Pesa password'}
        
        stk_url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        
        payload = {
            'BusinessShortCode': self.shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': str(int(amount)),
            'PartyA': formatted_phone,
            'PartyB': self.shortcode,
            'PhoneNumber': formatted_phone,
            'CallBackURL': f"{self.callback_url}/api/v1/mpesa/callback",
            'AccountReference': account_reference[:12],
            'TransactionDesc': description[:36]
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        logger.info(f"📱 Initiating STK Push for {formatted_phone}, amount: {amount}, shortcode: {self.shortcode}")
        
        try:
            response = requests.post(stk_url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                checkout_request_id = result.get('CheckoutRequestID')
                response_code = result.get('ResponseCode')
                response_desc = result.get('ResponseDescription')
                
                if response_code == '0':
                    logger.info(f"✅ STK Push initiated: {checkout_request_id}")
                    
                    if user_id:
                        self.save_payment_record(
                            user_id=user_id,
                            service_id=account_reference,
                            amount=amount,
                            phone=phone,
                            checkout_request_id=checkout_request_id,
                            status='pending'
                        )
                    
                    return {
                        'success': True,
                        'checkout_request_id': checkout_request_id,
                        'message': 'STK Push sent successfully',
                        'response_description': response_desc
                    }
                else:
                    logger.error(f"❌ STK Push failed: {response_code} - {response_desc}")
                    return {
                        'success': False,
                        'error': response_desc or 'STK Push failed',
                        'code': response_code
                    }
            else:
                logger.error(f"❌ STK Push error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': 'Failed to initiate STK Push',
                    'status_code': response.status_code
                }
                
        except Exception as e:
            logger.error(f"❌ STK Push error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def process_callback(self, callback_data: Dict[str, Any]) -> bool:
        """Process M-Pesa callback data."""
        try:
            body = callback_data.get('Body', {})
            stk_callback = body.get('stkCallback', {})
            
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            result_code = stk_callback.get('ResultCode')
            result_desc = stk_callback.get('ResultDesc')
            
            if not checkout_request_id:
                logger.error("❌ Callback missing CheckoutRequestID")
                return False
            
            if result_code == '0':
                self.update_payment_status(checkout_request_id, 'completed', result_code, result_desc)
                
                response = supabase.table('payments') \
                    .select('*') \
                    .eq('checkout_request_id', checkout_request_id) \
                    .execute()
                
                if response.data and len(response.data) > 0:
                    payment_data = response.data[0]
                    user_id = payment_data.get('user_id')
                    service_id = payment_data.get('service_id')
                    
                    if user_id and service_id:
                        self.unlock_service(user_id, service_id, checkout_request_id)
                
                logger.info(f"✅ Payment successful: {checkout_request_id}")
                
            else:
                self.update_payment_status(checkout_request_id, 'failed', result_code, result_desc)
                logger.warning(f"⚠️ Payment failed: {checkout_request_id} - {result_desc}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Callback error: {str(e)}")
            return False
    
    def get_payment_status(self, checkout_request_id: str) -> Dict[str, Any]:
        """Get the status of a payment."""
        try:
            response = supabase.table('payments') \
                .select('*') \
                .eq('checkout_request_id', checkout_request_id) \
                .execute()
            
            if response.data and len(response.data) > 0:
                payment = response.data[0]
                return {
                    'success': True,
                    'checkout_request_id': checkout_request_id,
                    'status': payment.get('status', 'pending'),
                    'amount': payment.get('amount'),
                    'service_id': payment.get('service_id'),
                    'created_at': payment.get('created_at'),
                    'updated_at': payment.get('updated_at'),
                    'result_code': payment.get('result_code'),
                    'result_desc': payment.get('result_desc')
                }
            else:
                return {
                    'success': False,
                    'error': 'Payment not found'
                }
                
        except Exception as e:
            logger.error(f"❌ Status check error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def confirm_payment_manually(self, checkout_request_id: str, user_id: str) -> Dict[str, Any]:
        """Manually confirm a payment."""
        try:
            response = supabase.table('payments') \
                .select('*') \
                .eq('checkout_request_id', checkout_request_id) \
                .execute()
            
            if not response.data or len(response.data) == 0:
                return {'success': False, 'error': 'Payment not found'}
            
            payment = response.data[0]
            service_id = payment.get('service_id')
            
            if not service_id:
                return {'success': False, 'error': 'Service ID not found'}
            
            success = self.unlock_service(user_id, service_id, checkout_request_id)
            
            if success:
                self.update_payment_status(checkout_request_id, 'completed', '0', 'Confirmed manually')
                return {
                    'success': True,
                    'message': 'Payment confirmed and service unlocked'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to unlock service'
                }
                
        except Exception as e:
            logger.error(f"❌ Confirm payment error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_user_services(self, user_id: str) -> List[Dict[str, Any]]:
        """Get unlocked services for a user."""
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
                    
                    if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
                        continue
                    
                    unlocked.append({
                        'service_id': service_id,
                        'name': self.get_service_name(service_id),
                        'status': 'active',
                        'expires_at': expires_at,
                        'unlocked_at': item.get('created_at')
                    })
            
            return unlocked
            
        except Exception as e:
            logger.error(f"❌ Get user services error: {str(e)}")
            return []
    
    def get_all_services(self) -> List[Dict[str, Any]]:
        """Get list of all available services with prices."""
        services = []
        
        for service_id, price in self.service_prices.items():
            try:
                db_price = self.get_service_price(service_id)
                if db_price:
                    price = db_price
            except:
                pass
            
            services.append({
                'id': service_id,
                'name': self.get_service_name(service_id),
                'price': price,
                'currency': 'KES'
            })
        
        return services
