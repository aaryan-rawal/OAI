from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.models import FleetDriver, FleetContainer, User, Shipment, DriverRestEvent
from app.schemas import DriverIn, ContainerIn
from datetime import datetime, timezone, timedelta
from app.authentication.dependencies import organization_owner, current_user

router=APIRouter(prefix="/fleet",tags=["fleet"])

def org_id(user: User) -> str:
    return user.organization_id or user.id

def driver_json(x): return {"id":x.id,"name":x.name,"email":x.email,"license_number":x.license_number,"date_of_birth":x.date_of_birth,"address":x.address,"verification_status":x.verification_status,"blacklisted":x.blacklisted,"blacklist_reason":x.blacklist_reason,"created_at":x.created_at.isoformat()}
def container_json(x): return {"id":x.id,"registration_number":x.registration_number,"truck":x.truck,"documents":x.documents or {},"driver_id":x.driver_id,"created_at":x.created_at.isoformat()}

@router.get("/drivers")
async def list_drivers(user: User=Depends(organization_owner),db:AsyncSession=Depends(get_db)):
    rows=(await db.scalars(select(FleetDriver).where(FleetDriver.organization_id==org_id(user)).order_by(FleetDriver.name))).all()
    return [driver_json(x) for x in rows]

@router.post("/drivers",status_code=201)
async def add_driver(payload:DriverIn,user:User=Depends(organization_owner),db:AsyncSession=Depends(get_db)):
    row=FleetDriver(organization_id=org_id(user),name=payload.name.strip(),email=str(payload.email).lower(),license_number=("*" * max(0, len(payload.license_number or "") - 4) + (payload.license_number or "")[-4:] if payload.license_number else None),date_of_birth=payload.date_of_birth,address=payload.address)
    db.add(row)
    try: await db.commit()
    except IntegrityError: await db.rollback(); raise HTTPException(409,"A driver with this email is already in your organization.")
    await db.refresh(row); return driver_json(row)

@router.delete("/drivers/{driver_id}",status_code=204)
async def delete_driver(driver_id:str,user:User=Depends(organization_owner),db:AsyncSession=Depends(get_db)):
    row=await db.scalar(select(FleetDriver).where(FleetDriver.id==driver_id,FleetDriver.organization_id==org_id(user)))
    if not row: raise HTTPException(404,"Driver not found.")
    used=await db.scalar(select(FleetContainer.id).where(FleetContainer.driver_id==driver_id).limit(1))
    assigned=await db.scalar(select(Shipment.id).where(Shipment.assigned_driver_id==driver_id).limit(1))
    if used or assigned: raise HTTPException(409,"Reassign this driver's containers and accepted jobs before removing them.")
    await db.delete(row); await db.commit(); return None

@router.get("/containers")
async def list_containers(user:User=Depends(organization_owner),db:AsyncSession=Depends(get_db)):
    rows=(await db.scalars(select(FleetContainer).where(FleetContainer.organization_id==org_id(user)).order_by(FleetContainer.registration_number))).all()
    return [container_json(x) for x in rows]

async def validate_driver(payload, user, db):
    if payload.driver_id:
        row=await db.scalar(select(FleetDriver).where(FleetDriver.id==payload.driver_id,FleetDriver.organization_id==org_id(user)))
        if not row: raise HTTPException(400,"Choose a driver in your organization.")

@router.post("/containers",status_code=201)
async def add_container(payload:ContainerIn,user:User=Depends(organization_owner),db:AsyncSession=Depends(get_db)):
    await validate_driver(payload,user,db)
    row=FleetContainer(organization_id=org_id(user),registration_number=payload.registration_number.strip().upper(),truck=payload.truck.model_dump(),driver_id=payload.driver_id)
    db.add(row)
    try: await db.commit()
    except IntegrityError: await db.rollback(); raise HTTPException(409,"This container is already registered to your organization.")
    await db.refresh(row); return container_json(row)

@router.put("/containers/{container_id}")
async def update_container(container_id:str,payload:ContainerIn,user:User=Depends(organization_owner),db:AsyncSession=Depends(get_db)):
    row=await db.scalar(select(FleetContainer).where(FleetContainer.id==container_id,FleetContainer.organization_id==org_id(user)))
    if not row: raise HTTPException(404,"Container not found.")
    await validate_driver(payload,user,db)
    if row.driver_id != payload.driver_id:
        active=await db.scalar(select(Shipment.id).where(Shipment.fleet_container_id==container_id,Shipment.status.notin_(["cancelled","delivered"])).limit(1))
        if active: raise HTTPException(409,"Reassign active shipments before changing this container's driver.")
    row.registration_number=payload.registration_number.strip().upper(); row.truck=payload.truck.model_dump(); row.driver_id=payload.driver_id
    try: await db.commit()
    except IntegrityError: await db.rollback(); raise HTTPException(409,"This container is already registered to your organization.")
    await db.refresh(row); return container_json(row)

@router.delete("/containers/{container_id}",status_code=204)
async def delete_container(container_id:str,user:User=Depends(organization_owner),db:AsyncSession=Depends(get_db)):
    row=await db.scalar(select(FleetContainer).where(FleetContainer.id==container_id,FleetContainer.organization_id==org_id(user)))
    if not row: raise HTTPException(404,"Container not found.")
    used=await db.scalar(select(Shipment.id).where(Shipment.fleet_container_id==container_id).limit(1))
    if used: raise HTTPException(409,"Reassign accepted jobs before removing this container.")
    await db.delete(row); await db.commit(); return None


@router.get("/me/rest-status")
async def my_rest_status(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if user.role != "driver":
        raise HTTPException(403, "Driver account required.")
    driver = await db.scalar(select(FleetDriver).where(FleetDriver.email == user.email))
    if not driver:
        raise HTTPException(404, "No company fleet driver profile is linked to this account.")
    active = await db.scalar(select(Shipment).where(Shipment.assigned_driver_id == driver.id,
        Shipment.status.notin_(["cancelled", "delivered"])).order_by(Shipment.created_at).limit(1))
    latest = await db.scalar(select(DriverRestEvent).where(DriverRestEvent.driver_id == driver.id).order_by(DriverRestEvent.ended_at.desc()).limit(1))
    reference = max(latest.ended_at, active.created_at) if latest and active else (active.created_at if active else None)
    overdue = bool(active and reference and datetime.now(timezone.utc) - reference >= timedelta(hours=24))
    if overdue and not driver.blacklisted:
        driver.blacklisted = True
        driver.blacklist_reason = "No driver-entered rest record or completed final delivery within 24 hours of the active duty reference."
        await db.commit()
    return {"driver_id": driver.id, "blacklisted": driver.blacklisted, "blacklist_reason": driver.blacklist_reason,
            "active_shipment_id": active.id if active else None, "last_rest_ended_at": latest.ended_at.isoformat() if latest else None,
            "rest_overdue": overdue}

@router.post("/me/rest", status_code=201)
async def log_my_rest(payload: dict, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if user.role != "driver":
        raise HTTPException(403, "Driver account required.")
    driver = await db.scalar(select(FleetDriver).where(FleetDriver.email == user.email))
    if not driver:
        raise HTTPException(404, "No company fleet driver profile is linked to this account.")
    if driver.blacklisted:
        raise HTTPException(403, "This driver profile is blacklisted. Contact the company administrator.")
    try:
        start = datetime.fromisoformat(str(payload.get("started_at")).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(payload.get("ended_at")).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise HTTPException(422, "started_at and ended_at must be ISO-8601 timestamps.")
    if start.tzinfo is None or end.tzinfo is None or end <= start or end > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise HTTPException(422, "Rest interval must have timezone-aware timestamps and a positive duration not in the future.")
    active = await db.scalar(select(Shipment).where(Shipment.assigned_driver_id == driver.id,
        Shipment.status.notin_(["cancelled", "delivered"])).order_by(Shipment.created_at.asc()).limit(1))
    event = DriverRestEvent(driver_id=driver.id, shipment_id=active.id if active else None,
        started_at=start, ended_at=end, rest_type=str(payload.get("rest_type", "rest"))[:30],
        notes=str(payload.get("notes", ""))[:1000] or None)
    db.add(event)
    await db.commit()
    return {"id": event.id, "started_at": start.isoformat(), "ended_at": end.isoformat(), "status": "recorded_self_reported"}


@router.put("/containers/{container_id}/permit-metadata")
async def update_permit_metadata(container_id: str, payload: dict, user: User = Depends(organization_owner), db: AsyncSession = Depends(get_db)):
    row = await db.scalar(select(FleetContainer).where(FleetContainer.id == container_id,
        FleetContainer.organization_id == org_id(user)))
    if not row: raise HTTPException(404, "Vehicle not found.")
    kind = payload.get("kind")
    if kind not in {"transport_permit", "over_dimensional_permit"}: raise HTTPException(422, "Invalid permit kind.")
    expiry = payload.get("expiry_date")
    route = payload.get("permitted_route")
    if not isinstance(expiry, str) or not expiry.strip(): raise HTTPException(422, "Permit expiry date is required.")
    try: datetime.fromisoformat(expiry)
    except ValueError:
        try: datetime.strptime(expiry, "%Y-%m-%d")
        except ValueError: raise HTTPException(422, "Permit expiry must be an ISO date.")
    if not isinstance(route, str) or not route.strip(): raise HTTPException(422, "Permitted route is required.")
    docs = dict(row.documents or {}); record = dict(docs.get(kind) or {})
    record.update({"expiry_date": expiry, "permitted_route": route.strip(), "metadata_status": "entered_unverified"})
    docs[kind] = record; row.documents = docs; await db.commit()
    return {"kind": kind, **record}
