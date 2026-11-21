"""SQLAlchemy persistence models for the operational OptiFreight application."""
from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "app_users"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(24), unique=True, nullable=True, index=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(40), default="client")
    tier: Mapped[str] = mapped_column(String(30), default="basic")
    organization_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    organization_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class ManualCargo(Base):
    __tablename__ = "manual_cargo"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(80))
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    rate_inr: Mapped[float | None] = mapped_column(Float, nullable=True)
    pickup: Mapped[dict] = mapped_column(JSONB)
    drop: Mapped[dict] = mapped_column(JSONB)
    pickup_window_start: Mapped[str | None] = mapped_column(String(40), nullable=True)
    pickup_window_end: Mapped[str | None] = mapped_column(String(40), nullable=True)
    loading_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    unloading_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    waiting_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    compliance_assessment: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    hazardous: Mapped[bool] = mapped_column(Boolean, default=False)
    hazardous_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    source_type: Mapped[str] = mapped_column(String(30), default="manual")
    assigned_driver_id: Mapped[str | None] = mapped_column(ForeignKey("app_users.id", ondelete="SET NULL"), nullable=True)
    assignment_status: Mapped[str] = mapped_column(String(24), default="open", nullable=False)

class MatchRun(Base):
    __tablename__ = "match_runs"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"), index=True)
    route_id: Mapped[str] = mapped_column(String(80))
    route_version: Mapped[int] = mapped_column(Integer)
    off_route_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    response: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class Shipment(Base):
    __tablename__ = "shipments"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[str] = mapped_column(String(80))
    candidate_id: Mapped[str] = mapped_column(String(100))
    route_id: Mapped[str] = mapped_column(String(80))
    route_version: Mapped[int] = mapped_column(Integer)
    route_name: Mapped[str] = mapped_column(String(160))
    origin: Mapped[dict] = mapped_column(JSONB)
    destination: Mapped[dict] = mapped_column(JSONB)
    route_polyline: Mapped[list] = mapped_column(JSONB)
    candidate: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(40), default="accepted")
    status_history: Mapped[list] = mapped_column(JSONB, default=list)
    assigned_driver_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fleet_container_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class FleetDriver(Base):
    __tablename__ = "fleet_drivers"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(320))
    license_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    aadhaar_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    pan_masked: Mapped[str | None] = mapped_column(String(16), nullable=True)
    date_of_birth: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), default="not_submitted")
    blacklisted: Mapped[bool] = mapped_column(Boolean, default=False)
    blacklist_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    __table_args__ = (UniqueConstraint("organization_id", "email", name="uq_driver_org_email"),)

class FleetContainer(Base):
    __tablename__ = "fleet_containers"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(100), index=True)
    registration_number: Mapped[str] = mapped_column(String(40))
    truck: Mapped[dict] = mapped_column(JSONB)
    documents: Mapped[dict] = mapped_column(JSONB, default=dict)
    driver_id: Mapped[str | None] = mapped_column(ForeignKey("fleet_drivers.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    __table_args__ = (UniqueConstraint("organization_id", "registration_number", name="uq_container_org_registration"),)


class DriverRestEvent(Base):
    __tablename__ = "driver_rest_events"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    driver_id: Mapped[str] = mapped_column(ForeignKey("fleet_drivers.id", ondelete="CASCADE"), index=True)
    shipment_id: Mapped[str | None] = mapped_column(ForeignKey("shipments.id", ondelete="SET NULL"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rest_type: Mapped[str] = mapped_column(String(30), default="rest")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class RegistrationOTP(Base):
    __tablename__ = "registration_otps"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    phone: Mapped[str] = mapped_column(String(24), index=True)
    otp_hash: Mapped[str] = mapped_column(String(128))
    registration_payload: Mapped[dict] = mapped_column(JSONB)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending_owner_approval", nullable=False)
    profile: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("app_users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class InPortalNotification(Base):
    __tablename__ = "in_portal_notifications"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    recipient_user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)

class DriverCargoRequest(Base):
    __tablename__ = "driver_cargo_requests"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    driver_user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False, index=True)
    cargo_id: Mapped[str] = mapped_column(ForeignKey("manual_cargo.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("app_users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (UniqueConstraint("driver_user_id", "cargo_id", name="uq_driver_cargo_request"),)

class PlatformAuditLog(Base):
    __tablename__ = "platform_audit_logs"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("app_users.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(80), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
