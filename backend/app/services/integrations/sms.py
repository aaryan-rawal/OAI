"""Registration OTP delivery adapters. Twilio is supported without storing OTP plaintext."""
from __future__ import annotations
import httpx
from app.config import settings

class SMSNotConfigured(RuntimeError):
    pass


def configured() -> bool:
    provider = settings.SMS_PROVIDER.strip().lower()
    if provider == "twilio":
        return bool(settings.SMS_TWILIO_ACCOUNT_SID and settings.SMS_TWILIO_AUTH_TOKEN and
                    (settings.SMS_TWILIO_MESSAGING_SERVICE_SID or settings.SMS_SENDER_ID))
    return bool(provider and settings.SMS_API_BASE_URL and settings.SMS_API_KEY and settings.SMS_SENDER_ID)


async def send_sms(to: str, body: str) -> None:
    provider = settings.SMS_PROVIDER.strip().lower()
    if not configured():
        raise SMSNotConfigured("SMS provider credentials are incomplete.")
    if provider == "twilio":
        sid = settings.SMS_TWILIO_ACCOUNT_SID
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        form = {"To": to, "Body": body}
        if settings.SMS_TWILIO_MESSAGING_SERVICE_SID:
            form["MessagingServiceSid"] = settings.SMS_TWILIO_MESSAGING_SERVICE_SID
        else:
            form["From"] = settings.SMS_SENDER_ID
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, data=form, auth=(sid, settings.SMS_TWILIO_AUTH_TOKEN))
            response.raise_for_status()
            data = response.json()
        if not data.get("sid") or data.get("status") in {"failed", "undelivered"}:
            raise RuntimeError("SMS provider did not accept the OTP message.")
        return
    # Generic provider adapter contract: POST /messages with Bearer key.
    base = settings.SMS_API_BASE_URL.rstrip("/")
    if not base.startswith("https://") and not base.startswith("http://localhost"):
        raise ValueError("SMS provider URL must use HTTPS (except local development).")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(base + "/messages", json={"to": to, "from": settings.SMS_SENDER_ID, "message": body},
                                     headers={"Authorization": f"Bearer {settings.SMS_API_KEY}"})
        response.raise_for_status()
