# app/modules/mpesa/stk_push.py

# ... (all the code above remains the same until line 840)

    async def _get_payment_record(self, checkout_request_id: str) -> Optional[Dict[str, Any]]:
        """Get payment record from database."""
        try:
            result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_PAYMENTS).select("*").eq(
                    "checkout_request_id", checkout_request_id
                ).maybe_single().execute()
            )
            return result.data
        except Exception as e:
            # FIXED: Properly terminated f-string with the closing quote
            logger.error(
                f"Error getting payment record | checkout_request_id={mask_sensitive(checkout_request_id)} error={e}"
            )
            return None

    async def _update_payment_status(
        self,
        checkout_request_id: str,
        result_code: str,
        result_desc: str,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update payment record with status from a manual status query.
        NOTE: This should only be used for non-terminal statuses."""
        try:
            current = await self._get_payment_record(checkout_request_id)
            if current and PaymentStatus(current.get("status", PaymentStatus.UNKNOWN.value)).is_terminal:
                logger.info(
                    f"Skipping status update — payment already terminal | "
                    f"checkout_request_id={mask_sensitive(checkout_request_id)} "
                    f"current_status={current.get('status')}"
                )
                return current

            status = self._map_result_code_to_status(result_code)
            now = datetime.now(timezone.utc).isoformat()

            update_data = {
                "status": status.value,
                "result_code": result_code,
                "result_desc": result_desc,
                "updated_at": now
            }

            if str(result_code) == "0":
                update_data["mpesa_receipt"] = data.get("MpesaReceiptNumber")
                update_data["transaction_id"] = checkout_request_id
                update_data["completed_at"] = now

            result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_PAYMENTS).update(update_data).eq(
                    "checkout_request_id", checkout_request_id
                ).execute()
            )

            self._spawn_background(self._log_payment_event(
                checkout_request_id, "status_update", {"status": status.value, "result_code": result_code}
            ))

            return result.data[0] if result.data else None

        except Exception as e:
            logger.error(
                f"Error updating payment status | checkout_request_id={mask_sensitive(checkout_request_id)} error={e}"
            )
            return None

    async def _create_payment_record(
        self,
        checkout_request_id: str,
        merchant_request_id: str,
        amount: float,
        phone: str,
        user_id: Optional[str],
        service_id: Optional[int],
        description: str
    ) -> Dict[str, Any]:
        """Create a payment record with idempotency check."""
        try:
            existing = await self._get_payment_record(checkout_request_id)
            if existing:
                logger.info(f"Payment already exists | checkout_request_id={mask_sensitive(checkout_request_id)}")
                return existing

            if service_id:
                service = await self._get_cached_service(service_id)
                if not service:
                    raise NotFoundException(f"Service {service_id} not found")

            now = datetime.now(timezone.utc).isoformat()
            payment_data = {
                "checkout_request_id": checkout_request_id,
                "merchant_request_id": merchant_request_id,
                "amount": amount,
                "phone": phone,
                "user_id": user_id,
                "service_id": service_id,
                "description": description[:DESCRIPTION_MAX_LENGTH],
                "status": PaymentStatus.PENDING.value,
                "unlock_status": UnlockStatus.PENDING.value,
                "created_at": now,
                "updated_at": now
            }

            result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_PAYMENTS).insert(payment_data).execute()
            )

            self._spawn_background(self._log_payment_event(
                checkout_request_id, "payment_created", {"amount": amount, "service_id": service_id}
            ))

            return result.data[0]

        except Exception as e:
            logger.error(
                f"Failed to create payment record | checkout_request_id={mask_sensitive(checkout_request_id)} error={e}"
            )
            raise

    async def _get_service_active_column(self) -> str:
        """Detect once whether the services table uses 'active' or 'is_active'."""
        if self._service_active_column:
            return self._service_active_column

        async with self._service_column_lock:
            if self._service_active_column:
                return self._service_active_column

            try:
                result = await execute_supabase_async(
                    lambda: self.supabase.table(TABLE_SERVICES).select("*").limit(1).execute()
                )
                if result.data:
                    columns = result.data[0].keys()
                    if "is_active" in columns:
                        self._service_active_column = "is_active"
                    elif "active" in columns:
                        self._service_active_column = "active"
                    else:
                        self._service_active_column = "active"
                else:
                    self._service_active_column = "active"
            except Exception as e:
                logger.warning(f"Could not detect services active-column, defaulting to 'active' | error={e}")
                self._service_active_column = "active"

            return self._service_active_column

    async def _validate_service(self, service_id: int) -> Optional[Dict[str, Any]]:
        """Validate that a service exists and is active."""
        try:
            active_column = await self._get_service_active_column()
            result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_SERVICES).select("*").eq(
                    "id", service_id
                ).eq(active_column, True).maybe_single().execute()
            )
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Error validating service | service_id={service_id} error={e}")
            return None

    async def _upsert_user_service(
        self,
        user_id: str,
        service_id: int,
        payment_id: int,
        expiry_days: Optional[int] = None,
        mpesa_receipt: Optional[str] = None,
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        fix #19: real atomic upsert via Supabase's .upsert(), which issues a
        single `INSERT ... ON CONFLICT (...) DO UPDATE` at the Postgres level
        instead of the previous update-then-insert-then-update dance (which
        had a real race window between the failed UPDATE and the INSERT).

        REQUIRES a unique constraint on (user_id, service_id) in
        user_services — if you don't already have one:

          ALTER TABLE user_services
          ADD CONSTRAINT user_services_user_service_unique
          UNIQUE (user_id, service_id);

        `on_conflict` below must match that constraint's columns exactly.
        """
        now = datetime.now(timezone.utc).isoformat()
        expires_at = self._get_expiry_date(expiry_days)

        row = {
            "user_id": user_id,
            "service_id": service_id,
            "payment_id": payment_id,
            "status": ServiceStatus.ACTIVE.value,
            "expires_at": expires_at,
            "mpesa_receipt": mpesa_receipt,
            "transaction_id": transaction_id,
            "updated_at": now,
        }

        try:
            result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_USER_SERVICES).upsert(
                    row, on_conflict="user_id,service_id"
                ).execute()
            )
            if result.data:
                return result.data[0]
            return row

        except Exception as e:
            logger.error(
                f"Error upserting user service | user_id={user_id} service_id={service_id} error={e}"
            )
            raise

    async def _atomic_unlock_transaction(
        self,
        checkout_request_id: str,
        mpesa_receipt: Optional[str] = None,
        callback_amount: Optional[float] = None
    ) -> Tuple[bool, str]:
        """Atomically mark the payment unlocked AND grant user_services access."""
        try:
            payment = await self._get_payment_record(checkout_request_id)
            if not payment:
                return False, "Payment record not found"

            if payment.get("unlock_status") == UnlockStatus.COMPLETED.value:
                return True, "Service already unlocked"

            user_id = payment.get("user_id")
            service_id = payment.get("service_id")
            payment_id = payment.get("id")
            expected_amount = payment.get("amount")

            if callback_amount is not None:
                if callback_amount <= 0:
                    return False, f"Invalid callback amount: {callback_amount}"
                if expected_amount and abs(float(callback_amount) - float(expected_amount)) > 0.01:
                    return False, f"Amount mismatch: expected {expected_amount}, got {callback_amount}"

            if not user_id or not service_id:
                return False, f"Missing user_id or service_id: {checkout_request_id}"

            service = await self._get_cached_service(service_id)
            expiry_days = service.get("expiry_days") if service else None
            expires_at = self._get_expiry_date(expiry_days)

            try:
                rpc_result = await execute_supabase_async(
                    lambda: self.supabase.rpc(
                        "unlock_paid_service",
                        {
                            "p_payment_id": payment_id,
                            "p_user_id": user_id,
                            "p_service_id": service_id,
                            "p_mpesa_receipt": mpesa_receipt,
                            "p_transaction_id": checkout_request_id,
                            "p_callback_amount": callback_amount,
                            "p_expires_at": expires_at,
                        },
                    ).execute()
                )
                already_unlocked = bool(rpc_result.data) and rpc_result.data is False
                unlock_via_rpc = True
            except Exception as rpc_error:
                logger.warning(
                    f"unlock_paid_service RPC unavailable, falling back to two-step unlock | "
                    f"checkout_request_id={mask_sensitive(checkout_request_id)} error={rpc_error}"
                )
                unlock_via_rpc = False
                already_unlocked = False

            if not unlock_via_rpc:
                now = datetime.now(timezone.utc).isoformat()
                result = await execute_supabase_async(
                    lambda: self.supabase.table(TABLE_PAYMENTS).update({
                        "unlock_status": UnlockStatus.COMPLETED.value,
                        "unlocked_at": now,
                        "mpesa_receipt": mpesa_receipt,
                        "callback_amount": callback_amount
                    }).eq("id", payment_id).eq("unlock_status", UnlockStatus.PENDING.value).execute()
                )
                if not result.data:
                    return True, "Service already unlocked (concurrent)"

                await self._upsert_user_service(
                    user_id=user_id,
                    service_id=service_id,
                    payment_id=payment_id,
                    expiry_days=expiry_days,
                    mpesa_receipt=mpesa_receipt,
                    transaction_id=checkout_request_id
                )
            elif already_unlocked:
                return True, "Service already unlocked (concurrent)"

            service_name = service.get("name", "Service") if service else "Service"

            # fix #2 / #6: the payment/user_services rows are already
            # durably written above (via the RPC, or the fallback
            # update+upsert path) — that's the actual "unlock." A failed or
            # slow notification insert must never make it look like the
            # unlock itself failed, and it shouldn't add latency to the
            # callback response either. Both go out as background tasks;
            # their own internal try/except already logs failures.
            self._spawn_background(self._create_notification(
                user_id=user_id,
                title=f"🎉 {service_name} Unlocked!",
                message=f"Your {service_name} has been successfully unlocked. You can now access it from your dashboard.",
                notification_type="service_unlocked",
                reference_id=checkout_request_id,
            ))

            self._spawn_background(self._log_payment_event(
                checkout_request_id,
                "service_unlocked",
                {"user_id": user_id, "service_id": service_id, "mpesa_receipt": mpesa_receipt}
            ))

            logger.info(f"Service unlocked | service_id={service_id} user_id={user_id}")
            return True, "Service unlocked successfully"

        except Exception as e:
            logger.error(
                f"Error unlocking service | checkout_request_id={mask_sensitive(checkout_request_id)} error={e}"
            )
            return False, str(e)

    # ─── STK PUSH ────────────────────────────────────────────

    async def initiate_push(
        self,
        phone: str,
        amount: float,
        description: str,
        checkout_request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        service_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Initiate STK Push payment."""
        normalized_phone = normalize_phone(phone)

        if amount <= 0:
            raise ValidationException("Amount must be greater than zero")
        if amount < MINIMUM_AMOUNT:
            raise ValidationException(f"Amount must be at least {MINIMUM_AMOUNT}")

        service_name = None
        if service_id:
            service = await self._get_cached_service(service_id)
            if not service:
                raise NotFoundException(f"Service {service_id} not found")
            service_name = service.get("name", "Service")

            service_price = float(service.get("price", 0))
            if service_price > 0 and abs(amount - service_price) > 0.01:
                logger.warning(
                    f"Amount mismatch between request and service price | "
                    f"service_id={service_id} requested_amount={amount} service_price={service_price}"
                )

        rounded_amount = math.ceil(amount)
        if rounded_amount != amount:
            logger.info(f"Amount rounded | original={amount} rounded={rounded_amount}")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        password = self._generate_password(timestamp)

        account_reference = generate_account_reference(service_name, user_id)

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": TRANSACTION_TYPE,
            "Amount": str(rounded_amount),
            "PartyA": normalized_phone,
            "PartyB": self.shortcode,
            "PhoneNumber": normalized_phone,
            "CallBackURL": self.callback_url,
            "AccountReference": account_reference,
            "TransactionDesc": description[:DESCRIPTION_MAX_LENGTH]
        }

        logger.info(f"Initiating STK Push | phone={mask_sensitive(normalized_phone)} amount={rounded_amount}")

        token = await self._get_access_token()

        # fix #16: this now goes through the retry-wrapped helper instead of
        # a bare client.post() — transient 429/502/503/504s and connection
        # blips are retried with backoff before we give up.
        response = await self._post_with_retry(
            f"{self.base_url}/mpesa/stkpush/v1/processrequest",
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            payload
        )

        data = response.json()
        if "ResponseCode" not in data:
            raise AppException("Invalid response from Safaricom", 502)

        response_code = data.get("ResponseCode")
        if response_code != "0":
            raise AppException(f"STK push failed: {data.get('ResponseDescription', 'Unknown error')}", 400)

        merchant_request_id = data.get("MerchantRequestID")
        checkout_id = data.get("CheckoutRequestID")

        if not checkout_id or not merchant_request_id:
            raise AppException("Missing CheckoutRequestID or MerchantRequestID from Safaricom", 502)

        payment = await self._create_payment_record(
            checkout_request_id=checkout_id,
            merchant_request_id=merchant_request_id,
            amount=rounded_amount,
            phone=normalized_phone,
            user_id=user_id,
            service_id=service_id,
            description=description
        )

        logger.info(
            f"STK Push successful | checkout_request_id={mask_sensitive(checkout_id)} payment_id={payment.get('id')}"
        )

        return {
            "checkout_request_id": checkout_id,
            "merchant_request_id": merchant_request_id,
            "response_code": data.get("ResponseCode"),
            "response_description": data.get("ResponseDescription"),
            "customer_message": data.get("CustomerMessage")
        }

    # ─── CALLBACK PROCESSING ─────────────────────────────────

    async def process_callback(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process M-Pesa callback with replay protection."""
        try:
            body = callback_data.get("Body", {})
            stk_callback = body.get("stkCallback", {})

            if not stk_callback:
                logger.error("Invalid callback structure")
                return {"status": "error", "message": "Invalid callback structure"}

            checkout_request_id = stk_callback.get("CheckoutRequestID")
            merchant_request_id = stk_callback.get("MerchantRequestID")
            result_code = stk_callback.get("ResultCode")
            result_desc = stk_callback.get("ResultDesc", "")

            if not checkout_request_id:
                logger.error("Callback missing CheckoutRequestID")
                return {"status": "error", "message": "Missing CheckoutRequestID"}

            # fix #17: DB-backed replay check (in-memory cache is just the
            # fast path inside _is_replay()).
            if await self._is_replay(checkout_request_id):
                logger.warning(
                    f"Replay detected — duplicate callback | "
                    f"checkout_request_id={mask_sensitive(checkout_request_id)}"
                )
                return {
                    "status": "replay_detected",
                    "message": "Callback already processed",
                    "checkout_request_id": checkout_request_id
                }

            payment = await self._get_payment_record(checkout_request_id)
            context = PaymentContext(
                checkout_request_id=checkout_request_id,
                merchant_request_id=merchant_request_id,
                payment_id=payment.get("id", 0) if payment else 0,
                user_id=payment.get("user_id", "") if payment else "",
                service_id=payment.get("service_id", 0) if payment else 0,
                amount=payment.get("amount", 0.0) if payment else 0.0
            )

            logger.info(
                f"Processing callback | checkout_request_id={mask_sensitive(checkout_request_id)} "
                f"result_code={result_code} {context}"
            )

            if not payment:
                self._spawn_background(self._log_payment_event(
                    checkout_request_id, "callback_unknown", {"result_code": result_code}
                ))
                return {"status": "ignored", "message": "Payment record not found"}

            if payment.get("merchant_request_id") != merchant_request_id:
                logger.error(
                    f"MerchantRequestID mismatch — possible malicious callback | "
                    f"expected={payment.get('merchant_request_id')} received={merchant_request_id}"
                )
                return {"status": "error", "message": "MerchantRequestID mismatch - possible malicious callback"}

            current_status = PaymentStatus(payment.get("status", PaymentStatus.UNKNOWN.value))
            if current_status.is_terminal:
                logger.info(
                    f"Callback already processed | "
                    f"checkout_request_id={mask_sensitive(checkout_request_id)} status={current_status.value}"
                )
                return {
                    "status": "already_processed",
                    "checkout_request_id": checkout_request_id,
                    "message": "Payment already processed"
                }

            callback_amount = None
            mpesa_receipt = None
            transaction_date = None

            callback_metadata = stk_callback.get("CallbackMetadata")
            if callback_metadata:
                items = callback_metadata.get("Item", [])
                for item in items:
                    name = item.get("Name")
                    value = item.get("Value")
                    if name == "Amount":
                        callback_amount = float(value) if value else None
                    elif name == "MpesaReceiptNumber":
                        mpesa_receipt = value
                    elif name == "TransactionDate":
                        transaction_date = value
            else:
                logger.info(f"No CallbackMetadata in callback | checkout_request_id={mask_sensitive(checkout_request_id)}")

            if callback_amount is not None:
                if callback_amount <= 0:
                    logger.error(
                        f"Invalid callback amount (<= 0) | callback_amount={callback_amount} "
                        f"checkout_request_id={mask_sensitive(checkout_request_id)}"
                    )
                    return {
                        "status": "failed",
                        "checkout_request_id": checkout_request_id,
                        "message": f"Invalid callback amount: {callback_amount}"
                    }

                expected_amount = float(payment.get("amount", 0))
                if abs(callback_amount - expected_amount) > 0.01:
                    logger.error(f"Amount mismatch on callback | expected={expected_amount} received={callback_amount}")
                    return {
                        "status": "failed",
                        "checkout_request_id": checkout_request_id,
                        "message": f"Amount mismatch: expected {expected_amount}, got {callback_amount}"
                    }

            unlock_success = False
            unlock_message = ""

            if str(result_code) == "0":
                unlock_success, unlock_message = await self._atomic_unlock_transaction(
                    checkout_request_id=checkout_request_id,
                    mpesa_receipt=mpesa_receipt,
                    callback_amount=callback_amount
                )

            if str(result_code) == "0":
                status = PaymentStatus.COMPLETED
                unlock_status = UnlockStatus.COMPLETED if unlock_success else UnlockStatus.FAILED
                message = (
                    "Payment confirmed and service unlocked"
                    if unlock_success
                    else f"Payment received but service unlock failed: {unlock_message}"
                )
                if not unlock_success:
                    logger.error(f"Payment completed but unlock failed | reason={unlock_message} {context}")
            else:
                status = PaymentStatus.FAILED
                unlock_status = UnlockStatus.FAILED
                message = "Payment failed"

            now = datetime.now(timezone.utc).isoformat()
            update_data = {
                "status": status.value,
                "unlock_status": unlock_status.value,
                "result_code": str(result_code),
                "result_desc": result_desc,
                "updated_at": now,
                "mpesa_receipt": mpesa_receipt,
                "transaction_id": checkout_request_id,
                "callback_amount": callback_amount
            }

            if str(result_code) == "0":
                update_data["completed_at"] = now

            await execute_supabase_async(
                lambda: self.supabase.table(TABLE_PAYMENTS).update(update_data).eq(
                    "checkout_request_id", checkout_request_id
                ).execute()
            )

            # fix #6: this is the audit-log write for the whole callback —
            # exactly the one the review flagged as adding latency right
            # before we respond to Safaricom. The payments row update above
            # is already durable; this is just an audit trail.
            self._spawn_background(self._log_payment_event(
                checkout_request_id,
                "callback_processed",
                {
                    "result_code": result_code,
                    "status": status.value,
                    "unlock_status": unlock_status.value,
                    "unlock_message": unlock_message
                }
            ))

            if str(result_code) == "0" and unlock_success:
                logger.info(f"Payment completed and service unlocked | {context}")
                return {
                    "status": "success",
                    "checkout_request_id": checkout_request_id,
                    "mpesa_receipt": mpesa_receipt,
                    "transaction_date": transaction_date,
                    "amount": callback_amount,
                    "message": "Payment confirmed and service unlocked"
                }
            elif str(result_code) == "0" and not unlock_success:
                return {
                    "status": "partial",
                    "checkout_request_id": checkout_request_id,
                    "mpesa_receipt": mpesa_receipt,
                    "message": f"Payment received but service unlock failed: {unlock_message}"
                }
            else:
                logger.warning(f"Callback reported failure | result_code={result_code} result_desc={result_desc} {context}")
                return {
                    "status": "failed",
                    "checkout_request_id": checkout_request_id,
                    "result_code": result_code,
                    "result_desc": result_desc,
                    "message": "Payment failed"
                }

        except Exception as e:
            logger.error(f"Error processing callback | error={e}")
            return {"status": "error", "message": str(e)}

    # ─── PAYMENT VERIFICATION ────────────────────────────────

    async def verify_payment_status(self, checkout_request_id: str) -> Dict[str, Any]:
        """
        Verify payment status with Safaricom API - READ-ONLY.
        The callback is the only source of truth that modifies payment records.
        """
        try:
            payment = await self._get_payment_record(checkout_request_id)
            if not payment:
                return {"status": "not_found", "message": "Payment record not found"}

            current_status = PaymentStatus(payment.get("status", PaymentStatus.UNKNOWN.value))

            if current_status.is_terminal:
                return {
                    "status": payment.get("status"),
                    "unlock_status": payment.get("unlock_status"),
                    "mpesa_receipt": payment.get("mpesa_receipt"),
                    "transaction_id": payment.get("transaction_id"),
                    "result_desc": payment.get("result_desc"),
                }

            token = await self._get_access_token()
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            password = self._generate_password(timestamp)

            payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            }

            logger.info(f"Querying payment status (read-only) | checkout_request_id={mask_sensitive(checkout_request_id)}")

            token_header = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            # fix #16: retry-wrapped here too.
            response = await self._post_with_retry(
                f"{self.base_url}/mpesa/stkpushquery/v1/query",
                token_header,
                payload
            )

            data = response.json()
            result_code = data.get("ResultCode")
            result_desc = data.get("ResultDesc", "Unknown")

            return {
                "status": self._map_result_code_to_status(result_code).value,
                "result_code": result_code,
                "result_desc": result_desc,
                "mpesa_receipt": data.get("MpesaReceiptNumber"),
                "transaction_id": checkout_request_id,
                "query_verified": True,
                "note": "Read-only query - callback is source of truth"
            }

        except httpx.HTTPError as e:
            logger.warning(f"Status query HTTP error | error={e}")
            return {"status": "unknown", "message": f"HTTP error: {str(e)}"}
        except Exception as e:
            logger.error(f"Payment verification error | error={e}")
            return {"status": "error", "message": str(e)}

    # ─── SERVICE ACCESS ──────────────────────────────────────

    async def check_service_access(self, user_id: str, service_id: int) -> Dict[str, Any]:
        """Check if a user has access to a service."""
        try:
            result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_USER_SERVICES).select("*").eq(
                    "user_id", user_id
                ).eq("service_id", service_id).maybe_single().execute()
            )

            if result.data:
                record = result.data
                status = record.get("status")
                expires_at = record.get("expires_at")

                if expires_at:
                    try:
                        expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        if datetime.now(timezone.utc) > expires:
                            return {"has_access": False, "status": "expired", "message": "Access has expired"}
                    except (ValueError, TypeError):
                        pass

                if status == ServiceStatus.ACTIVE.value:
                    return {
                        "has_access": True,
                        "status": status,
                        "expires_at": expires_at,
                        "message": "Access granted"
                    }

            payments_result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_PAYMENTS).select("*").eq(
                    "user_id", user_id
                ).eq("service_id", service_id).eq(
                    "status", PaymentStatus.COMPLETED.value
                ).eq(
                    "unlock_status", UnlockStatus.COMPLETED.value
                ).order("created_at", desc=True).limit(1).execute()
            )

            if payments_result.data:
                payment = payments_result.data[0]
                if not result.data:
                    service = await self._get_cached_service(service_id)
                    expiry_days = service.get("expiry_days") if service else None
                    await self._upsert_user_service(
                        user_id=user_id,
                        service_id=service_id,
                        payment_id=payment.get("id"),
                        expiry_days=expiry_days,
                        mpesa_receipt=payment.get("mpesa_receipt"),
                        transaction_id=payment.get("transaction_id")
                    )

                return {"has_access": True, "status": "active", "message": "Access granted (recovered from payment)"}

            return {"has_access": False, "status": "no_record", "message": "No access record found"}

        except Exception as e:
            logger.error(f"Error checking service access | user_id={user_id} service_id={service_id} error={e}")
            return {"has_access": False, "status": "error", "message": str(e)}

    async def get_user_services(self, user_id: str) -> Dict[int, bool]:
        """Get all services a user has access to."""
        try:
            result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_USER_SERVICES).select(
                    "service_id, status, expires_at"
                ).eq("user_id", user_id).execute()
            )

            services = {}
            now = datetime.now(timezone.utc)

            for record in result.data:
                service_id = record.get("service_id")
                status = record.get("status")
                expires_at = record.get("expires_at")

                is_expired = False
                if expires_at:
                    try:
                        expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        if now > expires:
                            is_expired = True
                    except (ValueError, TypeError):
                        pass

                has_access = status == ServiceStatus.ACTIVE.value and not is_expired
                services[service_id] = has_access

            return services

        except Exception as e:
            logger.error(f"Error getting user services | user_id={user_id} error={e}")
            return {}

    # ─── STALE PAYMENT CLEANUP ──────────────────────────────

    async def cleanup_stale_payments(self) -> int:
        """Mark stale pending payments as expired."""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=STALE_PAYMENT_HOURS)
            cutoff_str = cutoff.isoformat()

            result = await execute_supabase_async(
                lambda: self.supabase.table(TABLE_PAYMENTS).update({
                    "status": PaymentStatus.EXPIRED.value,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("status", PaymentStatus.PENDING.value).lt("created_at", cutoff_str).execute()
            )

            count = len(result.data) if result.data else 0
            if count > 0:
                logger.info(f"Cleaned up stale payments | count={count}")

            return count

        except Exception as e:
            logger.error(f"Error cleaning up stale payments | error={e}")
            return 0

    # ─── HELPERS ─────────────────────────────────────────────

    def _generate_password(self, timestamp: str) -> str:
        """Generate password for STK push."""
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(password_str.encode()).decode()

    def _map_result_code_to_status(self, result_code) -> PaymentStatus:
        """Map Safaricom result code to PaymentStatus."""
        try:
            code = int(result_code)
        except (TypeError, ValueError):
            return PaymentStatus.UNKNOWN

        if code == 0:
            return PaymentStatus.COMPLETED
        elif code in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
            return PaymentStatus.FAILED
        elif code in [17, 18, 19, 20, 21]:
            return PaymentStatus.CANCELLED
        else:
            return PaymentStatus.UNKNOWN
