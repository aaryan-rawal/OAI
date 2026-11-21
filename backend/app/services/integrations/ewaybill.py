"""Optional E-Way Bill provider adapter using an explicit normalized provider contract.

A paid GSP/API provider must supply its endpoint/auth contract. This adapter deliberately
fails closed rather than pretending that any arbitrary API key is a government credential.
"""
from __future__ import annotations
import httpx
from app.config import settings

class EWayBillNotConfigured(RuntimeError):
    pass

def configured() -> bool:
    return bool(settings.EWAYBILL_API_BASE_URL and settings.EWAYBILL_API_KEY)

async def create_ewaybill(payload: dict) -> dict:
    if not configured():
        raise EWayBillNotConfigured("E-Way Bill provider is not configured.")
    base = settings.EWAYBILL_API_BASE_URL.rstrip("/")
    if not (base.startswith("https://") or base.startswith("http://localhost") or base.startswith("http://127.0.0.1")):
        raise ValueError("E-Way Bill provider URL must use HTTPS (except local development).")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(base + "/ewaybill", json=payload,
            headers={"Authorization": f"Bearer {settings.EWAYBILL_API_KEY}",
                     **({"X-Client-Id": settings.EWAYBILL_CLIENT_ID} if settings.EWAYBILL_CLIENT_ID else {}),
                     **({"X-Client-Secret": settings.EWAYBILL_CLIENT_SECRET} if settings.EWAYBILL_CLIENT_SECRET else {}),
                     **({"X-GSTIN": settings.EWAYBILL_GSTIN} if settings.EWAYBILL_GSTIN else {})})
        response.raise_for_status()
        data = response.json()
    if not data.get("ewayBillNo") and not data.get("ewaybill_number"):
        raise RuntimeError("Provider response did not contain an E-Way Bill number.")
    return data
