from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from app.authentication.dependencies import organization_owner
from app.models import User
from app.services.integrations import ewaybill
from app.services.integrations.identity import verify_identity

router = APIRouter(prefix="/integrations", tags=["optional integrations"])

class EWayBillRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supply_type: str = Field(min_length=1, max_length=20)
    document_type: str = Field(min_length=1, max_length=20)
    document_number: str = Field(min_length=1, max_length=40)
    document_date: str
    from_gstin: str
    to_gstin: str
    from_place: str
    from_pincode: str
    to_place: str
    to_pincode: str
    total_value: float = Field(gt=0)
    hsn_code: str
    vehicle_number: str
    transport_document_number: str | None = None

class IdentityCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=2, max_length=160)
    date_of_birth: str
    driving_license_number: str = Field(min_length=5, max_length=40)
    pan_number: str = Field(min_length=10, max_length=10)
    aadhaar_number: str = Field(min_length=12, max_length=12)

@router.get("/status")
async def integration_status(user: User = Depends(organization_owner)):
    return {"ewaybill_configured": ewaybill.configured(), "identity_verification_configured": bool(__import__("app.config", fromlist=["settings"]).settings.IDENTITY_VERIFICATION_API_BASE_URL and __import__("app.config", fromlist=["settings"]).settings.IDENTITY_VERIFICATION_API_KEY)}

@router.post("/ewaybill")
async def generate_ewaybill(payload: EWayBillRequest, user: User = Depends(organization_owner)):
    try:
        return await ewaybill.create_ewaybill(payload.model_dump())
    except ewaybill.EWayBillNotConfigured as exc:
        raise HTTPException(503, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"E-Way Bill provider request failed: {type(exc).__name__}")

@router.post("/identity/verify")
async def verify_driver_identity(payload: IdentityCheck, user: User = Depends(organization_owner)):
    try:
        # Sensitive identifiers are forwarded only to the explicitly configured provider;
        # this API does not persist raw Aadhaar, PAN or licence numbers.
        return await verify_identity(payload.model_dump())
    except Exception as exc:
        raise HTTPException(502, f"Identity provider request failed: {type(exc).__name__}")
