# app/modules/mpesa/onsite.py
# STK Push for Auto-D Onsite valuations (cash clients). Fee is read from the database, never from the client.
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.core.database import get_supabase
from app.modules.mpesa.router import get_mpesa_service
from app.modules.mpesa.service import MpesaService
from app.modules.mpesa.stk_push import normalize_phone

logger = logging.getLogger(__name__)
router = APIRouter(tags=["M-Pesa Onsite"])


class OnsiteStkRequest(BaseModel):
    valuation_id: str
    phone: str


async def current_officer(authorization: Optional[str] = Header(default=None)) -> dict:
    """Validate the officer's Supabase session token and check they are an active officer."""
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(401, "Not signed in.")
    sb = get_supabase()
    try:
        user = sb.auth.get_user(token).user
    except Exception:
        raise HTTPException(401, "Invalid session.")
    res = (sb.table("valuation_officers").select("id,active,role,can_sign")
           .eq("id", user.id).maybe_single().execute())
    if not res or not res.data or not res.data.get("active"):
        raise HTTPException(403, "Not an active valuation officer.")
    return res.data


@router.post("/mpesa/onsite/stkpush")
async def onsite_stkpush(
    body: OnsiteStkRequest,
    officer: dict = Depends(current_officer),
    svc: MpesaService = Depends(get_mpesa_service),
):
    sb = get_supabase()
    vr = (sb.table("onsite_valuations")
          .select("id,ref,officer_id,fee,payment_status,client_id")
          .eq("id", body.valuation_id).maybe_single().execute())
    v = vr.data if vr else None
    billing = officer.get("can_sign") and officer.get("role") == "senior_valuer"
    if not v or (v["officer_id"] != officer["id"] and not billing):
        raise HTTPException(404, "Valuation not found.")

    cr = sb.table("onsite_clients").select("client_type").eq("id", v["client_id"]).maybe_single().execute()
    if not cr or not cr.data or cr.data["client_type"] != "cash":
        raise HTTPException(400, "Only cash clients pay per valuation.")
    if v["payment_status"] == "paid":
        raise HTTPException(409, "This valuation is already paid.")
    fee = float(v.get("fee") or 0)
    if fee <= 0:
        raise HTTPException(400, "No fee is set for this valuation.")
    if not svc.stk_push:
        raise HTTPException(503, "M-Pesa is not configured.")

    try:
        phone = normalize_phone(body.phone)
    except ValueError as e:
        raise HTTPException(400, str(e))

    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat()
    recent = (sb.table("payments").select("id").eq("onsite_valuation_id", v["id"])
              .eq("status", "pending").gte("created_at", cutoff).limit(1).execute())
    if recent.data:
        raise HTTPException(409, "A payment request was just sent. Wait for the client to respond.")

    ref = str(v["ref"])[:12]
    row = (sb.table("payments").insert({
        "onsite_valuation_id": v["id"], "account_reference": ref, "amount": fee,
        "currency": "KES", "status": "pending", "phone": phone,
        "description": f"Onsite valuation {v['ref']}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()).data[0]

    try:
        r = await svc.stk_push.initiate_push(
            phone=phone, amount=fee, description="Onsite valn", account_reference=ref)
    except Exception as e:
        sb.table("payments").update({"status": "failed", "result_desc": str(e)}).eq("id", row["id"]).execute()
        raise HTTPException(502, str(e))

    sb.table("payments").update({
        "checkout_request_id": r["checkout_request_id"], "mpesa_response": r,
    }).eq("id", row["id"]).execute()
    return {"status": "pending", "message": r.get("customer_message") or "STK Push sent."}
