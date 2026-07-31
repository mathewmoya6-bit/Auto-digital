# app/modules/mpesa/callback.py
# Auto-D Kenya - M-Pesa Callback Handler
# ================================================================
# TYPE: MODULE - M-Pesa callback processing

import logging
from typing import Dict, Any
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
        
        Args:
            callback_data: M-Pesa callback data
            
        Returns:
            Dict with processing result
        """
        try:
            # Extract callback data
            body = callback_data.get("Body", {})
            stk_callback = body.get("stkCallback", {})
            
            result_code = stk_callback.get("ResultCode")
            result_desc = stk_callback.get("ResultDesc")
            checkout_request_id = stk_callback.get("CheckoutRequestID")
            
            if not checkout_request_id:
                return {"ResultCode": 1, "ResultDesc": "Missing CheckoutRequestID"}
            
            logger.info(f"Processing callback for checkout: {checkout_request_id}")
            logger.debug(f"Callback data: {callback_data}")
            
            # Get payment record
            payment = await self.repository.get_payment_by_checkout_id(checkout_request_id)
            if not payment:
                logger.warning(f"Payment not found for checkout: {checkout_request_id}")
                return {"ResultCode": 1, "ResultDesc": "Payment not found"}
            
            # Extract transaction details from callback metadata
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
            
            logger.info(f"Callback metadata - Receipt: {mpesa_receipt}, Amount: {amount}, Phone: {phone}")
            
            if result_code == 0:
                # ─── ✅ STEP 8: Payment successful - update ALL fields ───
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
                
                # Unlock service for user
                if payment.get("user_id") and payment.get("service_id"):
                    await self.service.unlock_service(
                        payment["user_id"],
                        payment["service_id"]
                    )
                    logger.info(f"Service unlocked for user {payment['user_id']}")
                
                return {"ResultCode": 0, "ResultDesc": "Success"}
                
            else:
                # ─── ✅ STEP 8: Payment failed - update with result data ───
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
                
                return {"ResultCode": result_code, "ResultDesc": result_desc}
                
        except Exception as e:
            logger.error(f"Error processing callback: {str(e)}")
            return {"ResultCode": 1, "ResultDesc": str(e)}
