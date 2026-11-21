"""Tenant-scoped company, approval, driver-request and in-portal notification workflows."""
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.authentication.dependencies import current_user
from app.config import settings
from app.db import get_db
from app.models import (User, Organization, ManualCargo, DriverCargoRequest,
                        InPortalNotification, PlatformAuditLog)

router = APIRouter(tags=["portal workflows"])

def is_platform_owner(user: User) -> bool:
    return user.email.lower() in settings.platform_owner_email_list or user.role == "platform_owner"

def is_company_admin(user: User) -> bool:
    return user.role in {"organization_owner", "organization_admin", "organization_manager"}

def require_org(user: User) -> str:
    if not is_company_admin(user) or not user.organization_id:
        raise HTTPException(403, "Approved company administrator access required.")
    return user.organization_id

async def notify(db: AsyncSession, recipient: str, org_id: str | None, kind: str, title: str, message: str, payload: dict | None = None):
    db.add(InPortalNotification(recipient_user_id=recipient, organization_id=org_id, kind=kind,
        title=title, message=message, payload=payload or {}))

async def audit(db: AsyncSession, actor: User, action: str, entity_type: str, entity_id: str, org_id: str | None = None, details: dict | None = None):
    db.add(PlatformAuditLog(actor_user_id=actor.id, organization_id=org_id, action=action,
        entity_type=entity_type, entity_id=entity_id, details=details or {}))

class CompanyProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    legal_name: str = Field(min_length=2, max_length=200)
    registered_address: str = Field(min_length=5, max_length=1000)
    contact_email: str = Field(min_length=5, max_length=320)
    contact_phone: str = Field(min_length=8, max_length=24)
    gstin: str | None = Field(default=None, max_length=15)
    website: str | None = Field(default=None, max_length=300)

class CompanyReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern="^(approve|reject|blacklist|restore)$")
    note: str | None = Field(default=None, max_length=1000)

class CargoDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern="^(approve|reject)$")
    note: str | None = Field(default=None, max_length=1000)

@router.get("/companies")
async def list_companies(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if is_platform_owner(user):
        rows = (await db.scalars(select(Organization).order_by(Organization.created_at.desc()))).all()
    else:
        org_id = require_org(user)
        rows = (await db.scalars(select(Organization).where(Organization.id == org_id))).all()
    return [{"id": x.id, "name": x.name, "status": x.status, "created_at": x.created_at.isoformat(), "profile": x.profile or {}} for x in rows]

@router.get("/companies/available")
async def available_companies(db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(Organization).where(Organization.status == "active").order_by(Organization.name))).all()
    return [{"id": x.id, "name": x.name} for x in rows]

@router.put("/platform/companies/{organization_id}/review")
async def review_company(organization_id: str, payload: CompanyReview, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if not is_platform_owner(user): raise HTTPException(403, "Platform-owner access required.")
    try: UUID(organization_id)
    except ValueError: raise HTTPException(400, "Invalid company ID.")
    org = await db.scalar(select(Organization).where(Organization.id == organization_id).with_for_update())
    if not org: raise HTTPException(404, "Company not found.")
    if payload.decision == "approve":
        if org.status == "pending_owner_approval": org.status = "pending_profile_review"
        elif org.status == "pending_profile_review" and org.profile.get("profile_submitted") is True: org.status = "active"
        else: raise HTTPException(409, "Company must complete its profile before final approval.")
    else:
        org.status = {"reject":"rejected", "blacklist":"blacklisted", "restore":"active"}[payload.decision]
    org.reviewed_by = user.id; org.reviewed_at = datetime.now(timezone.utc)
    await audit(db,user,payload.decision,"organization",org.id,org.id,{"note":payload.note})
    owner = await db.get(User, org.owner_user_id)
    if owner: await notify(db, owner.id, org.id, "company_status", "Company status updated", f"Your company '{org.name}' is now {org.status}.", {"status":org.status})
    await db.commit()
    return {"id":org.id,"status":org.status}

@router.put("/company/profile")
async def update_company_profile(payload: CompanyProfile, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if user.role != "organization_owner" or not user.organization_id: raise HTTPException(403, "Company owner access required.")
    org = await db.get(Organization, user.organization_id)
    if not org or org.status not in {"pending_profile_review", "active"}: raise HTTPException(409, "Company profile cannot be edited in the current status.")
    org.profile = {**(org.profile or {}), **payload.model_dump(), "profile_submitted": True}
    org.status = "pending_profile_review"
    await db.commit()
    return {"id":org.id,"status":org.status,"profile":org.profile}

@router.get("/notifications")
async def list_notifications(unread_only: bool = False, limit: int = Query(50,ge=1,le=200), user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(InPortalNotification).where(InPortalNotification.recipient_user_id == user.id)
    if unread_only: stmt = stmt.where(InPortalNotification.read_at.is_(None))
    rows = (await db.scalars(stmt.order_by(InPortalNotification.created_at.desc()).limit(limit))).all()
    unread = await db.scalar(select(func.count(InPortalNotification.id)).where(InPortalNotification.recipient_user_id == user.id, InPortalNotification.read_at.is_(None)))
    return {"unread_count":unread or 0,"items":[{"id":x.id,"kind":x.kind,"title":x.title,"message":x.message,"payload":x.payload,"read_at":x.read_at.isoformat() if x.read_at else None,"created_at":x.created_at.isoformat()} for x in rows]}

@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    item = await db.scalar(select(InPortalNotification).where(InPortalNotification.id == notification_id, InPortalNotification.recipient_user_id == user.id).with_for_update())
    if not item: raise HTTPException(404,"Notification not found.")
    item.read_at = item.read_at or datetime.now(timezone.utc); await db.commit()
    return {"id":item.id,"read":True}

@router.get("/driver/cargo")
async def driver_available_cargo(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if user.role != "driver" or not user.organization_id: raise HTTPException(403,"Driver account required.")
    org = await db.get(Organization,user.organization_id)
    if not org or org.status != "active": raise HTTPException(403,"Company is not active.")
    rows = (await db.execute(select(ManualCargo,User).join(User,ManualCargo.owner_id == User.id).where(User.organization_id == org.id, ManualCargo.assignment_status == "open"))).all()
    return [{"id":c.id,"title":c.title,"category":c.category,"weight_kg":c.weight_kg,"pickup":c.pickup,"drop":c.drop,"hazardous":c.hazardous,"assignment_status":c.assignment_status} for c,_ in rows]

@router.post("/driver/cargo/{cargo_id}/request",status_code=201)
async def request_cargo(cargo_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if user.role != "driver" or not user.organization_id: raise HTTPException(403,"Driver account required.")
    org = await db.get(Organization,user.organization_id)
    if not org or org.status != "active": raise HTTPException(403,"Company is not active.")
    cargo = await db.scalar(select(ManualCargo).join(User,ManualCargo.owner_id == User.id).where(ManualCargo.id == cargo_id,User.organization_id == org.id,ManualCargo.assignment_status == "open"))
    if not cargo: raise HTTPException(404,"Cargo not found in your company.")
    existing = await db.scalar(select(DriverCargoRequest).where(DriverCargoRequest.driver_user_id == user.id,DriverCargoRequest.cargo_id == cargo.id))
    if existing: raise HTTPException(409,"You have already requested this cargo.")
    item=DriverCargoRequest(organization_id=org.id,driver_user_id=user.id,cargo_id=cargo.id)
    db.add(item)
    admins=(await db.scalars(select(User).where(User.organization_id == org.id,User.role.in_(["organization_owner","organization_admin","organization_manager"])))).all()
    for admin in admins: await notify(db,admin.id,org.id,"cargo_request","New driver cargo request",f"{user.name} requested {cargo.title}.",{"request_id":item.id,"cargo_id":cargo.id})
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "A request for this cargo already exists.") from exc
    return {"id":item.id,"status":item.status}

@router.get("/company/cargo-requests")
async def company_cargo_requests(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    org_id=require_org(user)
    rows=(await db.scalars(select(DriverCargoRequest).where(DriverCargoRequest.organization_id == org_id).order_by(DriverCargoRequest.requested_at.desc()))).all()
    return [{"id":x.id,"driver_user_id":x.driver_user_id,"cargo_id":x.cargo_id,"status":x.status,"requested_at":x.requested_at.isoformat(),"reviewed_by":x.reviewed_by,"reviewed_at":x.reviewed_at.isoformat() if x.reviewed_at else None,"review_note":x.review_note} for x in rows]

@router.post("/company/cargo-requests/{request_id}/review")
async def review_cargo_request(request_id: str,payload: CargoDecision,user: User = Depends(current_user),db: AsyncSession = Depends(get_db)):
    org_id=require_org(user)
    item=await db.scalar(select(DriverCargoRequest).where(DriverCargoRequest.id == request_id,DriverCargoRequest.organization_id == org_id).with_for_update())
    if not item: raise HTTPException(404,"Cargo request not found in your company.")
    if item.status != "pending": raise HTTPException(409,"This request has already been reviewed.")
    cargo = await db.scalar(select(ManualCargo).where(ManualCargo.id == item.cargo_id).with_for_update())
    if not cargo:
        raise HTTPException(404, "Requested cargo no longer exists.")
    if payload.decision == "approve":
        if cargo.assignment_status != "open" or cargo.assigned_driver_id:
            raise HTTPException(409, "This cargo has already been assigned or is no longer available.")
        cargo.assigned_driver_id = item.driver_user_id
        cargo.assignment_status = "assigned"
        item.status = "approved"
    else:
        item.status = "rejected"
    item.reviewed_by=user.id; item.reviewed_at=datetime.now(timezone.utc); item.review_note=payload.note
    await notify(db,item.driver_user_id,org_id,"cargo_request_decision","Cargo request reviewed",f"Your cargo request was {item.status}.",{"request_id":item.id,"cargo_id":item.cargo_id,"status":item.status})
    await audit(db,user,"cargo_request_"+payload.decision,"driver_cargo_request",item.id,org_id,{"driver_user_id":item.driver_user_id,"cargo_id":item.cargo_id,"note":payload.note})
    await db.commit(); return {"id":item.id,"status":item.status,"reviewed_by":user.id,"reviewed_at":item.reviewed_at.isoformat()}

@router.get("/driver/assignments")
async def driver_assignments(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if user.role != "driver" or not user.organization_id:
        raise HTTPException(403, "Driver account required.")
    rows = (await db.scalars(select(ManualCargo).join(User, ManualCargo.owner_id == User.id).where(
        User.organization_id == user.organization_id, ManualCargo.assigned_driver_id == user.id,
        ManualCargo.assignment_status == "assigned").order_by(ManualCargo.created_at.desc()))).all()
    return [{"id":c.id,"title":c.title,"category":c.category,"weight_kg":c.weight_kg,
             "pickup":c.pickup,"drop":c.drop,"hazardous":c.hazardous,"assignment_status":c.assignment_status}
            for c in rows]

@router.get("/platform/audit")
async def platform_audit(limit: int = Query(100,ge=1,le=500),user: User=Depends(current_user),db:AsyncSession=Depends(get_db)):
    if not is_platform_owner(user): raise HTTPException(403,"Platform-owner access required.")
    rows=(await db.scalars(select(PlatformAuditLog).order_by(PlatformAuditLog.created_at.desc()).limit(limit))).all()
    return [{"id":x.id,"actor_user_id":x.actor_user_id,"organization_id":x.organization_id,"action":x.action,"entity_type":x.entity_type,"entity_id":x.entity_id,"details":x.details,"created_at":x.created_at.isoformat()} for x in rows]
