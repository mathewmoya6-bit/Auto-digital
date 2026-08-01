# app/modules/mpesa/stk_push.py
# Auto-D Kenya - M-Pesa STK Push
# ================================================================
# TYPE: MODULE - M-Pesa STK Push logic

import base64
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import httpx

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.database import get_supabase

logger = logging.getLogger(__name__)


class StkPushService:
    """M-Pesa STK Push service with payment verification."""
    
    def __init__(self):
        self.supabase = get_supabase()
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = settings.MPESA_SHORTCODE
        self.callback_url = settings.MPESA_CALLBACK_URL
        
        self.base_url = (
            "https://api.safaricom.co.ke"
            if settings.MPESA_ENVIRONMENT == "production"
            else "https://sandbox.safaricom.co.ke"
        )
        
        self.access_token = None
        self.token_expiry = None
        
        # Log configuration at startup
        self._log_configuration()
    
    def _log_configuration(self) -> None:
        """Log M-Pesa configuration for debugging."""
        logger.info(f"=== M-Pesa Configuration ===")
        logger.info(f"Environment: {settings.MPESA_ENVIRONMENT}")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"Shortcode: {self.shortcode}")
        logger.info(f"Callback URL: {self.callback_url}")
        logger.info(f"Consumer Key Present: {bool(self.consumer_key)}")
        logger.info(f"Consumer Secret Present: {bool(self.consumer_secret)}")
        logger.info(f"Passkey Present: {bool(self.passkey)}")
        logger.info(f"============================")
    
    async def _get_access_token(self) -> str:
        """
        Get OAuth access token using GET request.
        
        Returns:
            str: Access token
            
        Raises:
            AppException: If token retrieval fails
        """
        # Check cached token
        if self.access_token and self.token_expiry and datetime.utcnow() < self.token_expiry:
            logger.debug("Using cached access token (valid until {})".format(
                self.token_expiry.isoformat()
            ))
            return self.access_token
        
        # Prepare authentication
        auth = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()
        
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        
        logger.info(f"Requesting OAuth token from: {url}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Basic {auth}",
                    "Accept": "application/json"
                },
                timeout=30.0
            )
        
        # Log response details
        logger.info(f"OAuth Status: {response.status_code}")
        logger.info(f"OAuth Body: {response.text[:500]}...")
        
        # Check response status
        response.raise_for_status()
        
        # Parse JSON safely
        try:
            data = response.json()
        except ValueError as e:
            logger.error(f"OAuth returned non-JSON response: {response.text}")
            raise AppException(
                f"OAuth returned non-JSON response: {response.text[:200]}",
                503
            )
        
        # Safe token extraction with validation
        token = data.get("access_token")
        
        if not token:
            error_msg = data.get("error", data.get("error_description", "Unknown error"))
            logger.error(f"OAuth error: {error_msg}")
            raise AppException(
                f"OAuth failed: {error_msg}",
                503
            )
        
        # Safely parse expires_in with type checking
        try:
            expires_in = int(data.get("expires_in", 3600))
        except (TypeError, ValueError):
            logger.warning(f"Invalid expires_in value: {data.get('expires_in')}, using default 3600")
            expires_in = 3600
        
        # Store token with expiry
        self.access_token = token
        self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        
        logger.info(f"OAuth token obtained successfully, expires in {expires_in}s")
        logger.debug(f"Token will expire at: {self.token_expiry.isoformat()}")
        
        return token
    
    def _generate_password(self, timestamp: str) -> str:
        """Generate password for STK push."""
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(password_str.encode()).decode()
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to 254 format."""
        # Remove any non-digit characters
        phone = ''.join(filter(str.isdigit, phone))
        
        # If it starts with 0, remove it
        if phone.startswith('0'):
            phone = phone[1:]
        
        # If it starts with 254, keep as is
        if phone.startswith('254'):
            return phone
        
        # Otherwise prepend 254
        return f"254{phone}"
    
    async def _create_payment_record(
        self,
        checkout_request_id: str,
        merchant_request_id: str,
        amount: float,
        phone: str,
        user_id: Optional[str],
        service_id: Optional[str],
        description: str
    ) -> None:
        """Create a payment record in the database."""
        try:
            payment_data = {
                "checkout_request_id": checkout_request_id,
                "merchant_request_id": merchant_request_id,
                "amount": amount,
                "phone": phone,
                "user_id": user_id,
                "service_id": service_id,
                "description": description,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table("payments").insert(payment_data).execute()
            logger.info(f"Payment record created: {checkout_request_id}")
            
        except Exception as e:
            logger.error(f"Failed to create payment record: {e}")
            # Don't raise - the STK push already succeeded
    
    async def _create_user_service_record(
        self,
        user_id: str,
        service_id: str,
        payment_id: int,
        expires_at: Optional[datetime] = None
    ) -> None:
        """Create a user service access record."""
        try:
            # Set default expiry (1 year from now)
            if not expires_at:
                expires_at = datetime.utcnow() + timedelta(days=365)
            
            service_data = {
                "user_id": user_id,
                "service_id": service_id,
                "payment_id": payment_id,
                "status": "pending",
                "expires_at": expires_at.isoformat(),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table("user_services").insert(service_data).execute()
            logger.info(f"User service record created: user={user_id}, service={service_id}")
            
        except Exception as e:
            logger.error(f"Failed to create user service record: {e}")
    
    async def initiate_push(
        self,
        phone: str,
        amount: float,
        description: str,
        checkout_request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        service_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initiate STK Push payment.
        
        Args:
            phone: Phone number (without country code)
            amount: Amount to charge
            description: Transaction description
            checkout_request_id: Optional custom ID
            user_id: Optional user ID for tracking
            service_id: Optional service ID for tracking
            
        Returns:
            Dict with checkout_request_id and status
            
        Raises:
            AppException: If STK push fails
        """
        # Ensure phone is in correct format
        phone = self._normalize_phone(phone)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        password = self._generate_password(timestamp)
        
        if not checkout_request_id:
            checkout_request_id = f"STK-{secrets.token_hex(8)}"
        
        # Build payload
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": str(int(amount)),
            "PartyA": phone,
            "PartyB": self.shortcode,
            "PhoneNumber": phone,
            "CallBackURL": self.callback_url,
            "AccountReference": checkout_request_id[:12],
            "TransactionDesc": description[:36]
        }
        
        logger.info(f"Initiating STK Push for {phone}: {amount} KES (Ref: {checkout_request_id})")
        logger.debug(f"Payload: {payload}")
        
        # Get access token (with caching)
        token = await self._get_access_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=30.0
            )
        
        logger.info(f"STK Push Status: {response.status_code}")
        logger.info(f"STK Push Response: {response.text[:500]}")
        
        if response.status_code != 200:
            logger.error(f"STK push HTTP error: {response.text}")
            raise AppException(
                f"Payment initiation failed: {response.text[:200]}",
                502
            )
        
        # Parse response safely
        try:
            data = response.json()
        except ValueError:
            logger.error(f"STK Push non-JSON response: {response.text}")
            raise AppException("Payment initiation failed: Invalid response", 502)
        
        # Check response code
        response_code = data.get("ResponseCode")
        response_desc = data.get("ResponseDescription", "Unknown error")
        
        if response_code != "0":
            logger.error(f"STK push failed: {response_code} - {response_desc}")
            raise AppException(
                f"STK push failed: {response_desc}",
                400
            )
        
        merchant_request_id = data.get("MerchantRequestID")
        checkout_id = data.get("CheckoutRequestID", checkout_request_id)
        
        logger.info(f"STK Push successful: {data.get('CustomerMessage')}")
        
        # ─── CREATE PAYMENT RECORD ──────────────────────────────
        await self._create_payment_record(
            checkout_request_id=checkout_id,
            merchant_request_id=merchant_request_id,
            amount=amount,
            phone=phone,
            user_id=user_id,
            service_id=service_id,
            description=description
        )
        
        # ─── CREATE USER SERVICE RECORD (pending) ──────────────
        if user_id and service_id:
            await self._create_user_service_record(
                user_id=user_id,
                service_id=service_id,
                payment_id=None  # Will be updated on callback
            )
        
        return {
            "checkout_request_id": checkout_id,
            "merchant_request_id": merchant_request_id,
            "response_code": data.get("ResponseCode"),
            "response_description": data.get("ResponseDescription"),
            "customer_message": data.get("CustomerMessage")
        }
    
    # ─── PAYMENT VERIFICATION ──────────────────────────────────────
    
    async def verify_payment_status(self, checkout_request_id: str) -> Dict[str, Any]:
        """
        Verify payment status with Safaricom API.
        
        Args:
            checkout_request_id: The checkout request ID to verify
            
        Returns:
            Dict with status and transaction details
        """
        try:
            # Get payment record from database
            payment = await self._get_payment_record(checkout_request_id)
            if not payment:
                return {
                    "status": "not_found",
                    "message": "Payment record not found"
                }
            
            # If already completed, return cached status
            if payment.get("status") in ["completed", "paid", "success"]:
                return {
                    "status": payment.get("status"),
                    "mpesa_receipt": payment.get("mpesa_receipt"),
                    "transaction_id": payment.get("transaction_id"),
                    "result_desc": payment.get("result_desc")
                }
            
            # Query Safaricom API
            token = await self._get_access_token()
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            password = self._generate_password(timestamp)
            
            url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
            
            payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            }
            
            logger.info(f"Querying payment status: {checkout_request_id}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30.0
                )
            
            logger.info(f"Status query response: {response.status_code}")
            logger.info(f"Status query body: {response.text[:500]}")
            
            if response.status_code != 200:
                logger.warning(f"Status query failed: {response.status_code}")
                return {
                    "status": "unknown",
                    "message": "Unable to verify payment status"
                }
            
            data = response.json()
            result_code = data.get("ResultCode")
            result_desc = data.get("ResultDesc", "Unknown")
            
            # Update payment record
            await self._update_payment_status(
                checkout_request_id=checkout_request_id,
                result_code=result_code,
                result_desc=result_desc,
                data=data
            )
            
            # ─── UNLOCK SERVICE ON SUCCESS ──────────────────────
            if result_code == "0":
                await self._unlock_service_on_payment(
                    checkout_request_id=checkout_request_id,
                    mpesa_receipt=data.get("MpesaReceiptNumber"),
                    transaction_id=data.get("TransactionID")
                )
            
            return {
                "status": self._map_result_code_to_status(result_code),
                "result_code": result_code,
                "result_desc": result_desc,
                "mpesa_receipt": data.get("MpesaReceiptNumber"),
                "transaction_id": data.get("TransactionID")
            }
            
        except Exception as e:
            logger.error(f"Payment verification error: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _get_payment_record(self, checkout_request_id: str) -> Optional[Dict[str, Any]]:
        """Get payment record from database."""
        try:
            response = self.supabase.table("payments").select("*").eq("checkout_request_id", checkout_request_id).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting payment record: {e}")
            return None
    
    async def _update_payment_status(
        self,
        checkout_request_id: str,
        result_code: str,
        result_desc: str,
        data: Dict[str, Any]
    ) -> None:
        """Update payment record with status."""
        try:
            status = self._map_result_code_to_status(result_code)
            
            update_data = {
                "status": status,
                "result_code": result_code,
                "result_desc": result_desc,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if result_code == "0":
                update_data["mpesa_receipt"] = data.get("MpesaReceiptNumber")
                update_data["transaction_id"] = data.get("TransactionID")
                update_data["completed_at"] = datetime.utcnow().isoformat()
            
            response = self.supabase.table("payments").update(update_data).eq("checkout_request_id", checkout_request_id).execute()
            logger.info(f"Payment status updated: {checkout_request_id} -> {status}")
            
        except Exception as e:
            logger.error(f"Error updating payment status: {e}")
    
    async def _unlock_service_on_payment(
        self,
        checkout_request_id: str,
        mpesa_receipt: Optional[str] = None,
        transaction_id: Optional[str] = None
    ) -> None:
        """
        Unlock service after successful payment.
        
        Only called when ResultCode == 0.
        """
        try:
            # Get payment record
            payment = await self._get_payment_record(checkout_request_id)
            if not payment:
                logger.warning(f"Payment record not found for unlock: {checkout_request_id}")
                return
            
            user_id = payment.get("user_id")
            service_id = payment.get("service_id")
            payment_id = payment.get("id")
            
            if not user_id or not service_id:
                logger.warning(f"Missing user_id or service_id for unlock: {checkout_request_id}")
                return
            
            # Update user_service record
            user_service = self.supabase.table("user_services").select("*").eq("user_id", user_id).eq("service_id", service_id).execute()
            
            if user_service.data and len(user_service.data) > 0:
                # Update existing
                update_data = {
                    "status": "active",
                    "payment_id": payment_id,
                    "expires_at": (datetime.utcnow() + timedelta(days=365)).isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                if mpesa_receipt:
                    update_data["mpesa_receipt"] = mpesa_receipt
                if transaction_id:
                    update_data["transaction_id"] = transaction_id
                
                response = self.supabase.table("user_services").update(update_data).eq("id", user_service.data[0]["id"]).execute()
                logger.info(f"User service updated: user={user_id}, service={service_id}")
            else:
                # Create new
                new_data = {
                    "user_id": user_id,
                    "service_id": service_id,
                    "payment_id": payment_id,
                    "status": "active",
                    "expires_at": (datetime.utcnow() + timedelta(days=365)).isoformat(),
                    "mpesa_receipt": mpesa_receipt,
                    "transaction_id": transaction_id,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                response = self.supabase.table("user_services").insert(new_data).execute()
                logger.info(f"User service created: user={user_id}, service={service_id}")
            
            # Update payment with service unlocked flag
            self.supabase.table("payments").update({
                "service_unlocked": True,
                "unlocked_at": datetime.utcnow().isoformat()
            }).eq("id", payment_id).execute()
            
            logger.info(f"✅ Service unlocked: {service_id} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error unlocking service: {e}")
    
    def _map_result_code_to_status(self, result_code: str) -> str:
        """Map Safaricom result code to status."""
        if result_code == "0":
            return "completed"
        elif result_code in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            return "failed"
        elif result_code in ["17", "18", "19"]:
            return "cancelled"
        else:
            return "unknown"
    
    # ─── SERVICE ACCESS CHECK ──────────────────────────────────────
    
    async def check_service_access(self, user_id: str, service_id: str) -> Dict[str, Any]:
        """
        Check if a user has access to a service.
        
        Args:
            user_id: User ID
            service_id: Service ID (e.g., 'valuation', 'mileage', 'ownership')
            
        Returns:
            Dict with has_access boolean and details
        """
        try:
            # Check user_services table
            response = self.supabase.table("user_services").select("*").eq("user_id", user_id).eq("service_id", service_id).execute()
            
            if not response.data or len(response.data) == 0:
                return {
                    "has_access": False,
                    "status": "no_record",
                    "message": "No access record found"
                }
            
            record = response.data[0]
            status = record.get("status")
            expires_at = record.get("expires_at")
            
            # Check if expired
            if expires_at:
                try:
                    expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    if datetime.utcnow() > expires:
                        return {
                            "has_access": False,
                            "status": "expired",
                            "message": "Access has expired"
                        }
                except:
                    pass
            
            # Check if active
            if status in ["active", "completed", "paid", "success"]:
                return {
                    "has_access": True,
                    "status": status,
                    "expires_at": expires_at,
                    "message": "Access granted"
                }
            else:
                return {
                    "has_access": False,
                    "status": status,
                    "message": f"Access status: {status}"
                }
                
        except Exception as e:
            logger.error(f"Error checking service access: {e}")
            return {
                "has_access": False,
                "status": "error",
                "message": str(e)
            }
    
    # ─── USER SERVICES ─────────────────────────────────────────────
    
    async def get_user_services(self, user_id: str) -> Dict[str, bool]:
        """
        Get all services a user has access to.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with service_id as key and boolean access status
        """
        try:
            response = self.supabase.table("user_services").select("service_id, status, expires_at").eq("user_id", user_id).execute()
            
            services = {}
            now = datetime.utcnow()
            
            if response.data:
                for record in response.data:
                    service_id = record.get("service_id")
                    status = record.get("status")
                    expires_at = record.get("expires_at")
                    
                    # Check expiry
                    is_expired = False
                    if expires_at:
                        try:
                            expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                            if now > expires:
                                is_expired = True
                        except:
                            pass
                    
                    # Determine access
                    has_access = status in ["active", "completed", "paid", "success"] and not is_expired
                    services[service_id] = has_access
            
            return services
            
        except Exception as e:
            logger.error(f"Error getting user services: {e}")
            return {}
    
    # ─── CALLBACK PROCESSING ───────────────────────────────────────
    
    async def process_callback(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process M-Pesa callback.
        
        This is the ONLY place where services should be unlocked.
        """
        try:
            # Extract data from callback
            body = callback_data.get("Body", {})
            stk_callback = body.get("stkCallback", {})
            
            merchant_request_id = stk_callback.get("MerchantRequestID")
            checkout_request_id = stk_callback.get("CheckoutRequestID")
            result_code = stk_callback.get("ResultCode")
            result_desc = stk_callback.get("ResultDesc")
            
            logger.info(f"Processing callback: {checkout_request_id} (ResultCode: {result_code})")
            
            # Update payment record
            payment = await self._get_payment_record(checkout_request_id)
            if not payment:
                logger.warning(f"Payment record not found for callback: {checkout_request_id}")
                return {"status": "ignored", "message": "Payment record not found"}
            
            # Update payment status
            await self._update_payment_status(
                checkout_request_id=checkout_request_id,
                result_code=str(result_code),
                result_desc=result_desc,
                data=stk_callback
            )
            
            # ─── UNLOCK SERVICE ONLY ON SUCCESS (ResultCode == 0) ───
            if result_code == 0:
                # Extract receipt from callback
                callback_metadata = stk_callback.get("CallbackMetadata", {})
                items = callback_metadata.get("Item", [])
                
                mpesa_receipt = None
                transaction_id = None
                
                for item in items:
                    if item.get("Name") == "MpesaReceiptNumber":
                        mpesa_receipt = item.get("Value")
                    elif item.get("Name") == "TransactionID":
                        transaction_id = item.get("Value")
                
                # Unlock the service
                await self._unlock_service_on_payment(
                    checkout_request_id=checkout_request_id,
                    mpesa_receipt=mpesa_receipt,
                    transaction_id=transaction_id
                )
                
                logger.info(f"✅ Service unlocked via callback: {checkout_request_id}")
                return {
                    "status": "success",
                    "checkout_request_id": checkout_request_id,
                    "mpesa_receipt": mpesa_receipt,
                    "transaction_id": transaction_id,
                    "message": "Payment confirmed and service unlocked"
                }
            else:
                logger.warning(f"Callback received failed payment: {result_code} - {result_desc}")
                return {
                    "status": "failed",
                    "checkout_request_id": checkout_request_id,
                    "result_code": result_code,
                    "result_desc": result_desc,
                    "message": "Payment failed"
                }
                
        except Exception as e:
            logger.error(f"Error processing callback: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def clear_token_cache(self) -> None:
        """Clear the cached access token to force refresh."""
        self.access_token = None
        self.token_expiry = None
        logger.info("Token cache cleared")
