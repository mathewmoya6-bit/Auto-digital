# Add this method to MpesaService class in mpesa_service.py

async def confirm_payment(self, checkout_id: str, user_id: str) -> Dict:
    """
    Manually confirm a payment by checkout ID.
    This is used when the callback didn't fire or user confirms manually.
    """
    try:
        # Get payment
        payment = await self.payment_repo.get_by_checkout_id(checkout_id)
        if not payment:
            return {"success": False, "error": "Payment not found"}
        
        # Verify user owns this payment
        if payment.user_id and payment.user_id != user_id:
            return {"success": False, "error": "Not authorized"}
        
        if payment.status == PaymentStatus.COMPLETED:
            return {"success": True, "status": "already_completed", "message": "Payment already confirmed"}
        
        # Get service
        service = await self.service_repo.get_by_id(payment.service_id)
        if not service:
            return {"success": False, "error": "Service not found"}
        
        # Create callback data
        callback_data = {
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": checkout_id,
                    "ResultCode": "0",
                    "ResultDesc": "Confirmed manually by user",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": float(payment.amount)},
                            {"Name": "MpesaReceiptNumber", "Value": f"MANUAL-{checkout_id[:8]}"},
                            {"Name": "PhoneNumber", "Value": payment.phone},
                        ]
                    }
                }
            }
        }
        
        # Process the callback
        success = await self.process_callback(callback_data)
        
        if success:
            return {"success": True, "message": "Payment confirmed"}
        else:
            return {"success": False, "error": "Failed to confirm payment"}
            
    except Exception as e:
        logger.exception(f"Confirm payment error: {e}")
        return {"success": False, "error": str(e)}
