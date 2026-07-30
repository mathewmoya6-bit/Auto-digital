# mpesa.py
# Auto-D Kenya - M-Pesa Integration Module
# ================================================================

import base64
import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import httpx

from fastapi import HTTPException, status
from config import settings
from database import get_supabase

logger = logging.getLogger(__name__)


class MpesaService:
    """M-Pesa Daraja API Integration."""
    
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = settings.MPESA_SHORTCODE
        self.callback_url = settings.MPESA_CALLBACK_URL
        
        # Determine environment
        self.base_url = (
            "https://api.safaricom.co.ke" 
            if settings.MPESA_ENVIRONMENT == "production" 
            else "https://sandbox.safaricom.co.ke"
        )
        
        self.access_token = None
        self.token_expiry = None
    
    async def _get_access_token(self) -> str:
        """Get OAuth access token from Safaricom."""
        if self.access_token and self.token_expiry and datetime.utcnow() < self.token_expiry:
            return self.access_token
        
        auth = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials",
                headers={"Authorization": f"Basic {auth}"}
            )
        
        if response.status_code != 200:
            logger.error(f"M-Pesa token error: {response.text}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="M-Pesa service unavailable"
            )
        
        data = response.json()
        self.access_token = data.get("access_token")
        self.token_expiry = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))
        return self.access_token
    
    def _generate_password(self, timestamp: str) -> str:
        """Generate the password for STK push."""
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(password_str.encode()).decode()
    
    async def stk_push(
        self, 
        phone: str, 
        amount: float, 
        description: str,
        checkout_request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initiate STK Push payment.
        
        Args:
            phone: Safaricom phone number (without country code)
            amount: Amount to charge
            description: Transaction description
            checkout_request_id: Optional custom ID
            
        Returns:
            Dict with checkout_request_id and status
        """
        # Ensure phone is in correct format (254XXXXXXXXX)
        if not phone.startswith("254"):
            phone = "254" + phone
        
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        password = self._generate_password(timestamp)
        
        if not checkout_request_id:
            checkout_request_id = f"STK-{secrets.token_hex(8)}"
        
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
        
        if response.status_code != 200:
            logger.error(f"M-Pesa STK push error: {response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="M-Pesa payment initiation failed"
            )
        
        data = response.json()
        
        # Check if successful
        if data.get("ResponseCode") != "0":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=data.get("ResponseDescription", "STK push failed")
            )
        
        return {
            "checkout_request_id": data.get("CheckoutRequestID", checkout_request_id),
            "merchant_request_id": data.get("MerchantRequestID"),
            "response_code": data.get("ResponseCode"),
            "response_description": data.get("ResponseDescription"),
            "customer_message": data.get("CustomerMessage")
        }
    
    async def query_status(self, checkout_request_id: str) -> Dict[str, Any]:
        """Query the status of an STK push transaction."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        password = self._generate_password(timestamp)
        
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }
        
        token = await self._get_access_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mpesa/stkpushquery/v1/query",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=30.0
            )
        
        if response.status_code != 200:
            logger.error(f"M-Pesa query error: {response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to query payment status"
            )
        
        return response.json()
    
    async def confirm_payment(self, checkout_request_id: str) -> Dict[str, Any]:
        """
        Confirm payment and unlock the service for the user.
        """
        try:
            # Query the status
            status_data = await self.query_status(checkout_request_id)
            
            # Check if payment was successful
            if status_data.get("ResultCode") == "0":
                # Payment successful - unlock the service
                await self._unlock_service(checkout_request_id)
                return {
                    "status": "completed",
                    "message": "Payment confirmed and service unlocked",
                    "data": status_data
                }
            else:
                return {
                    "status": "failed",
                    "message": status_data.get("ResultDesc", "Payment failed"),
                    "data": status_data
                }
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Confirm payment error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Payment confirmation failed: {str(e)}"
            )
    
    async def _unlock_service(self, checkout_request_id: str) -> None:
        """Unlock a service after successful payment."""
        try:
            supabase = get_supabase()
            
            # Get the payment record
            payment = supabase.table("mpesa_payments").select("*").eq("checkout_request_id", checkout_request_id).execute()
            
            if not payment.data:
                logger.warning(f"Payment record not found for {checkout_request_id}")
                return
            
            payment_data = payment.data[0]
            
            # Update payment status
            supabase.table("mpesa_payments").update({
                "status": "completed",
                "transaction_id": payment_data.get("transaction_id", f"TXN-{checkout_request_id[:8]}")
            }).eq("checkout_request_id", checkout_request_id).execute()
            
            # Unlock the service for the user
            if payment_data.get("user_id") and payment_data.get("service_id"):
                # Check if already exists
                existing = supabase.table("user_services").select("*").eq("user_id", payment_data["user_id"]).eq("service_id", payment_data["service_id"]).execute()
                
                if existing.data:
                    # Update existing
                    supabase.table("user_services").update({
                        "status": "active",
                        "purchased_at": datetime.utcnow().isoformat()
                    }).eq("id", existing.data[0]["id"]).execute()
                else:
                    # Create new
                    supabase.table("user_services").insert({
                        "user_id": payment_data["user_id"],
                        "service_id": payment_data["service_id"],
                        "status": "active",
                        "purchased_at": datetime.utcnow().isoformat()
                    }).execute()
                
                logger.info(f"Service {payment_data['service_id']} unlocked for user {payment_data['user_id']}")
                
        except Exception as e:
            logger.error(f"Unlock service error: {str(e)}")
            raise


# ─── M-PESA ROUTE HANDLERS ──────────────────────────────────────

async def handle_stk_push(
    phone: str,
    service_id: str,
    description: str,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    amount: Optional[float] = None
