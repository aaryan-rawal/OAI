"""Generic identity-provider adapter.

The selected Indian KYC provider's API contract and legal authorization must be confirmed
before enabling this adapter. Never send Aadhaar/PAN/DL values to an unconfigured endpoint.
"""
from __future__ import annotations
import httpx
from app.config import settings

class IdentityProviderNotConfigured(RuntimeError):
    pass

async def verify_identity(payload: dict) -> dict:
    if not (settings.IDENTITY_VERIFICATION_API_BASE_URL and settings.IDENTITY_VERIFICATION_API_KEY and settings.IDENTITY_VERIFICATION_PROVIDER):
        return {"status": "not_configured", "verified": False, "message": "No authorized identity-verification provider is configured."}
    base = settings.IDENTITY_VERIFICATION_API_BASE_URL.rstrip("/")
    if not (base.startswith("https://") or base.startswith("http://localhost") or base.startswith("http://127.0.0.1")):
        raise ValueError("Identity provider URL must use HTTPS (except local development).")
    url = base + "/verify"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(url, json=payload, headers={"Authorization": f"Bearer {settings.IDENTITY_VERIFICATION_API_KEY}", "X-Provider": settings.IDENTITY_VERIFICATION_PROVIDER})
        response.raise_for_status()
        data = response.json()
    # Normalize only a provider-confirmed boolean; never infer a pass from HTTP 200.
    verified = data.get("verified") is True and data.get("status") in {"verified", "success"}
    return {"status": "verified" if verified else "review_required", "verified": verified,
            "provider": settings.IDENTITY_VERIFICATION_PROVIDER, "reference": data.get("reference"),
            "checks": data.get("checks", {})}
