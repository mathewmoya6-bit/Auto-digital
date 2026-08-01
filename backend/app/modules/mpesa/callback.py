# app/modules/mpesa/callback.py
# Auto-D Kenya - M-Pesa Callback Handler
# ================================================================
# TYPE: MODULE - M-Pesa callback processing

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.modules.mpesa.repository import MpesaRepository
from app.modules.mpesa.service import MpesaService

logger = logging.getLogger(__name__)


class MpesaCallbackHandler:
    """M-Pesa callback handler."""
    
    def __init__(self):
        self.repository = MpesaRepository()
        self.service = MpesaService()
    
    async def process_callback(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process M-Pesa callback.
        
        This is the ONLY place where services should be unlocked.
        
        Args:
            callback_data: M-Pesa callback data
            
        Returns:
            Dict with processing result
        """
        try:
            # ─── Extract callback data ──────────────────────────────────
            body = callback_data.get("Body", {})
            stk_callback = body.get("stkCallback", {})
            
            result_code = stk_callback.get("ResultCode")
            result_desc = stk_callback.get("ResultDesc")
            checkout_request_id = stk_callback.get("CheckoutRequestID")
            merchant_request_id = stk_callback.get("MerchantRequestID")
            
            if not checkout_request_id:
                return {"ResultCode": 1, "ResultDesc": "Missing CheckoutRequestID"}
            
            logger.info(f"📡 Processing callback for checkout: {checkout_request_id}")
            logger.info(f"Result Code: {result_code}, Result Desc: {result_desc}")
            logger.debug(f"Full callback data: {callback_data}")
            
            # ─── Get payment record ────────────────────────────────────
            payment = await self.repository.get_payment_by_checkout_id(checkout_request_id)
            if not payment:
                logger.warning(f"⚠️ Payment not found for checkout: {checkout_request_id}")
                return {"ResultCode": 1, "ResultDesc": "Payment not found"}
            
            payment_id = payment.get("id")
            user_id = payment.get("user_id")
            service_id = payment.get("service_id")
            
            logger.info(f"📋 Payment record found: {payment_id}, User: {user_id}, Service: {service_id}")
            
            # ─── Extract transaction details from callback metadata ──────
            callback_metadata = stk_callback.get("CallbackMetadata", {})
            items = callback_metadata.get("Item", [])
            
            # Parse all items into a dictionary
            metadata = {}
            for item in items:
                name = item.get("Name")
                value = item.get("Value")
                if name:
                    metadata[name] = value
            
            # Extract specific fields
            mpesa_receipt = metadata.get("MpesaReceiptNumber")
            amount = metadata.get("Amount")
            phone = metadata.get("PhoneNumber")
            transaction_date_str = metadata.get("TransactionDate")
            
            # Parse transaction date if present (format: YYYYMMDDHHMMSS)
            transaction_date = None
            if transaction_date_str:
                try:
                    transaction_date = datetime.strptime(
                        str(transaction_date_str),
                        "%Y%m%d%H%M%S"
                    ).isoformat()
                except ValueError:
                    logger.warning(f"Could not parse transaction date: {transaction_date_str}")
            
            logger.info(f"📊 Callback metadata - Receipt: {mpesa_receipt}, Amount: {amount}, Phone: {phone}")
            
            # ─── Process based on result code ──────────────────────────
            if result_code == 0:
                # ─── ✅ SUCCESS: Payment successful ──────────────────────
                logger.info(f"✅ Payment successful for {checkout_request_id}")
                
                # Update payment with all callback data
                updated_payment = await self.repository.update_payment_from_callback(
                    checkout_request_id=checkout_request_id,
                    result_code=str(result_code),
                    result_desc=result_desc,
                    receipt=mpesa_receipt,
                    amount=float(amount) if amount else None,
                    phone=str(phone) if phone else None,
                    transaction_date=transaction_date,
                    callback_payload=callback_data
                )
                
                logger.info(f"📝 Payment updated: {updated_payment.get('id')}")
                
                # ─── 🗝️ UNLOCK SERVICE ──────────────────────────────────
                if user_id and service_id:
                    logger.info(f"🔓 Unlocking service {service_id} for user {user_id}")
                    
                    try:
                        # Update user_services table
                        user_service = await self.repository.get_user_service(user_id, service_id)
                        
                        if user_service:
                            # Update existing
                            await self.repository.update_user_service(
                                user_id=user_id,
                                service_id=service_id,
                                status="active",
                                payment_id=payment_id,
                                expires_days=365
                            )
                            logger.info(f"✅ User service updated: {user_id} -> {service_id}")
                        else:
                            # Create new
                            await self.repository.create_user_service(
                                user_id=user_id,
                                service_id=service_id,
                                payment_id=payment_id,
                                expires_days=365
                            )
                            logger.info(f"✅ User service created: {user_id} -> {service_id}")
                        
                        # Also call service.unlock_service for compatibility
                        await self.service.unlock_service(user_id, service_id)
                        
                    except Exception as unlock_err:
                        logger.error(f"❌ Error unlocking service: {unlock_err}")
                        # Don't fail the callback - payment is already recorded
                
                # ─── Update payment with unlock status ──────────────────
                try:
                    await self.repository.update_payment_status(
                        checkout_request_id=checkout_request_id,
                        status="completed",
                        transaction_id=mpesa_receipt
                    )
                except Exception as e:
                    logger.warning(f"Could not update payment status: {e}")
                
                return {
                    "ResultCode": 0,
                    "ResultDesc": "Success",
                    "checkout_request_id": checkout_request_id,
                    "mpesa_receipt": mpesa_receipt,
                    "service_unlocked": True
                }
                
            else:
                # ─── ❌ FAILURE: Payment failed ──────────────────────────
                logger.warning(f"❌ Payment failed for {checkout_request_id}: {result_desc}")
                
                # Update payment with failure data
                updated_payment = await self.repository.update_payment_from_callback(
                    checkout_request_id=checkout_request_id,
                    result_code=str(result_code),
                    result_desc=result_desc,
                    receipt=None,
                    amount=None,
                    phone=None,
                    transaction_date=None,
                    callback_payload=callback_data
                )
                
                # Update payment status to failed
                await self.repository.update_payment_status(
                    checkout_request_id=checkout_request_id,
                    status="failed"
                )
                
                return {
                    "ResultCode": result_code,
                    "ResultDesc": result_desc,
                    "checkout_request_id": checkout_request_id,
                    "service_unlocked": False
                }
                
        except Exception as e:
            logger.error(f"❌ Error processing callback: {str(e)}", exc_info=True)
            return {
                "ResultCode": 1,
                "ResultDesc": f"Internal error: {str(e)}",
                "error": str(e)
            }
    
    async def process_callback_safaricom(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process M-Pesa callback with Safaricom format.
        
        This is the format Safaricom sends the callback in.
        """
        try:
            # Extract from Safaricom format
            body = callback_data.get("Body", {})
            stk_callback = body.get("stkCallback", {})
            
            result_code = stk_callback.get("ResultCode")
            result_desc = stk_callback.get("ResultDesc")
            checkout_request_id = stk_callback.get("CheckoutRequestID")
            
            if not checkout_request_id:
                logger.warning("Missing CheckoutRequestID in callback")
                return {
                    "ResultCode": 1,
                    "ResultDesc": "Missing CheckoutRequestID"
                }
            
            # Get payment record
            payment = await self.repository.get_payment_by_checkout_id(checkout_request_id)
            if not payment:
                logger.warning(f"Payment not found for checkout: {checkout_request_id}")
                return {
                    "ResultCode": 1,
                    "ResultDesc": "Payment not found"
                }
            
            # ─── UNLOCK SERVICE ON SUCCESS ────────────────────────────
            if result_code == 0 and payment.get("user_id") and payment.get("service_id"):
                user_id = payment["user_id"]
                service_id = payment["service_id"]
                
                logger.info(f"✅ Payment successful - unlocking service: {user_id} -> {service_id}")
                
                # Update user_services
                user_service = await self.repository.get_user_service(user_id, service_id)
                if user_service:
                    await self.repository.update_user_service(
                        user_id=user_id,
                        service_id=service_id,
                        status="active",
                        payment_id=payment.get("id")
                    )
                else:
                    await self.repository.create_user_service(
                        user_id=user_id,
                        service_id=service_id,
                        payment_id=payment.get("id")
                    )
                
                # Also call service.unlock_service for compatibility
                await self.service.unlock_service(user_id, service_id)
            
            # Update payment
            await self.repository.update_payment_status(
                checkout_request_id=checkout_request_id,
                status="completed" if result_code == 0 else "failed"
            )
            
            return {
                "ResultCode": result_code,
                "ResultDesc": result_desc
            }
            
        except Exception as e:
            logger.error(f"Error processing Safaricom callback: {e}")
            return {
                "ResultCode": 1,
                "ResultDesc": f"Internal error: {str(e)}"
            }
    
    async def verify_callback_signature(self, callback_data: Dict[str, Any]) -> bool:
        """
        Verify callback signature for security.
        
        Placeholder - implement actual signature verification.
        """
        # In production, verify the signature here
        return True
    
    async def validate_callback_data(self, callback_data: Dict[str, Any]) -> bool:
        """
        Validate callback data structure.
        """
        required_fields = ["Body", "Body.stkCallback", "Body.stkCallback.CheckoutRequestID"]
        
        try:
            body = callback_data.get("Body", {})
            stk_callback = body.get("stkCallback", {})
            checkout_id = stk_callback.get("CheckoutRequestID")
            
            if not checkout_id:
                logger.warning("Invalid callback data: missing CheckoutRequestID")
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Callback validation failed: {e}")
            return False
