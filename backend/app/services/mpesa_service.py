"""
Auto-D Kenya
M-Pesa Business Logic
"""

import base64
import logging
import requests

from datetime import datetime
from app.core.config import settings
from app.core.database import supabase

logger = logging.getLogger(__name__)


class MpesaService:

    def __init__(self):

        self.environment = settings.MPESA_ENV
        self.shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.callback_url = settings.MPESA_CALLBACK_URL

        if self.environment == "production":
            self.base_url = "https://api.safaricom.co.ke"
        else:
            self.base_url = "https://sandbox.safaricom.co.ke"

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

    ###########################################################
    # Configuration
    ###########################################################

    def is_configured(self):

        return all([
            self.consumer_key,
            self.consumer_secret,
            self.shortcode,
            self.passkey,
            self.callback_url
        ])

    ###########################################################
    # Access Token
    ###########################################################

    def get_access_token(self):

        auth = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {auth}"
        }

        url = (
            f"{self.base_url}"
            "/oauth/v1/generate?grant_type=client_credentials"
        )

        response = requests.get(url, headers=headers, timeout=30)

        response.raise_for_status()

        return response.json()["access_token"]

    ###########################################################
    # Format Phone Number
    ###########################################################

    def format_phone_number(self, phone):
        """
        Format phone number for M-Pesa API.
        Converts 07XXXXXXXX or 7XXXXXXXX to 2547XXXXXXXX.
        """
        # Remove all non-numeric characters
        phone = ''.join(filter(str.isdigit, phone))
        
        # Remove leading 0 if present
        if phone.startswith('0'):
            phone = phone[1:]
        
        # Remove leading 254 if present
        if phone.startswith('254'):
            phone = phone[3:]
        
        # Add 254 prefix
        return f"254{phone}"

    ###########################################################
    # Save Payment Record
    ###########################################################

    def save_payment_record(
        self,
        user_id,
        service_id,
        amount,
        phone,
        checkout_request_id,
        status='pending'
    ):
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
                'created_at': datetime.utcnow().isoformat()
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

    ###########################################################
    # Update Payment Status
    ###########################################################

    def update_payment_status(
        self,
        checkout_request_id,
        status,
        result_code=None,
        result_desc=None
    ):
        """Update payment status in Supabase."""
        try:
            data = {
                'status': status,
                'updated_at': datetime.utcnow().isoformat()
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

    ###########################################################
    # Unlock Service
    ###########################################################

    def unlock_service(self, user_id, service_id, payment_ref):
        """Unlock a service for a user after successful payment."""
        try:
            # Check if already unlocked
            existing = supabase.table('service_access') \
                .select('id') \
                .eq('user_id', user_id) \
                .eq('service_id', service_id) \
                .eq('status', 'active') \
                .execute()

            if existing.data and len(existing.data) > 0:
                logger.info(f"ℹ️ Service {service_id} already unlocked for user {user_id}")
                return True

            # Set expiry to 365 days from now
            expires_at = datetime.utcnow().replace(
                year=datetime.utcnow().year + 1
            )

            data = {
                'user_id': user_id,
                'service_id': service_id,
                'status': 'active',
                'expires_at': expires_at.isoformat(),
                'payment_ref': payment_ref,
                'created_at': datetime.utcnow().isoformat()
            }

            response = supabase.table('service_access').insert(data).execute()

            if response.data:
                logger.info(f"✅ Service {service_id} unlocked for user {user_id}")
                
                # Create notification
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

    ###########################################################
    # Create Notification
    ###########################################################

    def create_notification(self, user_id, message, notif_type='service'):
        """Create a notification for the user."""
        try:
            data = {
                'user_id': user_id,
                'message': message,
                'type': notif_type,
                'read': False,
                'created_at': datetime.utcnow().isoformat()
            }

            response = supabase.table('notifications').insert(data).execute()

            if response.data:
                logger.info(f"✅ Notification created for user {user_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"❌ Error creating notification: {str(e)}")
            return False

    ###########################################################
    # STK Push
    ###########################################################

    async def initiate_stk_push(
        self,
        phone,
        amount,
        account_reference,
        description,
        user_id=None
    ):
        """
        Initiate Safaricom STK Push and save a pending payment.
        """
        try:
            # ─── Validate configuration ───
            if not self.is_configured():
                logger.error("❌ M-Pesa is not configured")
                return {
                    "success": False,
                    "error": "M-Pesa is not configured."
                }

            # ─── Get access token ───
            try:
                token = self.get_access_token()
                if not token:
                    logger.error("❌ Failed to get access token")
                    return {
                        "success": False,
                        "error": "Failed to authenticate with M-Pesa"
                    }
            except Exception as e:
                logger.error(f"❌ Token error: {str(e)}")
                return {
                    "success": False,
                    "error": f"Authentication failed: {str(e)}"
                }

            # ─── Generate timestamp and password ───
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            password = base64.b64encode(
                f"{self.shortcode}{self.passkey}{timestamp}".encode()
            ).decode()

            # ─── Format phone number ───
            formatted_phone = self.format_phone_number(phone)
            logger.info(f"📱 Formatted phone: {formatted_phone}")

            # ─── Build payload ───
            payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(float(amount)),
                "PartyA": formatted_phone,
                "PartyB": self.shortcode,
                "PhoneNumber": formatted_phone,
                "CallBackURL": self.callback_url,
                "AccountReference": account_reference[:12],
                "TransactionDesc": description[:36],
            }

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"

            logger.info(f"📱 Sending STK Push to {formatted_phone} for KES {amount}")

            # ─── Send request ───
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=60
            )

            response.raise_for_status()
            data = response.json()

            logger.info(f"📱 STK Push response: {data}")

            # ─── Check response ───
            if data.get("ResponseCode") != "0":
                error_msg = data.get("ResponseDescription", "STK Push failed")
                logger.error(f"❌ STK Push failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "code": data.get("ResponseCode")
                }

            checkout_request_id = data.get("CheckoutRequestID")
            merchant_request_id = data.get("MerchantRequestID")

            if not checkout_request_id:
                logger.error("❌ No CheckoutRequestID in response")
                return {
                    "success": False,
                    "error": "No checkout ID returned from M-Pesa"
                }

            # ─── Save payment record ───
            if user_id:
                self.save_payment_record(
                    user_id=user_id,
                    service_id=account_reference,
                    amount=amount,
                    phone=phone,
                    checkout_request_id=checkout_request_id,
                    status='pending'
                )

            logger.info(f"✅ STK Push initiated: {checkout_request_id}")

            return {
                "success": True,
                "checkout_request_id": checkout_request_id,
                "merchant_request_id": merchant_request_id,
                "customer_message": data.get("CustomerMessage"),
                "response_description": data.get("ResponseDescription")
            }

        except requests.exceptions.HTTPError as e:
            logger.exception("❌ Daraja HTTP error")
            return {
                "success": False,
                "error": f"HTTP error: {str(e)}"
            }
        except requests.exceptions.RequestException as e:
            logger.exception("❌ Daraja request error")
            return {
                "success": False,
                "error": f"Request error: {str(e)}"
            }
        except Exception as e:
            logger.exception("❌ STK Push failed")
            return {
                "success": False,
                "error": str(e)
            }

    ###########################################################
    # Callback
    ###########################################################

    def process_callback(self, callback):
        """
        Update payment from pending to completed or failed.
        """
        try:
            stk = callback.get("Body", {}).get("stkCallback", {})

            checkout_request_id = stk.get("CheckoutRequestID")
            result_code = stk.get("ResultCode")
            result_desc = stk.get("ResultDesc")

            if not checkout_request_id:
                logger.error("❌ Callback missing CheckoutRequestID")
                return False

            logger.info(f"📞 Processing callback for {checkout_request_id}, result: {result_code}")

            if result_code == 0:
                # ─── Payment successful ───
                status = "completed"
                
                # Get receipt number
                receipt = None
                metadata = stk.get("CallbackMetadata", {}).get("Item", [])
                for item in metadata:
                    if item.get("Name") == "MpesaReceiptNumber":
                        receipt = item.get("Value")
                        break

                # Update payment
                self.update_payment_status(
                    checkout_request_id,
                    status,
                    result_code,
                    result_desc
                )

                # Unlock service
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
                return True

            else:
                # ─── Payment failed ───
                self.update_payment_status(
                    checkout_request_id,
                    'failed',
                    result_code,
                    result_desc
                )
                logger.warning(f"⚠️ Payment failed: {checkout_request_id} - {result_desc}")
                return False

        except Exception as e:
            logger.exception("❌ Callback processing failed")
            return False

    ###########################################################
    # Payment Status
    ###########################################################

    def get_payment_status(self, checkout_request_id):
        """
        Get payment status from Supabase.
        """
        try:
            logger.info(f"🔍 Checking payment: {checkout_request_id}")

            response = (
                supabase
                .table("payments")
                .select("*")
                .eq("checkout_request_id", checkout_request_id)
                .limit(1)
                .execute()
            )

            if not response.data:
                logger.warning(f"⚠️ Payment not found: {checkout_request_id}")
                return {
                    "success": False,
                    "error": "Payment not found"
                }

            payment = response.data[0]
            logger.info(f"✅ Payment found: status={payment.get('status')}")

            return {
                "success": True,
                "checkout_request_id": payment["checkout_request_id"],
                "status": payment["status"],
                "amount": payment["amount"],
                "service_id": payment.get("service_id"),
                "service_name": payment.get("service_name"),
                "created_at": payment["created_at"],
                "updated_at": payment.get("updated_at"),
                "mpesa_receipt": payment.get("mpesa_receipt")
            }

        except Exception as e:
            logger.error(f"❌ Status check error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    ###########################################################
    # Manual Confirmation
    ###########################################################

    def confirm_payment_manually(
        self,
        checkout_request_id,
        user_id
    ):
        """
        Manually confirm a payment and unlock the service.
        """
        try:
            logger.info(f"🔓 Manual confirm: {checkout_request_id} for user {user_id}")

            # ─── Check if payment exists ───
            response = (
                supabase
                .table("payments")
                .select("*")
                .eq("checkout_request_id", checkout_request_id)
                .limit(1)
                .execute()
            )

            if not response.data:
                return {
                    "success": False,
                    "error": "Payment not found."
                }

            payment = response.data[0]
            service_id = payment.get("service_id")
            payment_user_id = payment.get("user_id")

            # ─── Verify user owns this payment ───
            if payment_user_id != user_id:
                logger.error(f"❌ User {user_id} does not own payment {checkout_request_id}")
                return {
                    "success": False,
                    "error": "Payment does not belong to this user"
                }

            # ─── Check if already completed ───
            if payment.get("status") == "completed":
                # Still try to unlock if not already
                if service_id:
                    self.unlock_service(user_id, service_id, checkout_request_id)
                return {
                    "success": True,
                    "message": "Payment already confirmed",
                    "already_completed": True
                }

            # ─── Unlock the service ───
            if not service_id:
                return {
                    "success": False,
                    "error": "Service ID not found"
                }

            success = self.unlock_service(user_id, service_id, checkout_request_id)

            if success:
                self.update_payment_status(
                    checkout_request_id,
                    'completed',
                    '0',
                    'Confirmed manually'
                )
                logger.info(f"✅ Payment confirmed manually: {checkout_request_id}")
                return {
                    "success": True,
                    "message": "Payment confirmed and service unlocked"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to unlock service"
                }

        except Exception as e:
            logger.exception("❌ Manual confirmation failed")
            return {
                "success": False,
                "error": str(e)
            }

    ###########################################################
    # Services
    ###########################################################

    def get_all_services(self):
        """Get all available services with prices."""
        services = []
        for service_id, price in self.service_prices.items():
            services.append({
                "service_id": service_id,
                "name": self.get_service_name(service_id),
                "price": price,
                "currency": "KES"
            })
        return services

    def get_service_name(self, service_id):
        """Get service name by ID."""
        return self.service_names.get(service_id, service_id)

    ###########################################################
    # User Services
    ###########################################################

    def get_user_services(self, user_id):
        """Get unlocked services for a user."""
        try:
            response = (
                supabase
                .table("service_access")
                .select("*")
                .eq("user_id", user_id)
                .eq("status", "active")
                .execute()
            )

            services = []
            if response.data:
                for item in response.data:
                    service_id = item.get('service_id')
                    expires_at = item.get('expires_at')

                    # Check if expired
                    if expires_at and datetime.fromisoformat(expires_at) < datetime.utcnow():
                        continue

                    services.append({
                        'service_id': service_id,
                        'service_name': self.get_service_name(service_id),
                        'status': 'active',
                        'expires_at': expires_at,
                        'unlocked_at': item.get('created_at')
                    })

            return services

        except Exception as e:
            logger.error(f"❌ Get user services error: {str(e)}")
            return []

    ###########################################################
    # Payment History
    ###########################################################

    def get_payment_history(self, user_id):
        """Get payment history for a user."""
        try:
            response = (
                supabase
                .table("payments")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )

            return response.data or []

        except Exception as e:
            logger.error(f"❌ Get payment history error: {str(e)}")
            return []
