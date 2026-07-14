# Auto-D Kenya — M-Pesa backend

Flask service that triggers M-Pesa STK Push payments via Safaricom's Daraja API,
and receives the payment result on a callback endpoint.

## ⚠️ First: rotate your credentials

Any M-Pesa Consumer Key/Secret, Passkey, or Short Code that has ever been pasted into
a chat, ticket, email, or shared doc should be treated as compromised. Before deploying
this:

1. Log into the [Daraja portal](https://developer.safaricom.co.ke/).
2. Regenerate the Consumer Key/Secret for this app.
3. Confirm the Passkey for your paybill with Safaricom if you suspect it's been exposed.
4. Only ever put the new values in a local `.env` file (or your host's secret manager) —
   never in code, never in chat, never committed to git.

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with your real credentials
python app.py
```

The server starts on `http://localhost:5000` by default.

## Environment variables

See `.env.example` for the full list. Key ones:

| Variable | Purpose |
|---|---|
| `MPESA_ENV` | `sandbox` while testing, `production` when live |
| `MPESA_CONSUMER_KEY` / `MPESA_CONSUMER_SECRET` | App credentials from Daraja |
| `MPESA_SHORTCODE` | Your paybill/till number |
| `MPESA_PASSKEY` | Lipa Na M-Pesa Online passkey for that shortcode |
| `MPESA_CALLBACK_URL` | Public HTTPS URL Safaricom posts results to — **must be internet-reachable**, not `localhost` |

For local testing, expose your machine with a tool like `ngrok http 5000` and put the
ngrok HTTPS URL + `/api/mpesa/callback` into `MPESA_CALLBACK_URL`.

## Endpoints

- `POST /api/mpesa/stkpush` — body `{ "phone": "0712345678", "amount": 100, "account_reference": "AUTO-D-1234", "description": "Vehicle valuation" }`. Triggers the STK push prompt on the customer's phone and returns a `checkout_request_id`.
- `POST /api/mpesa/callback` — Safaricom calls this automatically once the customer completes (or cancels) the prompt.
- `GET /api/mpesa/status/<checkout_request_id>` — frontend polls this to find out if the payment succeeded.
- `GET /api/health` — health check.

## Production notes

- Replace the in-memory `transactions` dict with a real database — it doesn't persist across restarts and won't work with multiple worker processes.
- Run behind `gunicorn` + HTTPS (e.g. `gunicorn -w 4 -b 0.0.0.0:5000 app:app`), fronted by nginx or your platform's HTTPS termination.
- Restrict CORS (`origins=[...]`) to your real frontend domain instead of allowing all origins.
- Log and alert on repeated `MpesaAPIError`s — usually a sign of an expired/incorrect credential or a shortcode/passkey mismatch.
