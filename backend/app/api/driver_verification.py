from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.authentication.dependencies import organization_owner
from app.db import get_db
from app.models import FleetDriver, User
from app.services.integrations.identity import verify_identity

router = APIRouter(prefix="/fleet/drivers", tags=["driver verification"])
class DriverIdentityPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=2, max_length=160)
    date_of_birth: str
    driving_license_number: str = Field(min_length=5, max_length=40)
    pan_number: str = Field(min_length=10, max_length=10)
    aadhaar_number: str = Field(min_length=12, max_length=12)

@router.post("/{driver_id}/verify")
async def verify_fleet_driver(driver_id: str, payload: DriverIdentityPayload,
    user: User = Depends(organization_owner), db: AsyncSession = Depends(get_db)):
    driver = await db.scalar(select(FleetDriver).where(FleetDriver.id == driver_id,
        FleetDriver.organization_id == (user.organization_id or user.id)))
    if not driver: raise HTTPException(404, "Driver not found.")
    if driver.name.strip().casefold() != payload.full_name.strip().casefold():
        raise HTTPException(422, "Entered name does not match the company fleet driver's name. Correct the profile before verification.")
    if driver.date_of_birth and driver.date_of_birth != payload.date_of_birth:
        raise HTTPException(422, "Date of birth does not match the company fleet profile.")
    result = await verify_identity(payload.model_dump())
    driver.license_number = "*" * max(0, len(payload.driving_license_number) - 4) + payload.driving_license_number[-4:]
    driver.aadhaar_last4 = payload.aadhaar_number[-4:]
    driver.pan_masked = payload.pan_number[:2] + "******" + payload.pan_number[-2:]
    driver.verification_status = result.get("status", "review_required")
    # Store provider result/reference only. Raw Aadhaar, PAN and licence input are not persisted.
    driver.verification_result = result
    await db.commit()
    return {"driver_id": driver.id, "verification_status": driver.verification_status,
            "aadhaar_last4": driver.aadhaar_last4, "pan_masked": driver.pan_masked,
            "provider_result": result}
