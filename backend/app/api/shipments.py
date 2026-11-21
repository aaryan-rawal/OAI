from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.models import MatchRun, Shipment, User, FleetDriver, FleetContainer
from app.schemas import AcceptIn, AssignmentIn
from app.authentication.dependencies import current_user, organization_owner
from app.domain.routes import get_route
from app.domain.rules import trip_caps, IST

router = APIRouter(prefix="/shipments", tags=["shipments"])
ORDER = ["accepted", "heading_to_pickup", "loaded", "in_transit", "delivered"]

def serialize(s: Shipment) -> dict:
    return {"id":s.id,"created_at":s.created_at.isoformat(),"status":s.status,"status_history":s.status_history,
            "route_id":s.route_id,"route_name":s.route_name,"route_version":s.route_version,"origin":s.origin,
            "destination":s.destination,"route_polyline":s.route_polyline,"candidate":s.candidate,
            "assigned_driver_id":s.assigned_driver_id,"fleet_container_id":s.fleet_container_id}

@router.post("", status_code=201)
async def accept(payload: AcceptIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    run = await db.scalar(select(MatchRun).where(MatchRun.id == payload.run_id, MatchRun.user_id == user.id))
    if not run: raise HTTPException(404, "Matching run not found.")
    if run.route_id != payload.route_id or run.route_version != payload.route_version:
        raise HTTPException(409, "The matching result belongs to a different route version.")
    candidate = next((c for c in run.response.get("candidates",[]) if c.get("id")==payload.candidate_id), None)
    if not candidate: raise HTTPException(404, "Candidate not found in this matching run.")
    if candidate.get("eligible") != "pass": raise HTTPException(409, "Only candidates with every required check passing can be accepted.")
    route = run.response.get("route") or get_route(payload.route_id)
    if not route: raise HTTPException(404, "Route snapshot not found.")
    active_rows=(await db.scalars(select(Shipment).where(Shipment.user_id==user.id,Shipment.route_id==payload.route_id,Shipment.status.notin_(["cancelled","delivered"])))).all()
    caps=trip_caps(float(route["distance_km"]))
    if len(active_rows) >= caps["max_jobs_total"]:
        raise HTTPException(409,f"This trip already has the maximum of {caps['max_jobs_total']} extra jobs.")
    if any(s.candidate_id==payload.candidate_id for s in active_rows):
        raise HTTPException(409,"You already accepted this cargo listing for this trip.")
    if caps["max_jobs_per_day"] is not None:
        pickup_start=candidate.get("pickup_window_start")
        if not pickup_start: raise HTTPException(409,"Pickup date is unknown; the daily job cap cannot be verified.")
        try:
            pickup_dt=datetime.fromisoformat(str(pickup_start).replace("Z","+00:00"))
            pickup_day=(pickup_dt.astimezone(IST) if pickup_dt.tzinfo else pickup_dt.replace(tzinfo=IST)).date()
            same_day=0
            for existing in active_rows:
                old_start=existing.candidate.get("pickup_window_start")
                if not old_start:
                    raise HTTPException(409,"An existing active shipment has no verifiable pickup date; the daily cap cannot be safely checked.")
                old_dt=datetime.fromisoformat(str(old_start).replace("Z","+00:00"))
                old_day=(old_dt.astimezone(IST) if old_dt.tzinfo else old_dt.replace(tzinfo=IST)).date()
                same_day += int(old_day==pickup_day)
            if same_day >= caps["max_jobs_per_day"]:
                raise HTTPException(409,"The Indian-calendar-day pickup cap has been reached.")
        except ValueError as exc:
            raise HTTPException(409,"Pickup timestamp could not be interpreted; the daily cap cannot be verified.") from exc
    now = datetime.now(timezone.utc).isoformat()
    row=Shipment(user_id=user.id,run_id=run.id,candidate_id=payload.candidate_id,route_id=route["id"],route_version=payload.route_version,
                 route_name=route["name"],origin=route["origin"],destination=route["destination"],
                 route_polyline=route["polyline"],candidate=candidate,status="accepted",
                 status_history=[{"status":"accepted","at":now}])
    db.add(row); await db.commit(); await db.refresh(row)
    return serialize(row)

@router.get("")
async def list_shipments(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows=(await db.scalars(select(Shipment).where(Shipment.user_id==user.id).order_by(Shipment.created_at.desc()))).all()
    return [serialize(x) for x in rows]

@router.get("/{shipment_id}")
async def get_shipment(shipment_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    row=await db.scalar(select(Shipment).where(Shipment.id==shipment_id,Shipment.user_id==user.id))
    if not row: raise HTTPException(404,"Shipment not found.")
    return serialize(row)

@router.post("/{shipment_id}/assignment")
async def assign(shipment_id: str, payload: AssignmentIn, user: User = Depends(organization_owner), db: AsyncSession = Depends(get_db)):
    row=await db.scalar(select(Shipment).where(Shipment.id==shipment_id,Shipment.user_id==user.id))
    if not row: raise HTTPException(404,"Shipment not found.")
    if row.status in {"delivered","cancelled"}: raise HTTPException(409,"Only active shipments can be assigned.")
    if payload.driver_id and payload.container_id:
        org=user.organization_id or user.id
        driver=await db.scalar(select(FleetDriver).where(FleetDriver.id==payload.driver_id,FleetDriver.organization_id==org))
        container=await db.scalar(select(FleetContainer).where(FleetContainer.id==payload.container_id,FleetContainer.organization_id==org))
        if not driver or not container or container.driver_id != driver.id:
            raise HTTPException(400,"Choose a container assigned to the selected driver in your organization.")
        if driver.blacklisted:
            raise HTTPException(409, "This driver is blacklisted and cannot be assigned to a shipment.")
    row.assigned_driver_id=payload.driver_id; row.fleet_container_id=payload.container_id
    await db.commit(); await db.refresh(row); return serialize(row)

@router.post("/{shipment_id}/advance")
async def advance(shipment_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    row=await db.scalar(select(Shipment).where(Shipment.id==shipment_id,Shipment.user_id==user.id))
    if not row: raise HTTPException(404,"Shipment not found.")
    if row.status not in ORDER[:-1]: raise HTTPException(409,"This shipment cannot move further.")
    next_status=ORDER[ORDER.index(row.status)+1]
    row.status=next_status; row.status_history=[*row.status_history,{"status":next_status,"at":datetime.now(timezone.utc).isoformat()}]
    await db.commit(); await db.refresh(row); return serialize(row)

@router.post("/{shipment_id}/cancel")
async def cancel(shipment_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    row=await db.scalar(select(Shipment).where(Shipment.id==shipment_id,Shipment.user_id==user.id))
    if not row: raise HTTPException(404,"Shipment not found.")
    if row.status in {"delivered","cancelled"}: raise HTTPException(409,"This shipment can no longer be cancelled.")
    row.status="cancelled"; row.status_history=[*row.status_history,{"status":"cancelled","at":datetime.now(timezone.utc).isoformat()}]
    await db.commit(); await db.refresh(row); return serialize(row)
