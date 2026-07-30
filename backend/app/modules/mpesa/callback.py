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
            
            # Get payment record
            payment = await self.repository.get_payment_by_checkout_id(checkout_request_id)
            if not payment:
                return {"ResultCode": 1, "ResultDesc": "Payment not found"}
            
            if result_code == "0":
                # Payment successful
                # Extract transaction details
                callback_metadata = stk_callback.get("CallbackMetadata", {})
                items = callback_metadata.get("Item", [])
                
                transaction_id = None
                amount = None
                
                for item in items:
                    if item.get("Name") == "MpesaReceiptNumber":
                        transaction_id = item.get("Value")
                    elif item.get("Name") == "Amount":
                        amount = item.get("Value")
                
                # Update payment status
                await self.repository.update_payment_status(
                    checkout_request_id,
                    "completed",
                    transaction_id
                )
                
                # Unlock service for user
                if payment.get("user_id") and payment.get("service_id"):
                    await self.service.unlock_service(
                        payment["user_id"],
                        payment["service_id"]
                    )
                
                logger.info(f"Payment completed: {checkout_request_id}")
                return {"ResultCode": 0, "ResultDesc": "Success"}
                
            else:
                # Payment failed
                await self.repository.update_payment_status(
                    checkout_request_id,
                    "failed"
                )
                
                logger.warning(f"Payment failed: {checkout_request_id} - {result_desc}")
                return {"ResultCode": result_code, "ResultDesc": result_desc}
                
        except Exception as e:
            logger.error(f"Error processing callback: {str(e)}")
            return {"ResultCode": 1, "ResultDesc": str(e)}
